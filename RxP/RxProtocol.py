import socket
import threading
from random import randint
import time
from exception import RxPException, NetworkReinitException

__author__ = 'Lovissa Winyoto'


class RxProtocol:
    __sockets = {}  # key: (client_ip_addr, client_port_num) value: socket
    __port_number = {}  # key: (client_ip_addr, client_port_num) value: my
    # port number
    __port_to_addr = {}  # key: my port number value: (client_ip_addr,
    # client_port_num)

    # socket that glued RxP layer with network layer
    __udp_sock = None

    # first hop of every segment sent out of this layer
    __proxy_addr = None

    BUFF_SIZE = int(2048)

    @classmethod
    def open_network(cls, udp_port, proxy_addr):
        if cls.__udp_sock is not None:
            raise NetworkReinitException()
        else:
            cls.__udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cls.__udp_sock.bind(('', udp_port))
            cls.__proxy_addr = proxy_addr

    @classmethod
    def get_available_port(cls):
        port = randint(0, 65536)
        while port in cls.__port_to_addr.keys():
            port = randint(0, 65536)
        return port

    @classmethod
    def is_available_port(cls, port_num):
        return port_num in cls.__port_to_addr

    @classmethod
    def register(cls, soc, port=get_available_port(), addr_port=(0, 0)):
        if cls.__sockets[addr_port] is None:
            cls.__sockets[addr_port] = soc
            if cls.__port_to_addr[
                port] is None:  # if port is available (which it should be)
                cls.__sockets[addr_port] = soc
                cls.__port_number[addr_port] = port
                cls.__port_to_addr[port] = addr_port
                return True
            return False
        else:
            raise RxPException(105)  # TODO: correct number?

    @classmethod
    def unregister(cls, soc):
        port_addr = (soc._get_ip_address, soc._get_port_num)
        if port_addr in cls.__sockets:
            deleted = cls.__sockets[port_addr]
            my_port = cls.__port_number[port_addr]
            del cls.__sockets[port_addr]
            del cls.__port_number[port_addr]
            del cls.__port_to_addr[my_port]
            return deleted
        else:
            return None

    @classmethod
    def __receive(cls):
        while True:
            received = cls.__udp_sock.recvfrom(cls.BUFF_SIZE)
            data = received[0]
            addr_port = received[1]
            if addr_port in cls.__sockets.keys():
                dst_socket = cls.__sockets[addr_port]
            else:
                dst_socket = cls.__sockets[cls.__port_to_addr[addr_port[1]]]
            dst_socket._process_rcvd(addr_port[0], data)

    @classmethod
    def send(cls, address, data):
        cls.__udp_sock.sendto(data, address)

    # Retransmit @msg every @ms_interval until @stop_func return True
    #
    # @dest_addr    address of the receiver
    # @msg          message to be transmitted
    # @ms_interval  interval between retransmission in ms
    # @stop_func    function with no param that return True when
    #               this function should stop
    @classmethod
    def ar_send(cls, dest_addr, msg, ms_interval, stop_func=lambda: False):
        def dispatcher():
            sec_interval = ms_interval / 1000
            cls.send(dest_addr, msg)
            time.sleep(sec_interval)
            while not stop_func():
                cls.send(dest_addr, msg)
                time.sleep(sec_interval)

        threading.Thread(target=dispatcher).start()
