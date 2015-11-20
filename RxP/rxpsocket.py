import random
import threading
from asyncio import Queue, Lock

from FxA.util import Util
from RxP.Packeter import Packeter
from RxP.RTOEstimator import RTOEstimator
from RxP.RecvBuffer import RecvBuffer
from RxP.RxProtocol import RxProtocol
from RxP.SendBuffer import SendBuffer
from exception import RxPException

# list of all states
# Active open: OPEN->YO_SENT->SYN_YO_ACK_SENT->ESTABLISHED
# Passive open: OPEN->LISTEN->YO_RCVD->ESTABLISHED
# Closing Initiator: CYA_SENT->CYA_WAIT->LAST_WAIT->CLOSED
# Closing Responder: CLOSE_WAIT->LAST_WORD->CLOSED
LAST_WAIT_DUR_S = 15
MAX_SEQ_NUM = 4294967296


class States:
    OPEN = 'OPEN'
    CLOSED = 'CLOSED'
    LISTEN = 'LISTEN'
    YO_SENT = 'YO_SENT'
    YO_RCVD = 'YO_RCVD'
    SYN_YO_ACK_SENT = 'SYN_YO_ACK_SENT'
    ESTABLISHED = 'ESTABLISHED'
    CYA_SENT = 'CYA_SENT'
    CYA_WAIT = 'CYA_WAIT'
    LAST_WAIT = 'LAST_WAIT'
    CLOSE_WAIT = 'CLOSE_WAIT'
    LAST_WORD = 'LAST_WORD'


