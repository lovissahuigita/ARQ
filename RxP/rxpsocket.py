import threading
from queue import Queue
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

MAX_SEQ_NUM = 4294967296

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
        self.__state_cond = threading.Condition(threading.Lock())
        self.__self_addr = None
        self.__peer_addr = None
        self.__recv_buffer = None
        self.__send_buffer = None
        self.__next_seq_num = None
        self.__next_ack_num = None
        self.__connected_client_queue = None
        self.__inbound_processor = lambda src_port, rcvd_segment: None
        self.__peer_window_size = 1

        # replacement for static method var, please dont use it
        self.__flush_send_scheder = None
        self.__schedule_active_closure_scheder = None

    def __str__(self):
        return 'rxpsocket' + str(
            (self.__state, self.__self_addr, self.__peer_addr,
             self.__inbound_processor.__name__))

    def bind(self, address):
        """ Bind the socket to address
        :param address: tuple of IP address and port to bind
        :return: None
        """

        # The port has to be empty in order to bind
        if self.__self_addr is not None:
            raise RxPException(errno=105)

        # Find an available port to bind
        if RxProtocol.is_available_port(port=address[1]):

            # Claim the port by registering it
            RxProtocol.register(
                socket=self,
                port=address[1]
            )
            self.__self_addr = address
        else:
            raise RxPException(errno=100)

    def listen(self, max_num_queued):
        """ Listen at this socket for an incoming connection
        :param max_num_queued: the maximum number of client waiting to be
        served
        :return: None
        """
        if self.__state == States.OPEN:

            # Change the state of the connection
            self.__state = States.LISTEN

            # register the port to be used by the socket
            if self.__self_addr is None:
                RxProtocol.register(socket=self)
            self.__connected_client_queue = Queue(maxsize=max_num_queued)
            self.__inbound_processor = self.__process_passive_open
        else:
            raise RxPException(108)

    # Attempt to make connection to @address
    #
    # @address  address of host to be connected
    def connect(self, address):
        if self.__state == States.OPEN:
            if self.__self_addr is None:
                RxProtocol.register(socket=self)

            self.__send_buffer = SendBuffer(
                src_port=self.__self_addr[1],
                dst_port=address[1]
            )

            self.__recv_buffer = RecvBuffer()

            RxProtocol.register_peer(
                port=self.__self_addr[1],
                peer_addr=address
            )
            self.__state = States.YO_SENT
            cond = self.__state_cond

            # def term_func():
            #     RTOEstimator.rt_update()
            #     term_func.tries -= 1
            #     cond.acquire()
            #
            #     # wait will block until predicate is True, ret<-True
            #     # else if timeout, ret<-False
            #     ret = cond.wait_for(
            #         predicate=lambda: self.__state != States.YO_SENT or
            #                           term_func.tries == 0,
            #         timeout=RTOEstimator.get_rto_interval() / 1000
            #     )
            #     cond.release()
            #
            #     # we return true iff predicate is true
            #     return ret
            # term_func.tries = self.MAX_INIT_RETRIES
            self.__peer_addr = address
            self.__inbound_processor = self.__process_active_open
            self.__logger.info("Starting 4-way handshake procedure...")
            self.__send_buffer.put(
                yo=True
            )
            self.__flush_send(with_ack=False)
            cond.acquire()
            cond.wait_for(
                predicate=lambda: self.__state == States.ESTABLISHED
            )
            cond.release()

            # TODO: need to find a way to be notified if we failed to
            # retransmit for 5 times

            # first_yo = Packeter.control_packet(
            #     src_port=self.__self_addr[1],
            #     dst_port=address[1],
            #     seq_num=0,
            #     ack_num=0,
            #     yo=True
            # )
            # worker = RxProtocol.ar_send(
            #     dest_addr=address,
            #     msg=first_yo,
            #     stop_func=term_func,
            # )
            # worker.join()
            if self.__state != States.ESTABLISHED:
                raise RxPException(errno=101)
        elif self.__state == States.CLOSED:
            raise RxPException(errno=103)
        elif self.__state == States.LAST_WAIT:
            raise RxPException(errno=106)
        else:
            raise RxPException(errno=104)

    def accept(self):
        # conn is a new socket object usable to send and
        # receive data on the connection, and address
        # is the address bound to the socket on the other
        # end of the connection
        # return (conn, address)
        # pool = ThreadPool(processes=1)
        # res = pool.apply_async(
        #     # TODO: do we need a new thread to wait?
        # thread for the listening?
        #     func=self.__connected_client_queue.get,
        #     args=True
        # )
        # return res.get()
        childsock = self.__connected_client_queue.get(block=True)
        return childsock, childsock.__peer_addr

    def send(self, data_bytes):
        self.__send_buffer.put(
            data=data_bytes
        )
        # TODO: return number of bytes sent
        self.__flush_send()
        return len(data_bytes)

    def recv(self, buffsize):
        return self.__recv_buffer.take(max_read=buffsize)

    def close(self):
        self.__send_buffer.put(
            cya=True
        )
        if self.__state == States.ESTABLISHED:
            self.__state = States.CYA_SENT
            self.__inbound_processor = self.__process_init_close
        elif self.__state == States.CLOSE_WAIT:
            self.__state = States.LAST_WORD
            self.__inbound_processor = self.__process_resp_close
        elif self.__state == States.LISTEN:
            # TODO: WHAT SHOULD I DO NOW?
            pass
        self.__flush_send()
        cond = self.__state_cond
        cond.acquire()
        cond.wait_for(
            predicate=lambda: self.__state == States.CLOSED
        )
        cond.release()

    # For internal use only
    def _get_addr(self):
        return self.__self_addr

        # For internal use only

    def _set_addr(self, addr):
        self.__self_addr = addr

    # Process header for control related information
    # and then pass the segment to buffer to process data related
    # information
    def _process_rcvd(self, src_ip, rcvd_segment):
        self.__logger.info("Received segment...")
        if Packeter.validate_checksum(rcvd_segment):
            self.__inbound_processor(src_ip, rcvd_segment)
        if rcvd_segment.is_yo() or rcvd_segment.is_cya() or \
                rcvd_segment.get_data():
            self.__flush_send(with_ack=self.__state != States.YO_RCVD)
        self.__logger.debug(str(self))
        cond = self.__state_cond
        cond.acquire()
        cond.notify()
        cond.release()

    def __process_data_xchange(self, _src_ip, _rcvd_segment):
        src_addr = (_src_ip, _rcvd_segment.get_src_port())
        if src_addr == self.__peer_addr and self.__recv_buffer.is_expecting(
                _rcvd_segment):

            # allows send buffer to discard acked segments
            self.__send_buffer.notify_ack(_rcvd_segment.get_ack_num())

            # keeptrack of peer window size
            self.__peer_window_size = _rcvd_segment.get_window_size()

            # let recv buffer to update the expected seq_num
            # if not control packet >> put data in recv_buffer
            self.__recv_buffer.put(inbound_segment=_rcvd_segment)

            # if the peer initiate closing
            if _rcvd_segment.is_cya():
                self.__state = States.CLOSE_WAIT

    def __flush_send(self, with_ack=True):
        if self.__flush_send_scheder is not None:
            self.__flush_send_scheder.cancel()
        flow_window = self.__peer_window_size
        congestion_window = 2000000000 # TODO: WE still dont have congestion
        # window
        flushed = self.__send_buffer.take(
            ack=with_ack,
            ack_num=self.__recv_buffer.get_expected_seq_num(),
            self_rcv_wind_size=self.__recv_buffer.get_window_size(),
            # we still want to send 1 segment at a time even when peer
            # closed their window so we know once it open
            max_segment=max(min(flow_window, congestion_window), 1)
        )
        for segment in flushed:
            RxProtocol.send(
                address=self.__peer_addr,
                packet=segment
            )
        self.__flush_send_scheder = threading.Timer(
            RTOEstimator.get_rto_interval(), self.__flush_send)
        self.__flush_send_scheder.start()
        self.__logger.debug(str(self))

    # use this after listen() is invoked
    def __process_passive_open(self, _src_ip, _rcvd_segment):
        client_queue = self.__connected_client_queue
        if not client_queue.full() and _rcvd_segment.is_yo():
            src_addr = (_src_ip, _rcvd_segment.get_src_port())
            cond = self.__state_cond
            if _rcvd_segment.is_ack() and _rcvd_segment.get_ack_num() == \
                    self.__send_buffer.get_next_seq_num() and src_addr == \
                    self.__peer_addr:
                # Received YO!+ACK segment
                # PASSIVE OPEN: YO_RCVD->ESTABLISHED
                self.__peer_window_size = _rcvd_segment.get_window_size()
                self.__send_buffer.notify_ack(_rcvd_segment.get_ack_num())

                # expands the buffer size
                self.__recv_buffer.commit()
                self.__send_buffer.commit()
                self.__recv_buffer.sync_ack_num(_rcvd_segment.get_seq_num())
                client_queue.put(self.__spawn_kid())
                cond.acquire()
                self.__state = States.LISTEN
                cond.notify()
                cond.release()

                # RxProtocol.send(
                #     address=src_addr,
                #     packet=Packeter.control_packet(
                #         src_port=self.__self_addr[1],
                #         dst_port=self.__peer_addr[1],
                #         seq_num=self.__next_seq_num,
                #         ack_num=self.__next_ack_num,
                #         ack=True
                #     )
                # )
                # TODO: what if there are lots of client waiting, and this
                # listening socket closed?
                # TODO: let the new created socket send ACK with data
            else:
                # Received YO! segment
                if self.__state == States.LISTEN:
                    # PASSIVE OPEN: LISTEN->YO_RCVD
                    self.__peer_addr = src_addr
                    self.__send_buffer = SendBuffer(
                        src_port=self.__self_addr[1],
                        dst_port=src_addr[1]
                    )
                    self.__recv_buffer = RecvBuffer()

                    send_buffer = self.__send_buffer
                    send_buffer.generate_seq_num()

                    # keeptrack of peer window size
                    self.__peer_window_size = _rcvd_segment.get_window_size()

                    self.__state = States.YO_RCVD
                    self.__send_buffer.put(yo=True)

                    # TODO: reflush if we receive unexpected segment!

                    # def term_func():
                    #     RTOEstimator.rt_update()
                    #     cond.acquire()
                    #     ret = cond.wait_for(
                    #         predicate=lambda: self.__state ==
                    #                           States.ESTABLISHED,
                    #         timeout=RTOEstimator.get_rto_interval()
                    #     )
                    #     cond.release()
                    #     return ret
                    #
                    # syn_yo = Packeter.control_packet(
                    #     src_port=self.__self_addr[1],
                    #     dst_port=src_addr[1],
                    #     seq_num=self.__next_seq_num,
                    #     ack_num=0,
                    #     yo=True
                    # )
                    #
                    # RxProtocol.ar_send(
                    #     dest_addr=src_addr,
                    #     msg=syn_yo,
                    #     stop_func=term_func,
                    # )

    def __spawn_kid(self):
        # TODO: make sure this kid initialized with all the right value!!!!!
        kiddy = rxpsocket()
        kiddy.__state = States.ESTABLISHED
        kiddy.__peer_addr = self.__peer_addr
        kiddy.__next_seq_num = self.__next_seq_num
        kiddy.__next_ack_num = self.__next_ack_num
        kiddy.__recv_buffer = self.__recv_buffer
        kiddy.__send_buffer = self.__send_buffer
        kiddy.__peer_window_size = self.__peer_window_size
        kiddy.__inbound_processor = kiddy.__process_data_xchange
        RxProtocol.register(
            socket=kiddy
        )
        RxProtocol.register_peer(
            # after the previous call return, this kiddy socket should have
            # a port num
            port=kiddy.__self_addr[1],
            peer_addr=self.__peer_addr
        )
        kiddy.__self_addr = self.__self_addr
        return kiddy

    # use this after first Yo! is sent
    def __process_active_open(self, _src_ip, _rcvd_segment):
        src_addr = (_src_ip, _rcvd_segment.get_src_port())
        if src_addr == self.__peer_addr:
            cond = self.__state_cond
            if _rcvd_segment.is_yo():
                if self.__state == States.YO_SENT:
                    # ACTIVE OPEN: YO_SENT->SYN_YO_ACK_SENT
                    self.__send_buffer.generate_seq_num()
                    self.__recv_buffer.commit()
                    self.__send_buffer.commit()
                    self.__send_buffer.notify_ack(1)
                    self.__recv_buffer.sync_ack_num(
                        _rcvd_segment.get_seq_num())
                    cond.acquire()
                    self.__state = States.SYN_YO_ACK_SENT
                    cond.notify()
                    cond.release()
                    self.__send_buffer.put(
                        yo=True
                    )
                    #
                    # def term_func():
                    #     RTOEstimator.rt_update()
                    #     cond.acquire()
                    #     ret = cond.wait_for(
                    #         predicate=lambda: self.__state !=
                    #                           States.SYN_YO_ACK_SENT,
                    #         timeout=RTOEstimator.get_rto_interval()
                    #     )
                    #     cond.release()
                    #     return ret
                    #
                    # syn_yo_ack = Packeter.control_packet(
                    #     src_port=self.__self_addr[1],
                    #     dst_port=src_addr[1],
                    #     seq_num=self.__next_seq_num,
                    #     ack_num=self.__next_ack_num,
                    #     yo=True,
                    #     ack=True
                    # )
                    # RxProtocol.ar_send(
                    #     dest_addr=src_addr,
                    #     msg=syn_yo_ack,
                    #     stop_func=term_func
                    # )
            elif _rcvd_segment.is_ack() and _rcvd_segment.get_ack_num() == \
                    self.__send_buffer.get_next_seq_num() and \
                    self.__recv_buffer.is_expecting(_rcvd_segment) and \
                            self.__state == States.SYN_YO_ACK_SENT:

                # allows send buffer to discard acked segments
                self.__send_buffer.notify_ack(_rcvd_segment.get_ack_num())

                # keeptrack of peer window size
                self.__peer_window_size = _rcvd_segment.get_window_size()

                # let recv buffer to update the expected seq_num
                # if not control packet >> put data in recv_buffer
                self.__recv_buffer.put(inbound_segment=_rcvd_segment)

                # ACTIVE OPEN: SYN_YO_ACK_SENT->ESTABLISHED
                cond.acquire()
                self.__state = States.ESTABLISHED
                cond.notify()
                cond.release()
                # TODO: process data
                self.__inbound_processor = self.__process_data_xchange

    def __process_init_close(self, _src_ip, _rcvd_segment):
        src_addr = (_src_ip, _rcvd_segment.get_src_port())

        if src_addr == self.__peer_addr and self.__recv_buffer.is_expecting(
                _rcvd_segment):
            # allows send buffer to discard acked segments
            self.__send_buffer.notify_ack(_rcvd_segment.get_ack_num())

            # keeptrack of peer window size
            self.__peer_window_size = _rcvd_segment.get_window_size()

            # ACK of CYA, there might be a data here as well
            if _rcvd_segment.is_ack() and _rcvd_segment.get_ack_num() == \
                    self.__send_buffer.get_next_seq_num() and self.__state \
                    == States.CYA_SENT:
                cond = self.__state_cond
                cond.acquire()
                self.__state = States.CYA_WAIT
                cond.notify()
                cond.release()

            if _rcvd_segment.is_cya():
                # we dont want to accept any more data if CYA bit was set
                if self.__state == States.CYA_WAIT:
                    self.__state = States.LAST_WAIT
                    self.__send_buffer.put(
                        cya=True
                    )
                    # last_ack = Packeter.control_packet(
                    #     src_port=self.__self_addr[1],
                    #     dst_port=_src_ip[1],
                    #     seq_num=self.__next_seq_num,
                    #     ack_num=self.__next_ack_num,
                    #     ack=True
                    # )
                    # RxProtocol.send(
                    #     address=src_addr,
                    #     data=last_ack
                    # )
                    self.__schedule_active_closure()

            # let recv buffer to update the expected seq_num
            # if not control packet >> put data in recv_buffer
            self.__recv_buffer.put(inbound_segment=_rcvd_segment)

    def __schedule_active_closure(self):
        if self.__schedule_active_closure_scheder is not None:
            self.__schedule_active_closure_scheder.cancel()

        def closure():
            self.__send_buffer = None
            self.__recv_buffer = None
            self.__inbound_processor = lambda src_port, rcvd_segment: None
            self.__state = States.CLOSED
            RxProtocol.deregister(self)

        self.__schedule_active_closure_scheder = \
            threading.Timer(LAST_WAIT_DUR_S, closure)
        self.__schedule_active_closure_scheder.start()

    def __process_resp_close(self, _src_ip, _rcvd_segment):
        # there should not be any more data here, since the initiator
        # supposed to already close their send buffer
        if _rcvd_segment.is_ack() and _rcvd_segment.is_ack_num() == \
                self.__send_buffer.get_next_seq_num() and \
                self.__recv_buffer.is_expecting(
            _rcvd_segment) and self.__state == States.LAST_WORD:
            self.__send_buffer = None
            self.__recv_buffer = None
            self.__inbound_processor = lambda src_port, rcvd_segment: None
            cond = self.__state_cond
            cond.acquire()
            self.__state = States.CLOSED
            cond.notify()
            cond.release()
            RxProtocol.deregister(self)
