import collections
from FxA.util import Util
from RxP.Packeter import Packeter


class SendBuffer:
    __logger = Util.setup_logger()

    def __init__(self):
        self.__send_buffer = collections.deque()

        # last ack_num rcvd from peer
        self.__last_ackd = 0


    def get_last_ackd(self):
        return self.__last_ackd


    def notify_ack(self, new_acknum):
        """
        Remove any segment sent successfully from buffer. now the ACK_NUM is what the peer expect next, not what
        they received last think if the last_acknum overflow, such that self.__last_ackd = 65535 and last_acknum is 5
        :param new_acknum: the newest acknowledgement number
        :return: None
        """
        is_overflow = self.__last_ackd - new_acknum > 2147483647
        if new_acknum > self.__last_ackd or is_overflow:
            self.__last_ackd = new_acknum
            buffer = self.__send_buffer
            while len(buffer) > 0 and (buffer[0].get_seq_num() < new_acknum or (is_overflow and buffer[0].get_seq_num() > new_acknum)):  #TODO: kayaknya bener sih
                buffer.popleft()

    def put(self, src_port, dst_port, seq_num, data):
        """
        Return the next sequence number
        :param src_port: the source port
        :param dst_port: the destination port
        :param seq_num: the sequence number
        :param data: the data being sent
        :return: the sequence number + length of the data
        """
        for segment in Packeter.packetize(
                src_port=src_port,
                seq_num=seq_num,
                dst_port=dst_port,
                data=data
        ):
            self.__send_buffer.append(segment)
        return seq_num + len(data)

    def take(self, ack_num, max_segment=0):
        """
        Put ack_num and ack_bit and checksum just before pushing segments to lower layer
        :param ack_num: the acknowledgement number
        :param max_segment: the maximum segment size
        :return: the segments
        """
        buffer = self.__send_buffer
        if max_segment == 0:
            max_segment = len(buffer)
        else:
            max_segment = min(max_segment, len(buffer))
        segments = []
        for i in range(0, max_segment):
            prepare = buffer[i]
            prepare.set_ack(ack_num=ack_num)
            Packeter.compute_checksum(prepare)
            segments.append(prepare)
        return segments

