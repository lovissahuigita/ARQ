import collections
from FxA.util import Util
from RxP.Packeter import Packeter


class SendBuffer:
    __logger = Util.setup_logger()

    def __init__(self):
        self.__send_buffer = collections.deque()

        # last ack_num rcvd from peer
        self.__last_ackd = 0

    # Remove any segment sent successfully from buffer
    # now the ACK_NUM is what the peer expect next, not what they received last
    # think if the last_acknum overflow, such that self.__last_ackd = 65535 and
    # last_acknum is 5
    def notify_ack(self, last_acknum):
        #TODO: below will not work, need another way...
        if last_acknum > self.__last_ackd:
            self.__last_ackd = last_acknum
            buffer = self.__send_buffer
            while len(buffer) > 0 and buffer[0].get_seq_num() < last_acknum:
                buffer.popleft()

    # return    next sequence number
    def put(self, src_port, dst_port, seq_num, data):
        for segment in Packeter.packetize(
                src_port=src_port,
                seq_num=seq_num,
                dst_port=dst_port,
                data=data
        ):
            self.__send_buffer.append(segment)
        return seq_num + len(data)

    # put ack_num and ack_bit and checksum just before pushing segments to
    # lower layer
    def take(self, ack_num, max_segment=0):
        buffer = self.__send_buffer
        if max_segment == 0:
            max_segment = len(buffer)
        else:
            max_segment = min(max_segment, len(buffer))
        segments = []
        for i in range(0, max_segment):
            prepare = buffer[i]
            prepare.set_ack(ack_num=ack_num)
            # TODO: how to compute checksum here?
            segments.append(prepare)
        return segments

