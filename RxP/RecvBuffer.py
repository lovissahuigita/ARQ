import collections
import threading
from FxA.util import Util
# All Units of size are in segments!!!
from RxP import rxpsocket
from RxP.Packeter import Packeter


class RecvBuffer:
    __logger = Util.setup_logger()

    def __init__(self):
        """ Creates a new receive buffer
        :return: None
        """
        class_lock = threading.Lock()
        self.__empty_cond = threading.Condition(class_lock)
        self.__resize_cond = threading.Condition(class_lock)
        self.__recv_buffer = collections.deque(maxlen=1)
        self.__next_ack_num = 0
        self.__logger.info(
            "Receive Buffer has been created. Size: %d" %
            self.__recv_buffer.maxlen)

    def commit(self, buffer_size=32768):
        buffer_size *= Packeter.MSS
        self.__resize_cond.acquire()
        self.__recv_buffer = collections.deque(
            maxlen=buffer_size,
            iterable=self.__recv_buffer
        )
        self.__resize_cond.release()

    def sync_ack_num(self, first_seq_num):
        self.__next_ack_num = first_seq_num
        self.__increment_next_ack_num()

    def get_expected_seq_num(self):
        return self.__next_ack_num

    def get_buffer_size(self):
        """ Get the size of the buffer
        :return: The size of the buffer
        """
        return min(self.__recv_buffer.maxlen, 2147483647)

    def set_buffer_size(self, size_in_segment):
        """ Sets the size of the buffer
        :param size_in_segment: the desired size of the buffer
        :return: None
        """
        size_in_segment *= Packeter.MSS
        self.__resize_cond.acquire()
        self.__resize_cond.wait_for(len(self.__recv_buffer) < size_in_segment)
        # once the recv buffer contains less segment than requested new size:
        self.__recv_buffer = collections.deque(
            iterable=self.__recv_buffer,
            maxlen=size_in_segment
        )
        self.__resize_cond.release()
        self.__logger.info(
            "SET Buffer Size is: %d" % self.__recv_buffer.maxlen)

    def get_window_size(self):
        """ Returns current window size in segment
        :return: the size of the window
        """
        return self.__recv_buffer.maxlen - len(self.__recv_buffer)

    def put(self, inbound_segment):
        """ Puts a segment into the receive buffer
        :param inbound_segment: the segment to be put
        :return: the acknowledgement number
        """
        buffer = self.__recv_buffer
        self.__logger.info("Buffer Size: %d" % len(buffer))
        self.__empty_cond.acquire()
        if len(buffer) < buffer.maxlen and self.is_expecting(inbound_segment):
            if inbound_segment.is_yo() or inbound_segment.is_cya():
                self.__increment_next_ack_num()
            else:
                data = inbound_segment.get_data()
                if data:
                    for byte in data:
                        buffer.append(byte)
                    for i in range(0, len(data)):
                        self.__increment_next_ack_num()
            self.__logger.info("Buffer Size: %d" % len(buffer))
        self.__empty_cond.notify()
        self.__empty_cond.release()

    def take(self, max_read):
        """ Takes buffered segment's data.
        :param max_read: the maximum byte stream read
        :return: the list of data bytes with at most max_read long
        """
        data = []
        buffer = self.__recv_buffer
        self.__empty_cond.acquire()
        self.__logger.debug('RecvContent: ' + str(self.__recv_buffer))
        self.__empty_cond.wait_for(lambda: len(buffer) > 0)
        front = buffer[0]
        assert len(buffer) > 0
        while len(buffer) > 0 and len(data) < max_read:
            if front:
                data.append(front)
                buffer.popleft()
                if len(buffer) > 0:
                    front = buffer[0]
        self.__resize_cond.notify()
        self.__empty_cond.release()
        self.__logger.info("TAKE data from receive buffer")
        self.__logger.debug(str(data))
        ret = bytearray()
        for byte in data:
            ret.append(byte)
        return ret

    def __increment_next_ack_num(self):
        self.__next_ack_num = (self.__next_ack_num + 1) % rxpsocket.MAX_SEQ_NUM

    def is_expecting(self, segment):
        return self.__next_ack_num == segment.get_seq_num()
