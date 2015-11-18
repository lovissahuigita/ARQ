import random
from asyncio import Queue

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
        self.__self_addr = None
        self.__peer_addr = None
        self.__recv_buffer = None
        self.__send_buffer = None
        self.__init_seq_num = None
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

            def term_func():
                RTOEstimator.rt_update()
                term_func.tries -= 1
                return self.__state is States.SYN_YO_ACK_SENT or \
                       term_func.tries == 0

            term_func.tries = self.MAX_INIT_RETRIES

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
                ms_interval=RTOEstimator.get_rto_interval,
                stop_func=term_func,
            )
            self.__peer_addr = address
            self.__inbound_processor = self.__process_active_open
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
        pass

    def recv(self, buffsize):
        pass

    def close(self):
        pass

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
        if src_addr is self.__peer_addr:
            if _rcvd_segment.get_cya() and _rcvd_segment.get_seq_num() == \
                    self.__recv_buffer.get_expected_seq_num():
                self.__state = States.CLOSE_WAIT
            else:
                self.__recv_buffer.put(_rcvd_segment)

    # use this after listen() is invoked
    def __process_passive_open(self, _src_ip, _rcvd_segment):
        client_queue = self.__connected_client_queue
        if not client_queue.full() and _rcvd_segment.get_yo():
            src_addr = (_src_ip, _rcvd_segment.get_src_port())
            if _rcvd_segment.get_ack() and src_addr is self.__peer_addr:
                # Received YO!+ACK segment
                if _rcvd_segment.get_ack_num() == self.__init_seq_num + 1:
                    # PASSIVE OPEN: YO_RCVD->ESTABLISHED
                    self.__recv_buffer = RecvBuffer(
                        base_seq_num=_rcvd_segment.get_seq_num() + 1
                    )
                    self.__send_buffer = SendBuffer(
                        base_seq_num=self.__init_seq_num + 1
                    )
                    self.__state = States.LISTEN
                    # TODO: make new socket for the new client and enqueue
                    # TODO: send ACK with data
                else:
                    # failed to sync, peer send wrong ack number
                    pass
            else:
                # Received YO! segment
                if self.__state is States.LISTEN:
                    # PASSIVE OPEN: LISTEN->YO_RCVD
                    self.__peer_addr = src_addr
                    self.__init_seq_num = random.randint(0, 4294967296)
                    self.__state = States.YO_RCVD

                    def term_func():
                        RTOEstimator.rt_update()
                        return self.__state is States.ESTABLISHED

                    syn_yo = Packeter.control_packet(
                        src_port=self.__self_addr[1],
                        dst_port=src_addr[1],
                        seq_num=self.__init_seq_num,
                        ack_num=0,
                        yo=True
                    )

                    RxProtocol.ar_send(
                        dest_addr=src_addr,
                        msg=syn_yo,
                        ms_interval=RTOEstimator.get_rto_interval,
                        stop_func=term_func,
                    )

    def __reinit(self, ip_addr, state, peer_addr, init_seq_num,
                 init_ack_num, recv_buffer_size):
        self.__self_addr = (ip_addr, int)
        self.__state = state
        self.__peer_addr = peer_addr
        self.__recv_buffer = RecvBuffer(
            base_seq_num=init_ack_num,
            buffer_size=recv_buffer_size
        )
        self.__send_buffer = SendBuffer(base_seq_num=init_seq_num)

    # use this after first Yo! is sent
    def __process_active_open(self, _src_ip, _rcvd_segment):
        src_addr = (_src_ip, _rcvd_segment.get_src_port())
        if src_addr is self.__peer_addr:
            if _rcvd_segment.get_yo():
                if self.__state is States.YO_SENT:
                    # ACTIVE OPEN: YO_SENT->SYN_YO_ACK_SENT
                    self.__init_seq_num = random.randint(0, 4294967296)
                    self.__recv_buffer = RecvBuffer(
                        base_seq_num=_rcvd_segment.get_seq_num() + 1
                    )
                    self.__send_buffer = SendBuffer(
                        base_seq_num=self.__init_seq_num + 1
                    )
                    self.__state = States.SYN_YO_ACK_SENT

                    def term_func():
                        RTOEstimator.rt_update()
                        return self.__state is States.ESTABLISHED

                    syn_yo_ack = Packeter.control_packet(
                        src_port=self.__self_addr[1],
                        dst_port=src_addr[1],
                        seq_num=self.__init_seq_num,
                        ack_num=_rcvd_segment.get_seq_num() + 1,
                        yo=True,
                        ack=True
                    )
                    RxProtocol.ar_send(
                        dest_addr=src_addr,
                        msg=syn_yo_ack,
                        ms_interval=RTOEstimator.get_rto_interval,
                        stop_func=term_func
                    )
            elif _rcvd_segment.get_ack() and self.__state is \
                    States.SYN_YO_ACK_SENT:
                if _rcvd_segment.get_ack_num() == self.__init_seq_num + 1:
                    # ACTIVE OPEN: SYN_YO_ACK_SENT->ESTABLISHED
                    self.__state = States.ESTABLISHED
                    # TODO: process data
                    self.__inbound_processor = self.__process_data_exchange
                else:
                    # Failed to synchronize, server sent wrong ack number
                    pass

    def __process_init_close(self, _src_ip, _rcvd_segment):
        if _rcvd_segment.get_ack() and _rcvd_segment.get_ack_num() == \
                self.__send_buffer.get_next_seq_num() \
                and self.__state is States.CYA_SENT:
            self.__send_buffer = None
            self.__state = States.CYA_WAIT
        elif _rcvd_segment.get_cya() and _rcvd_segment.get_seq_num() == \
                self.__recv_buffer.get_expected_seq_num():
            if self.__state is States.CYA_WAIT:
                self.__state = States.LAST_WAIT
            if self.__state is States.LAST_WAIT:
                # TODO: send ACK
                # TODO: once timeout, release receive buffer
                pass

    def __process_resp_close(self, _src_ip, _rcvd_segment):
        if _rcvd_segment.get_ack() and _rcvd_segment.get_ack_num() == \
                self.__send_buffer.get_next_seq_num() and self.__state is \
                States.LAST_WORD:
            self.__send_buffer = None
            self.__recv_buffer = None
            self.__state = States.CLOSED

    def _process_send(self, ):
        pass
