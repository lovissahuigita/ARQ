import collections

from FxA.util import Util


class RecvBuffer:
    __logger = Util.setup_logger()

    def __init__(self, base_seq_num, buffer_size=int(1024)):
        self.__recv_buffer = collections.deque(maxlen=buffer_size)

        # sequence number of the last received segment + its data size
        # this is our ack to confirm peer's data arrived correctly
        self.__recv_last_ackd = None

        # sequence number of the received segment in index 0
        self.__recv_base = base_seq_num

    def get_base_seq_num(self):
        return self.__recv_base

    def get_expected_seq_num(self):
        return self.__recv_base + len(self.__recv_buffer)

    def get_buffer_size(self):
        return self.__recv_buffer.maxlen

    def set_buffer_size(self, size_in_bytes):
        pass

    def get_window_size(self):
        return self.__recv_buffer.maxlen - len(self.__recv_buffer)

    def put(self, inbound_segment):
        expected_seq = self.__recv_base + len(self.__recv_buffer)
        segment_seq_num = inbound_segment.get_seq_num()

        # Sequence number is expected
        if segment_seq_num == expected_seq:
            segment_data = inbound_segment.get_data()
            if segment_data is not None:
                for data_byte in segment_data:
                    if len(self.__recv_buffer) < self.__recv_buffer.maxlen:
                        self.__recv_buffer.append(data_byte)
                    else:
                        # dropping, no more room in the buffer
                        self.__logger.info('recv buffer size: ' + str(len(
                            self.__recv_buffer)) + '/' +
                                           self.__recv_buffer.maxlen
                                           + ' dropping segment seq# ' +
                                           segment_seq_num)
        else:
            self.__logger.info(' unexpected packet: expected seq#: ' +
                               str(expected_seq) + ' received seq#:  ' +
                               inbound_segment.get_seq_num)

    def take(self, max):
        pass

