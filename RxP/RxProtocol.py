import socket

__author__ = 'Lovissa Winyoto'


class rxprotocol:
    __sockets = {}
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @classmethod
    def register(cls, socket):
        port_num = socket.get_port_num()
        if cls.__sockets[port_num] is None:
            cls.__sockets[port_num] = socket
            return True
        else:
            return False
