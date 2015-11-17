# raised when '\n' has not been received but sender no longer sending file
class NoMoreMessage(Exception):
    pass


class PortNumberInvalid(Exception):
    pass


class InvalidIP4Format(Exception):
    pass


class UnexpectedMessage(Exception):
    pass

class NetworkReinitException(Exception):
    pass


class ArgumentCountException(Exception):
    def __init__(self, commandname='', argcountreq=1, argsymbol=()):
        self.__name = str(commandname)
        self.__reqcount = int(argcountreq)
        self.__argsymbol = argsymbol

    def __str__(self):
        return '\'' + self.__name + '\' requires ' + str(self.__reqcount) + \
               ' argument(s) ' + str(self.__argsymbol)


class RxPException(Exception):
    # Form -> errno: errmsg
    ERROR = {
        100: 'Port number in use (cannot bind error).',
        101: 'Connection refused (no listening socket exists).',
        102: 'Not connected (no connection error).',
        103: 'Socket is already closed.',
        104: 'Socket is already connected.',
        105: 'Socket already bound.',
        106: 'Socket is in use (socket still active).',
        107: 'Connection force closed by peer.',
        108: 'Invalid state.'
    }

    def __init__(self, errno):
        self.__errno = errno
        self.__msg = self.ERROR.get(errno)

    def msg(self):
        return self.__msg

    def errno(self):
        return self.__errno

    def __str__(self):
        return str(self.__errno) + ' ' + self.__msg
