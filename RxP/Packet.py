class Packet:

    def __init__(self, src_port=0, dst_port=0, seq_num=0, data=None):
        if not data:
            data = []
        elif type(data) is not type([]):
            data = list(data)


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

    def _copy(self, src, dst, seq, ack, wind, chk, cyo, ccya, cack, data):
        if not data:
            data = []
        self.__src_port = src
        self.__dst_port = dst
        self.__seq_num = seq
        self.__ack_num = ack

        self.__recv_window_size = wind
        self.__checksum = chk

        self.__yo = cyo
        self.__cya = ccya
        self.__ack = cack

        self.__data = data

    def _stringify(self):
        st = ''
        st += '<src>' + str(self.__src_port) + '</src>'
        st += '<dst>' + str(self.__dst_port) + '</dst>'
        st += '<seq>' + str(self.__seq_num) + '</seq>'
        st += '<ack>' + str(self.__ack_num) + '</ack>'
        st += '<wind>' + str(self.__recv_window_size) + '</wind>'
        st += '<chk>' + str(self.__checksum) + '</chk>'
        st += '<cyo>' + str(self.__yo) + '</cyo>'
        st += '<ccya>' + str(self.__cya) + '</ccya>'
        st += '<cack>' + str(self.__ack) + '</cack>'
        st += '<data>' + str(self.__data)
        i = int(0)
        for data in self.__data:
            st += '<' + str(i) + '>' + str(data) + '</' + str(i) + '>'
            i += 1
        st += '</data>'
        return st

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

    def get_window_size(self):
        return self.__recv_window_size

    def set_window_size(self, new_size):
        self.__recv_window_size = new_size

    def set_checksum(self, checksum):
        self.__checksum = checksum

    def set_yo(self):
        self.__yo = True

    def set_cya(self):
        self.__cya = True

    def set_ack(self, ack_num):
        self.__ack = True
        self.__ack_num = ack_num

    def is_yo(self):
        return self.__yo

    def is_cya(self):
        return self.__cya

    def is_ack(self):
        return self.__ack

    def __str__(self):
        text = None
        if self.is_yo():
            text = "YO!"
        elif self.is_cya():
            text = "CYA!"
        else:
            text = "Data"
        if self.is_ack():
            if not text:
                text = "ACK"
            else:
                text += ", ACK"
        to_return = "Packet Description: \nSource Port             : "
        to_return += str(self.__src_port)
        to_return += "\nDestination Port       : "
        to_return += str(self.__dst_port)
        to_return += "\nSequence Number        : "
        to_return += str(self.__seq_num)
        to_return += "\nAcknowledgement Number : "
        to_return += str(self.__ack_num)
        to_return += "\n Window Size            : "
        to_return += str(self.__recv_window_size)
        to_return += "\n Checksum               : "
        to_return += str(self.__checksum)
        to_return += "\nType                    : "
        to_return += text
        to_return += "\nData                    : "
        to_return += str(self.__data)
        return to_return
