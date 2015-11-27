import collections
import threading
import random

from FxA.util import Util
from RxP.Packeter import Packeter
from RxP import rxpsocket


class SendBuffer:
    __logger = Util.setup_logger()

    def __init__(self, src_port, dst_port):
        """ Created a new send buffer
        :return: None
        """
        self.__send_buffer = collections.deque(maxlen=1)
        self.__last_ackd = 0
        self.__logger.info("Send Buffer created")
        self.__next_seq_num = 0
        self.__src_port = src_port
        self.__dst_port = dst_port
        self.__class_lock = threading.Lock()
        self.__full_cond = threading.Condition(self.__class_lock)
        self.__resize_cond = threading.Condition(self.__class_lock)


    def get_next_seq_num(self):
        return self.__next_seq_num

    def commit(self, buffer_size=1024):
        self.__resize_cond.acquire()
        self.__send_buffer = collections.deque(
            maxlen=buffer_size,
            iterable=self.__send_buffer
        )
        self.__resize_cond.release()

    def generate_seq_num(self):
        self.__next_seq_num = random.randint(0, rxpsocket.MAX_SEQ_NUM - 1) + 1

    def notify_ack(self, new_acknum):
        """ Remove any segment sent successfully from buffer. now the
        ACK_NUM is what the peer expect next, not what
        they received last think if the last_acknum overflow, such that
        self.__last_ackd = 65535 and last_acknum is 5
        :param new_acknum: the newest acknowledgement number
        :return: None
        """
        self.__full_cond.acquire()
        is_overflow = self.__last_ackd - new_acknum > 2147483647
        normal = new_acknum > self.__last_ackd
        if normal or is_overflow:
            self.__last_ackd = new_acknum
            buffer = self.__send_buffer
            while len(buffer) > 0 and ((buffer[0].get_seq_num() <
                new_acknum) or (is_overflow and
                buffer[0].get_seq_num() > new_acknum)):
                # TODO: kayaknya bener sih
                buffer.popleft()
                print('popping')
        self.__full_cond.notify()
        self.__full_cond.release()
        self.__logger.info("NOTIFY new ack: %d" % new_acknum)

    def __put_control(self, yo=False, cya=False):
        self.__send_buffer.append(Packeter.control_packet(
            src_port=self.__src_port,
            dst_port=self.__dst_port,
            seq_num=self.__next_seq_num,
            yo=yo,
            cya=cya
        ))
        self.__increment_next_seq_num()

    def __put_data(self, data):
        for segment in Packeter.packetize(
                src_port=self.__src_port,
                dst_port=self.__dst_port,
                seq_num=self.__next_seq_num,
                data=data
        ):
            self.__send_buffer.append(segment)
        if data:
            for i in range(0, len(data)):
                self.__increment_next_seq_num()

    def put(self, yo=False, cya=False, data=None):
        """ Puts the data in the send buffer.
        Returns the next sequence number
        :param data: the data being sent
        :return: the sequence number + length of the data
        """

        maxlen = self.__send_buffer.maxlen
        self.__logger.debug('send buffer size: ' + str(len(
            self.__send_buffer)) + '/' + str(self.__send_buffer.maxlen))
        # self.__full_cond.acquire()
        # self.__full_cond.wait_for(
        #     predicate=lambda: len(self.__send_buffer) < maxlen
        # )
        if maxlen and len(self.__send_buffer) == maxlen:
            raise OverflowError
        if yo and not cya or cya and not yo:
            self.__put_control(yo=yo, cya=cya)
        elif not yo and not cya:
            self.__put_data(data=data)
        # self.__full_cond.release()
        self.__logger.info("PUT data in the send buffer")

    def take(self, ack, ack_num, self_rcv_wind_size, max_segment=0):
        """ Put ack_num and ack_bit and checksum just before pushing
        segments to lower layer
        :param ack_num: the acknowledgement number
        :param max_segment: the maximum segment size
        :return: the segments
        """
        buffer = self.__send_buffer
        # self.__class_lock.acquire()
        if len(buffer) == 0:
            self.put()
        max_segment = max(min(max_segment, len(buffer)), 1)
        # if max_segment == len(buffer) and max_segment > 1:
        #     max_segment -= 1
        segments = []
        self.__logger.debug("Max Segment: " + str(max_segment) + ' Bufferlen: '
            '' + str(len(buffer)))
        assert max_segment > 0
        assert len(buffer) > 0
        for i in range(0, max_segment):
            if i < len(buffer):
                prepare = buffer[i]
                if ack:
                    prepare.set_ack(ack_num=ack_num)
                prepare.set_window_size(new_size=self_rcv_wind_size)
                Packeter.compute_checksum(prepare)
                segments.append(prepare)
        # self.__class_lock.release()
        self.__logger.info("TAKE from the send buffer")
        return segments

    def __increment_next_seq_num(self):
        self.__next_seq_num = (self.__next_seq_num + 1) % rxpsocket.MAX_SEQ_NUM
