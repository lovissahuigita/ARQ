import collections
from FxA.util import Util


# All Units of size are in segments!!!
class RecvBuffer:
    __logger = Util.setup_logger()

    def __init__(self, buffer_size=int(1024)):
        self.__recv_buffer = collections.deque(maxlen=buffer_size)

    # return buffer capacity in segment
    def get_buffer_size(self):
        return self.__recv_buffer.maxlen

    def set_buffer_size(self, size_in_bytes):
        pass

    # return current window size in segment
    def get_window_size(self):
        return self.__recv_buffer.maxlen - len(self.__recv_buffer)

    def put(self, ack_num, inbound_segment):
        buffer = self.__recv_buffer
        if len(buffer) < buffer.maxlen and inbound_segment.get_seq_num() == \
                ack_num:
            buffer.append(inbound_segment)
            ack_num += max(len(inbound_segment.get_data()), 1)
        return ack_num

    # Take buffered segment's data.
    #
    # @max_read          max number of bytes to be read
    # return data   list of data bytes with at most @max_read long
    def take(self, max_read):
        data = []
        buffer = self.__recv_buffer
        front = buffer[0].get_data()
        while len(buffer) > 0 and len(data) + len(front) < max_read:
            if front is not None:
                for byte in front:
                    data.append(byte)
            buffer.popleft()
            front = buffer[0].get_data()
        return data
