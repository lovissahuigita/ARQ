import collections

from FxA.util import Util


class SendBuffer:
    __logger = Util.setup_logger()

    def __init__(self, base_seq_num):
        self.__send_buffer = collections.deque()

        #
        self.__send_ackd_buffer = collections.deque()

        # sequence number of the first byte in the buffer
        self.__send_base = int(0)

    def get_base_seq_num(self):
        return self.__send_base

    def get_next_seq_num(self):
        return self.__send_base + len(self.__send_buffer)

    # put data from user space into buffer
    def put(self, data):
        pass

    # attempt to send any
    def flush(self):
        pass


# def sendSegments(self):
#
# # return number of packet sent but not yet ACK'd by receiver
# def getNotReceivedCount(self):
#
# def processControlPacket(self, ctrlPacket): # to process FRR and ACK packets
#
# def setStartRestrasmitTimerCallBack(self, cb_startRestransmitTimer):