class rxpsocket:
    MAX_INIT_RETRIES = int(5)

    __logger = Util.setup_logger()

    # Attach RxP Layer to UDP Layer as the network layer.
    #
    # @udp_port     port number of the UDP socket to open
    # @proxy_addr   address of the first hop of every segment sent out
    @staticmethod
    def initial_setup(udp_port=int(15000),
                      proxy_addr=('127.0.0.1', int(13000))):
        RxProtocol.open_network(udp_port, proxy_addr)

    def __init__(self):
        self.__state = States.OPEN
        self.__state_cond = threading.Condition(Lock())
        self.__self_addr = None
        self.__peer_addr = None
        self.__recv_buffer = None
        self.__send_buffer = None
        self.__next_seq_num = None
        self.__next_ack_num = None
        self.__connected_client_queue = None
        self.__inbound_processor = lambda src_port, rcvd_segment: None

    # Bind this socket to @address
    #
    # @address  address of this socket
    def bind(self, address):
        if self.__self_addr is not None:
            raise RxPException(errno=105)
        if RxProtocol.is_available_port(port_num=address[1]):
            self.__self_addr = address
        else:
            raise RxPException(errno=100)

    # Listen at this socket for an incoming connection
    #
    # @max_num_queued   maximum number of client waiting to be served
    def listen(self, max_num_queued):
        if self.__state is States.OPEN:
            self.__state = States.LISTEN
            if self.__self_addr is None:
                RxProtocol.register(soc=self)
            else:
                RxProtocol.register(soc=self, port=self.__self_addr[1])
            self.__connected_client_queue = Queue(maxsize=max_num_queued)
            self.__inbound_processor = self.__process_passive_open
        else:
            raise RxPException(108)

    # Attempt to make connection to @address
    #
    # @address  address of host to be connected
    def connect(self, address):
        if self.__state is States.OPEN:
            if self.__self_addr is None:
                RxProtocol.register(soc=self, addr_port=address)
            else:
                RxProtocol.register(
                    soc=self,
                    port=self.__self_addr[1],
                    addr_port=address
                )
            self.__state = States.YO_SENT
            cond = self.__state_cond

            def term_func():
                RTOEstimator.rt_update()
                term_func.tries -= 1
                cond.acquire()

                # wait will block until predicate is True, ret<-True
                # else if timeout, ret<-False
                ret = cond.wait_for(
                    predicate=self.__state is not States.YO_SENT or
                              term_func.tries == 0,
                    timeout=RTOEstimator.get_rto_interval() / 1000
                )
                cond.release()

                # we return true iff predicate is true
                return ret

            term_func.tries = self.MAX_INIT_RETRIES
            self.__peer_addr = address
            self.__inbound_processor = self.__process_active_open
            first_yo = Packeter.control_packet(
                src_port=self.__self_addr[1],
                dst_port=address[1],
                seq_num=0,
                ack_num=0,
                yo=True
            )
            RxProtocol.ar_send(
                dest_addr=address,
                msg=first_yo,
                stop_func=term_func,
            )
        elif self.__state is States.CLOSED:
            raise RxPException(errno=103)
        elif self.__state is States.LAST_WAIT:
            raise RxPException(errno=106)
        else:
            raise RxPException(errno=104)

    def accept(self):
        # conn is a new socket object usable to send and
        # receive data on the connection, and address
        # is the address bound to the socket on the other
        # end of the connection
        # return (conn, address)
        pass

    def send(self, data_bytes):
        self.__next_seq_num = self.__send_buffer.put(
            src_port=self.__self_addr[1],
            dst_port=self.__peer_addr[1],
            seq_num=self.__next_seq_num,
            data=data_bytes
        )
        # TODO: return number of bytes sent

    def recv(self, buffsize):
        pass

    def close(self):
        cya = Packeter.control_packet(
            src_port=self.__self_addr[1],
            dst_port=self.__peer_addr[1],
            seq_num=self.__next_seq_num,
            ack_num=self.__next_ack_num,
            cya=True
        )
        self.__increment_next_seq_num()
        if self.__state is States.ESTABLISHED:
            self.__state = States.CYA_SENT
            self.__inbound_processor = self.__process_init_close
            cond = self.__state_cond

            def term_func():
                RTOEstimator.rt_update()
                cond.acquire()
                ret = cond.wait_for(
                    predicate=self.__state is not States.CYA_SENT,
                    timeout=RTOEstimator.get_rto_interval() / 1000
                )
                cond.release()
                return ret

            RxProtocol.ar_send(
                dest_addr=self.__peer_addr,
                msg=cya,
                stop_func=term_func
            )

        elif self.__state is States.CLOSE_WAIT:
            self.__state = States.LAST_WORD
            self.__inbound_processor = self.__process_resp_close
            cond = self.__state_cond

            def term_func():
                RTOEstimator.rt_update()
                cond.acquire()
                ret = cond.wait_for(
                    predicate=self.__state is not States.LAST_WORD,
                    timeout=RTOEstimator.get_rto_interval()
                )
                cond.release()
                return ret

            # TODO: might need a way to immediately close after ACK rcvd,
            # how to notify a sleeping thread? cond var?
            RxProtocol.ar_send(
                dest_addr=self.__peer_addr,
                msg=cya,
                stop_func=term_func
            )

    # For internal use only
    def _get_addr(self):
        return self.__self_addr

    # Process header for control related information
    # and then pass the segment to buffer to process data related
    # information
    def _process_rcvd(self, src_ip, rcvd_segment):
        if Packeter.validate_checksum(rcvd_segment):
            self.__inbound_processor(src_ip, rcvd_segment)

    def __process_data_exchange(self, _src_ip, _rcvd_segment):
        src_addr = (_src_ip, _rcvd_segment.get_src_port())
        if src_addr is self.__peer_addr and \
                        _rcvd_segment.get_seq_num() == self.__next_ack_num:
            if _rcvd_segment.get_cya():
                self.__increment_next_ack_num()
                self.__state = States.CLOSE_WAIT
            else:
                self.__next_ack_num = self.__recv_buffer.put(
                    acknum=self.__next_ack_num,
                    inbound_segment=_rcvd_segment
                )

    # use this after listen() is invoked
    def __process_passive_open(self, _src_ip, _rcvd_segment):
        client_queue = self.__connected_client_queue
        if not client_queue.full() and _rcvd_segment.get_yo():
            src_addr = (_src_ip, _rcvd_segment.get_src_port())
            if _rcvd_segment.get_ack() and _rcvd_segment.get_ack_num() == \
                    self.__next_seq_num and src_addr is self.__peer_addr:
                # Received YO!+ACK segment
                # PASSIVE OPEN: YO_RCVD->ESTABLISHED
                self.__recv_buffer = RecvBuffer()
                self.__send_buffer = SendBuffer()
                self.__next_ack_num = _rcvd_segment.get_seq_num()
                self.__increment_next_ack_num()
                cond = self.__state_cond
                cond.acquire()
                self.__state = States.LISTEN
                cond.notify()
                cond.release()
                # TODO: make new socket for the new client and enqueue
                # TODO: let the new created socket send ACK with data
            else:
                # Received YO! segment
                if self.__state is States.LISTEN:
                    # PASSIVE OPEN: LISTEN->YO_RCVD
                    self.__peer_addr = src_addr
                    self.__next_seq_num = random.randint(0, MAX_SEQ_NUM)
                    self.__state = States.YO_RCVD

                    def term_func():
                        RTOEstimator.rt_update()
                        cond.acquire()
                        ret = cond.wait_for(
                            predicate=self.__state is States.ESTABLISHED,
                            timeout=RTOEstimator.get_rto_interval()
                        )
                        cond.release()
                        return ret

                    syn_yo = Packeter.control_packet(
                        src_port=self.__self_addr[1],
                        dst_port=src_addr[1],
                        seq_num=self.__next_seq_num,
                        ack_num=0,
                        yo=True
                    )

                    RxProtocol.ar_send(
                        dest_addr=src_addr,
                        msg=syn_yo,
                        stop_func=term_func,
                    )
                    self.__increment_next_seq_num()

    def __reinit(self, ip_addr, state, peer_addr, init_seq_num,
                 init_ack_num, recv_buffer_size):
        self.__self_addr = (ip_addr, int)
        self.__state = state
        self.__peer_addr = peer_addr
        self.__next_seq_num = init_seq_num
        self.__next_ack_num = init_ack_num
        self.__recv_buffer = RecvBuffer(buffer_size=recv_buffer_size)
        self.__send_buffer = SendBuffer()

    # use this after first Yo! is sent
    def __process_active_open(self, _src_ip, _rcvd_segment):
        src_addr = (_src_ip, _rcvd_segment.get_src_port())
        if src_addr is self.__peer_addr:
            cond = self.__state_cond
            if _rcvd_segment.get_yo():
                if self.__state is States.YO_SENT:
                    # ACTIVE OPEN: YO_SENT->SYN_YO_ACK_SENT
                    self.__next_seq_num = random.randint(0, MAX_SEQ_NUM)
                    self.__next_ack_num = _rcvd_segment.get_seq_num()
                    self.__increment_next_ack_num()
                    self.__recv_buffer = RecvBuffer()
                    self.__send_buffer = SendBuffer()
                    cond.acquire()
                    self.__state = States.SYN_YO_ACK_SENT
                    cond.notify()
                    cond.release()

                    def term_func():
                        RTOEstimator.rt_update()
                        cond.acquire()
                        ret = cond.wait_for(
                            predicate=self.__state is not
                                      States.SYN_YO_ACK_SENT,
                            timeout=RTOEstimator.get_rto_interval()
                        )
                        cond.release()
                        return ret

                    syn_yo_ack = Packeter.control_packet(
                        src_port=self.__self_addr[1],
                        dst_port=src_addr[1],
                        seq_num=self.__next_seq_num,
                        ack_num=_rcvd_segment.get_seq_num() + 1,
                        yo=True,
                        ack=True
                    )
                    RxProtocol.ar_send(
                        dest_addr=src_addr,
                        msg=syn_yo_ack,
                        stop_func=term_func
                    )
                    self.__increment_next_seq_num()
            elif _rcvd_segment.get_ack() and _rcvd_segment.get_ack_num() == \
                    self.__next_seq_num and _rcvd_segment.get_seq_num() == \
                    self.__next_ack_num and self.__state is \
                    States.SYN_YO_ACK_SENT:
                # ACTIVE OPEN: SYN_YO_ACK_SENT->ESTABLISHED
                cond.acquire()
                self.__state = States.ESTABLISHED
                cond.notify()
                cond.release()
                # TODO: process data
                self.__inbound_processor = self.__process_data_exchange

    def __process_init_close(self, _src_ip, _rcvd_segment):
        src_addr = (_src_ip, _rcvd_segment.get_src_port())
        if src_addr is self.__peer_addr and _rcvd_segment.get_seq_num() == \
                self.__next_ack_num:
            # ACK of CYA, there might be a data here as well
            if _rcvd_segment.get_ack() and _rcvd_segment.get_ack_num() == \
                    self.__next_seq_num and self.__state is States.CYA_SENT:
                self.__send_buffer = None
                cond = self.__state_cond
                cond.acquire()
                self.__state = States.CYA_WAIT
                cond.notify()
                cond.release()

            if _rcvd_segment.get_cya():
                # we dont want to accept any more data if CYA bit was set
                if self.__state is States.CYA_WAIT:
                    self.__state = States.LAST_WAIT
                if self.__state is States.LAST_WAIT:
                    last_ack = Packeter.control_packet(
                        src_port=self.__self_addr[1],
                        dst_port=_src_ip[1],
                        seq_num=self.__next_seq_num,
                        ack_num=self.__next_ack_num,
                        ack=True
                    )
                    self.__increment_next_seq_num()
                    RxProtocol.send(
                        address=src_addr,
                        data=last_ack
                    )
                    self.__schedule_active_closure()
            else:
                self.__process_data_exchange(_src_ip, _rcvd_segment)

    def __schedule_active_closure(self):
        if self.__schedule_active_closure.scheder is not None:
            self.__schedule_active_closure.scheder.cancel()

        def closure():
            self.__recv_buffer = None
            self.__inbound_processor = lambda src_port, rcvd_segment: None
            self.__state = States.CLOSED

        self.__schedule_active_closure.scheder = \
            threading.Timer(LAST_WAIT_DUR_S, closure)
        self.__schedule_active_closure.scheder.start()

    __schedule_active_closure.scheder = None

    def __process_resp_close(self, _src_ip, _rcvd_segment):
        # there should not be any more data here, since the initiator
        # supposed to already close their send buffer
        if _rcvd_segment.get_ack() and _rcvd_segment.get_ack_num() == \
                self.__next_seq_num and _rcvd_segment.get_seq_num() == \
                self.__next_ack_num and self.__state is States.LAST_WORD:
            self.__send_buffer = None
            self.__recv_buffer = None
            self.__inbound_processor = lambda src_port, rcvd_segment: None
            cond = self.__state_cond
            cond.acquire()
            self.__state = States.CLOSED
            cond.notify()
            cond.release()

    def __increment_next_seq_num(self):
        self.__next_seq_num = (self.__next_seq_num + 1) % MAX_SEQ_NUM

    def __increment_next_ack_num(self):
        self.__next_ack_num = (self.__next_ack_num + 1) % MAX_SEQ_NUM
