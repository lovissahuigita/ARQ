import socket
import threading
import thread
from random import randint
from RxP.Packeter import Packeter
#import time
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
        """
        Opens a UDP socket.
        :param udp_port: the udp port used to send and received
        :param proxy_addr: proxy address
        :return: None
        """
        if cls.__udp_sock is not None:
            raise NetworkReinitException()
        else:
            cls.__udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            cls.__udp_sock.bind(('', udp_port))
            cls.__proxy_addr = proxy_addr
            thread.start_new_thread(cls.__receive, "Thread-Receive")

    @classmethod
    def get_available_port(cls):
        """
        Get a currently available port number
        :return: the port number
        """
        port = randint(0, 65536)
        while port in cls.__port_to_addr.keys():
            port = randint(0, 65536)
        return port

    @classmethod
    def is_available_port(cls, port_num):
        """
        Checks whether a port number is available
        :param port_num: the port number to be checked
        :return: True if the port is available, False otherwise
        """
        return port_num in cls.__port_to_addr

    @classmethod
    def register(cls, soc, port=get_available_port(), addr_port=(0, 0)):
        """
        Register a new socket to the protocol so it knows which are active
        :param soc: the socket
        :param port: the port of the socket
        :param addr_port: the address of the port of the socket
        :return: True if the socket is registered, False otherwise
        """
        # TODO: who will set the port number field on socket class?
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
    def deregister(cls, soc):
        """
        Delete a socket from the list of active socket
        :param soc: the socket to be deleted/deregistered
        :return: the deleted socket if it exists, None otherwise
        """
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
        """
        Blocking call to receive from the UDP socket and send it to the socket.
        Infinite server.
        :return: None
        """
        while True:
            received = cls.__udp_sock.recvfrom(cls.BUFF_SIZE)
            data = Packeter.objectize(received[0])
            addr_port = received[1]
            if addr_port in cls.__sockets.keys():
                dst_socket = cls.__sockets[addr_port]
            else:
                dst_socket = cls.__sockets[cls.__port_to_addr[addr_port[1]]]
            dst_socket._process_rcvd(addr_port[0], data)

    @classmethod
    def send(cls, address, packet):
        """
        Interface the socket and UDP, to send a packet through the UDP by first binarizing the packet
        :param address: the address to send the packet
        :param packet: the packet to be sent
        :return: None
        """
        bin = Packeter.binarize(packet)
        cls.__udp_sock.sendto(bin, address)

    @classmethod
    def ar_send(cls, dest_addr, msg, stop_func=lambda: False):
        """

        :param dest_addr: address of the receiver
        :param msg: message to be transmitted
        :param stop_func: function with no param that return True when this function should stop
        :return: None
        """
        def dispatcher():
            cls.send(dest_addr, msg)
            while not stop_func():
                cls.send(dest_addr, msg)

        threading.Thread(target=dispatcher).start()
