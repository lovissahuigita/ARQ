import logging
import os
import re
import sys
import traceback
from exception import NoMoreMessage, PortNumberInvalid, InvalidIP4Format, \
    UnexpectedMessage


# Housed many shared or common functions
class Util(object):
    TEXT_ENCODING = 'utf-8'
    ERROR_TAG = '[ERROR] '

    __util_logger = None

    @classmethod
    def setup_logger(cls):
        if cls.__util_logger is None:
            cls.__util_logger = logging.getLogger('debug')
            log_handler = logging.StreamHandler()
            log_formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s/%(funcName)s/%(lineno)d: '
                '%(message)s')
            log_handler.setFormatter(log_formatter)
            cls.__util_logger.addHandler(log_handler)
        cls.__util_logger.info("logger set up!")
        return cls.__util_logger

    @classmethod
    def exit_error(cls, msg):
        # print(cls.ERROR_TAG + msg, file=sys.stderr)
        exit()

    @classmethod
    def parse_args(cls, port_num, ne_ip, ne_port):
        cls.__util_logger.info(
            'NetEmu: ' + str(ne_ip) + ':' + str(ne_port) + ' port: ' +
            str(port_num))

        try:
            port_num = int(port_num)
            if (port_num < 0) or (port_num > 65535):
                raise PortNumberInvalid
        except ValueError:
            cls.exit_error(str(port_num) + ' is not a number!')
        except PortNumberInvalid:
            cls.exit_error(str(port_num) + ' is not in valid port number '
                                           'range')
        except:
            raise

        try:
            ip_pattern = re.compile(
                '(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})')
            match = ip_pattern.match(ne_ip)
            if match:
                for octet in match.groups():
                    byte = int(octet)
                    if byte < 0 or byte > 255:
                        raise InvalidIP4Format
            else:
                raise InvalidIP4Format

            ne_port = int(ne_port)
            if ne_port < 0 or ne_port > 65535:
                raise PortNumberInvalid
        except ValueError:
            cls.exit_error(str(ne_port) + ' is not a number!')
        except InvalidIP4Format:
            cls.exit_error(str(ne_ip) + ' is not a valid IPv4 format')
        except PortNumberInvalid:
            cls.exit_error(str(ne_port) + ' is not in valid port number range')
        except:
            raise

        return port_num, (ne_ip, ne_port)

    @classmethod
    def upload(cls, socket, filename):
        filesize = os.path.getsize(filename)
        cls.send_msg('SIZE ' + str(filesize), socket)

        cls.__util_logger.debug('Reading ' + filename)
        filehandle = open(filename, 'rb')
        cls.__util_logger.debug(str(filehandle))
        bytetotalsent = int(0)

        while bytetotalsent < filesize:
            dataread = filehandle.read(1024)
            bytesent = int(0)
            byteread = len(dataread)
            cls.__util_logger.debug('read ' + str(byteread) + ' bytes')
            while bytesent < byteread:
                bytesent += socket.send(dataread[bytesent:])
                cls.__util_logger.debug(
                    'sent: ' + str(bytetotalsent) + '/' + str(filesize))
            bytetotalsent += bytesent

        cls.__util_logger.debug('sent: ' + str(bytetotalsent) + '/' +
                                str(filesize))
        filehandle.close()
        print(filename + ' sent!')

    @classmethod
    def download(cls, socket, filename):
        filesize = re.split('\s+', cls.recv_msg(socket), maxsplit=1)
        cls.__util_logger.debug(str(filesize))

        if len(filesize) == 2 and filesize[0] == 'SIZE':
            try:
                filesize = int(filesize[1])
            except:
                cls.__util_logger.debug('\n' + traceback.format_exc())
                raise UnexpectedMessage
        else:
            raise UnexpectedMessage

        cls.__util_logger.debug('Writing ' + filename + ' of size ' +
                                str(filesize) + ' bytes')
        filehandle = open(filename, 'wb')
        cls.__util_logger.debug(str(filehandle))
        bytetotalwritten = int(0)

        while bytetotalwritten < filesize:
            datarcvd = socket.recv(4096)
            bytewritten = int(0)
            bytercvd = len(datarcvd)
            cls.__util_logger.debug('received ' + str(bytercvd) + ' bytes')
            while bytewritten < bytercvd:
                bytewritten += filehandle.write(datarcvd[bytewritten:])
                cls.__util_logger.debug(
                    'writting ' + str(bytetotalwritten) + '/' + str(filesize))
            bytetotalwritten += bytewritten

        cls.__util_logger.debug(
            'writting ' + str(bytetotalwritten) + '/' + str(filesize))
        filehandle.close()
        print(filename + ' received!')

    @classmethod
    def send_msg(cls, msg, socket):
        sent = int(0)
        msg += '\n'
        cls.__util_logger.debug('sending ' + msg)
        msg = msg.encode(cls.TEXT_ENCODING)
        msglen = len(msg)
        while sent < msglen:
            sent += socket.send(msg[sent:])

    @classmethod
    def recv_msg(cls, socket):
        msg = socket.recv(1)
        if len(msg) == 0:
            cls.__util_logger.debug(msg)
            raise NoMoreMessage
        decoded = msg.decode(cls.TEXT_ENCODING)
        while not decoded[len(decoded) - 1] == '\n':
            msg = socket.recv(1)
            if len(msg) == 0:
                cls.__util_logger.debug(msg)
                raise NoMoreMessage
            decoded += msg.decode(cls.TEXT_ENCODING)
        cls.__util_logger.debug(decoded)
        return decoded.strip()
