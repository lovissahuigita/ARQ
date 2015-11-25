import collections
import threading

from FxA.util import Util


# All Units of size are in segments!!!
class RecvBuffer:
    __logger = Util.setup_logger()

    def __init__(self, buffer_size=int(1024)):
        """ Creates a new receive buffer
        :param buffer_size: the size of the buffer
        :return: None
        """
        class_lock = threading.Lock()
        self.__empty_cond = threading.Condition(class_lock)
        self.__resize_cond = threading.Condition(class_lock)
        self.__recv_buffer = collections.deque(maxlen=buffer_size)
        self.__logger.info("Receive Buffer has been created. Size: %d" % self.__recv_buffer.maxlen)

    # return buffer capacity in segment
    def get_buffer_size(self):
        """ Get the size of the buffer
        :return: The size of the buffer
        """
        self.__logger.info("Get Buffer Size: %d" % min(self.__recv_buffer.maxlen, 2147483647))
        return min(self.__recv_buffer.maxlen, 2147483647)

    def set_buffer_size(self, size_in_segment):
        """ Sets the size of the buffer
        :param size_in_segment: the desired size of the buffer
        :return: None
        """
        self.__resize_cond.acquire()
        self.__resize_cond.wait_for(len(self.__recv_buffer) < size_in_segment)
        # once the recv buffer contains less segment than requested new size:
        self.__recv_buffer = collections.deque(
            iterable=self.__recv_buffer,
            maxlen=size_in_segment
        )
        self.__resize_cond.release()
        self.__logger.info("Buffer Size is: %d" % self.__recv_buffer.maxlen)

    def get_window_size(self):
        """ Returns current window size in segment
        :return: the size of the window
        """
        self.__logger.info("Window Size: %d" % self.__recv_buffer.maxlen - len(self.__recv_buffer))
        return self.__recv_buffer.maxlen - len(self.__recv_buffer)

    def put(self, ack_num, inbound_segment):
        """ Puts a segment into the receive buffer
        :param ack_num: the acknowledgement number of the segment
        :param inbound_segment: the segment to be put
        :return: the acknowledgement number
        """
        buffer = self.__recv_buffer
        self.__logger.info("Buffer Size: %d" % len(buffer))
        self.__empty_cond.acquire()
        if len(buffer) < buffer.maxlen and inbound_segment.get_seq_num() == \
                ack_num:
            buffer.append(inbound_segment)
            self.__logger.info("Buffer Size: %d" % len(buffer))
            ack_num += max(len(inbound_segment.get_data()), 1)
        self.__empty_cond.notify()
        self.__empty_cond.release()
        return ack_num

    def take(self, max_read):
        """ Takes buffered segment's data.
        :param max_read: the maximum byte stream read
        :return: the list of data bytes with at most max_read long
        """
        data = []
        buffer = self.__recv_buffer
        self.__empty_cond.acquire()
        front = buffer[0].get_data()
        self.__empty_cond.wait_for(len(buffer) > 0)
        while len(buffer) > 0 and len(data) + len(front) < max_read:
            if front is not None:
                for byte in front:
                    data.append(byte)
            buffer.popleft()
            front = buffer[0].get_data()
        self.__resize_cond.notify()
        self.__empty_cond.release()
        self.__logger.info("Data: " + data)
        return data
