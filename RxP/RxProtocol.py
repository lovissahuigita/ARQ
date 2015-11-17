import socket
from random import randint
from exception import RxPException

__author__ = 'Lovissa Winyoto'


class rxprotocol:
    __sockets = {}  # key: (client_ip_addr, client_port_num) value: socket
    __port_number = {}  # key: (client_ip_addr, client_port_num) value: my port number
    __port_to_addr = {} # key: my port number value: (client_ip_addr, client_port_num)

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(address)  # TODO: what is the address

    @classmethod
    def get_available_port(cls):
        port = randint(0,65536)
        while port in cls.__port_to_addr.keys():
            port = randint(0,65536)
        return port

    @classmethod
    def register(cls, socket, port, addr_port = (0, 0)):
        if cls.__sockets[addr_port] is None:
            cls.__sockets[addr_port] = socket
            if cls.__port_to_addr[port] is None:  # if port is available (which it should be)
                cls.__sockets[addr_port] = socket
                cls.__port_number[addr_port] = port
                cls.__port_to_addr[port] = addr_port
                return True
            return False
        else:
            raise RxPException(105); # TODO: correct number?

    @classmethod
    def __receive(cls):
        received = cls.udp_sock.recvfrom(udp_port_num) # TODO: Update the port num
        data = received[0]
        addr_port = received[1]
        if addr_port in cls.__sockets.keys():
            dst_socket = cls.__sockets[addr_port]
        else:
            dst_socket = cls.__sockets[cls.__port_to_addr[addr_port[1]]]
        dst_socket._process_rcvd(addr_port[0], data)



    @classmethod
    def send(cls, data, address):
        cls.udp_sock.sendto(data, address)
