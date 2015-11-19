class Packet:
    def __init__(self, src_port, dst_port, seq_num=0, data=None):
        if not data:
            data = []
        self.__src_port = src_port
        self.__dst_port = dst_port
        self.__seq_num = seq_num
        self.__ack_num = 0

        self.__recv_window_size = 0
        self.__checksum = 0

        self.__yo = False
        self.__cya = False
        self.__ack = False

        self.__data = data

    def get_data(self):
        return self.__data

    def get_dst_port(self):
        return self.__dst_port

    def get_src_port(self):
        return self.__src_port

    def get_checksum(self):
        return self.__checksum

    def get_seq_num(self):
        return self.__seq_num

    def get_ack_num(self):
        return self.__ack_num

    def set_checksum(self, checksum):
        self.__checksum = checksum

    def set_yo(self):
        self.__yo = True

    def set_cya(self):
        self.__cya = True

    def set_ack(self, ack_num):
        self.__ack = True
        self.__ack_num = ack_num
