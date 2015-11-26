import socket
import threading
from random import randint
from RxP.Packeter import Packeter
from FxA.util import Util
from exception import RxPException, NetworkReinitException, InvalidPeerAddress

__author__ = 'Lovissa Winyoto'


class RxProtocol:
    # for debugging purposes
    __logger = Util.setup_logger()

    __sockets = {}
    # key	: my port number
    # value : the socket

    __addr_port_pairs = {}
    # key	: the socket
    # value : client (address:port)

    __ports = {}
    # key   : client (address:port)
    # value : my port number


    # socket that glued RxP layer with network layer
    __udp_sock = None

    # first hop of every segment sent out of this layer
    __proxy_addr = None

    @classmethod
    def __debug_state(cls):
        cls.__logger.debug("__sockets: " + str(cls.__sockets))
        cls.__logger.debug("__port_number: " + str(cls.__port_number))
        cls.__logger.debug("__port_to_addr: " + str(cls.__port_to_addr))

    BUFF_SIZE = int(2048)

    @classmethod
    def open_network(cls, udp_port, proxy_addr):
        """ Opens a UDP socket.
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
            recvthread = threading.Thread(target=cls.__receive)
            recvthread.start()
        cls.__logger.info("Network Opened")

    @classmethod
    def get_available_port(cls):
        """Get a currently available port
        :return: an available port number
        """
        port = randint(0, 65536)
        while port in cls.__sockets.keys():
            port = randint(0, 65536)
        cls.__logger.info("GOT available port: %d" % port)
        return port

    @classmethod
    def is_available_port(cls, port):
        """ Checks whether a port number is available
        :param port_num: the port number to be checked
        :return: True if the port is available, False otherwise
        """
        return port not in cls.__sockets.keys()

    @classmethod
    def register(cls, socket, port=None):
        """Register a new socket to the protocol during bind state.
        The socket and the port does not know its peer IP address and port
        number yet
        :param socket: the socket to be registered
        :param port: our port to be registered, default value: None >> random
        port number will be assigned to the socket
        :return: True if the socket is registered, False otherwise
        """
        # assign a random port number
        if not port:
            port = cls.get_available_port()
            socket._set_addr(('127.0.0.1', port))

        # register the port number and socket
        if port not in cls.__sockets.keys():
            cls.__sockets[port] = socket
            cls.__logger.info(
                "Socket %d is registered in port %d" % (socket, port))
            return True
        else:
            cls.__logger.info("Socket %d is NOT registered" % socket)
            return False

    @classmethod
    def register_peer(cls, port, peer_addr):
        """Register a peer's IP address and port number to the corresponding
        socket and port.
        :param port: the port number where the peer address is registered
        :param peer_addr: the peer's IP address and port number pair to be
        registered
        :return: True if the peer is registered, False otherwise
        """
        socket = None
        if not ((peer_addr is None) or (peer_addr is (None, None))):
            if port in cls.__sockets.keys():
                socket = cls.__sockets[port]
                cls.__addr_port_pairs[socket] = peer_addr
                cls.__ports[peer_addr] = port
                cls.__logger.info(
                    "REGISTERED IP:port %s to socket %d in port %d" % (
                        str(peer_addr), socket, port))
                return True
            else:
                raise RxPException(105)
            return False
        else:
            raise InvalidPeerAddress()

    @classmethod
    def deregister(cls, socket):
        """Free a port from binding with a socket.
        :param socket: the socket that will unbind a port
        :return: The deleted socket from the list of active sockets if it
        exists, None otherwise
        """
        peer_addr = cls.__addr_port_pairs.get(socket)
        port = cls.__ports.get(peer_addr)
        deleted = None
        msg = ""
        if socket in cls.__addr_port_pairs.keys():
            del cls.__addr_port_pairs[socket]
            msg += "\nIP:port OK"
        if peer_addr in cls.__ports.keys():
            del cls.__ports[peer_addr]
            msg += "\nPorts OK"
        if port in cls.__sockets.keys():
            deleted = cls.__sockets[port]
            del cls.__sockets[port]
            msg += "\nSockets OK"
        cls.__logger.info("DEREGISTERED: %s" % msg)
        return deleted

    @classmethod
    def __receive(cls):
        """ Blocking call to receive from the UDP socket and send it to the
        socket.
        Infinite server.
        :return: None
        """

        while True:
            # Receive from UDP
            cls.__logger.info("RxP waits to RECEIVE")
            received = cls.__udp_sock.recvfrom(cls.BUFF_SIZE)
            cls.__logger.info("RxP receives something...")

            # Objectize the segment (packet) and get the source IP:port
            segment = Packeter.objectize(received[0])
            my_port = (segment.get_dst_port())
            peer_addr = received[1]

            if peer_addr in cls.__sockets.keys():
                dest_socket = cls.__sockets.get(peer_addr)
            else:
                dest_socket = cls.__sockets.get(my_port)
            dest_socket._process_rcvd(peer_addr[0], segment)
            cls.__logger.info("RxP RECEIVED:\nsrc: %s\ndata: %s" % (
            str(peer_addr), str(segment)))

    @classmethod
    def send(cls, address, packet):
        """ Interface the socket and UDP, to send a packet through the UDP by
        first binarizing the packet
        :param address: the address to send the packet
        :param packet: the packet to be sent
        :return: None
        """
        cls.__debug_state()
        bin = Packeter.binarize(packet)
        cls.__logger.info("RxProtocol TRIES to send something")
        cls.__udp_sock.sendto(bin, cls.__proxy_addr)
        cls.__logger.info("RxProtocol SENT something to " + str(address))

    @classmethod
    def ar_send(cls, dest_addr, msg, stop_func=lambda: False):
        # TODO: Van ini apaan
        """
        :param dest_addr: address of the receiver
        :param msg: message to be transmitted
        :param stop_func: function with no param that return True when this
        function should stop
        :return: None
        """

        def dispatcher():
            # TODO: function inside of a function?
            cls.send(dest_addr, msg)
            while not stop_func():
                cls.send(dest_addr, msg)
            threading.Thread(target=dispatcher).start()
