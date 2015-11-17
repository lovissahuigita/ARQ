import collections


class SendBuffer:
    def __init__(self, base_seq_num):
        self.__send_buffer = collections.deque()
        self.__send_ackd_buffer = collections.deque()
        self.__send_base = int(0)

    def get_base_seq_num(self):
        return self.__send_base

    # put data from user space into buffer
    def put(self, data):
        pass

    def send_yo(self):
        pass

    def send_syn_yo(self):


# def sendSegments(self):
#
# # return number of packet sent but not yet ACK'd by receiver
# def getNotReceivedCount(self):
#
# def processControlPacket(self, ctrlPacket): # to process FRR and ACK packets
#
# def setStartRestrasmitTimerCallBack(self, cb_startRestransmitTimer):
