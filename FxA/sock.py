# socket wrapper
# map tcp socket function call to rxp socket function call
import socket

from exception import RxPException


class sock:
    def __init__(self, udp_port, proxy_addr=('127.0.0.1', 13000)):
        self.__udp_port = udp_port
        self.__proxy_addr = proxy_addr
        try:
            self.__s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except:
            raise

    def connect(self, address):
        try:
            self.__s.connect(address)
        except OSError as err:
            print(str(err))
            if err.winerror == 10038:
                raise RxPException(103)
            elif err.winerror == 10056:
                raise RxPException(104)
            elif err.winerror == 10048:
                raise RxPException(106)
            elif err.winerror == 10061:
                raise RxPException(101)
            else:
                print(self.__s)
                raise
        except:
            raise

    def bind(self, address):
        try:
            self.__s.bind(address)
        except:
            raise

    def listen(self, maxQC):
        try:
            self.__s.listen(maxQC)
        except:
            raise

    def accept(self):
        try:
            ret = sock(self.__udp_port, self.__proxy_addr)
            ret.__s, client_addr = self.__s.accept()
            ret.__proxy_addr = self.__proxy_addr
            return ret, client_addr
        except OSError as err:
            if int(err.winerror) == 10038:
                raise RxPException(103)
            else:
                raise

    def send(self, dataBytes):
        try:
            return self.__s.send(dataBytes)
        except OSError as err:
            if int(err.winerror) == 10057:
                raise RxPException(102)
            elif int(err.winerror) == 10038:
                raise RxPException(103)
            elif int(err.winerror) == 10054:
                raise RxPException(107)
            else:
                raise

    def recv(self, maxBytesRead):
        try:
            return self.__s.recv(maxBytesRead)
        except OSError as err:
            if int(err.winerror) == 10054:
                raise RxPException(107)
            else:
                raise

    # set receive buffer size to x segment
    def set_buffer_size(x):
        pass

    def close(self):
        try:
            self.__s.close()
        except:
            raise

    def __str__(self):
        return str(self.__s)

    def __repr__(self):
        return str(self.__s)
