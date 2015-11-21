from RxP.Packet import Packet

__author__ = 'Lovissa Winyoto'


class Packeter:
    MSS = 544  # in bytes

    # breakdown data into packets
    #  input data is already in binary 
    # this method breaks the binary to 544 bytes def
    @classmethod
    def packetize(cls, src_port, dst_port, seq_num, data):
        packet_list = []
        leftover = len(data)
        start = 0
        end = (cls.MSS if len(data) >= cls.MSS else len(data)) - 1
        while leftover > 0:
            seq_num += end
            new_packet = cls.__compute_checksum(
                Packet(src_port, dst_port, seq_num, data[start:end]))
            packet_list.append(new_packet)
            leftover -= (end - start + 1)
            # update the index
            start = end + 1
            end += cls.MSS if leftover >= cls.MSS else leftover
        return packet_list

    @classmethod
    def __carry_around(cls, a, b):  # TODO: is this right?
        c = a + b
        return (c & 0xffff) + (c >> 16)

    @classmethod
    def __checksum(cls, message):  # TODO: is this right?
        s = 0
        for i in range(0, len(message), 2):
            word = ord(message[i] + ord(message[i + 1]) << 8)
            s = cls.__carry_around(s, word)
        return ~s & 0xffff

    # generate checksum for given data
    @classmethod
    def compute_checksum(cls, packet):
        checksum = cls.__checksum(packet.get_data())  # TODO: set this to the right value
        packet.set_checksum(checksum)
        return packet

    # validate data integrity
    @classmethod
    def validate_checksum(cls, packet):
        """Returns whether a packet is good based on checksum validation.
        """
        checksum = packet.get_checksum()
        packet.setCheckSum(0)
        return checksum == cls.compute_checksum(packet)

    @classmethod
    def control_packet(cls, src_port, dst_port, seq_num, ack_num, yo=False,
                       cya=False, ack=False):
        cp = Packet(src_port, dst_port, seq_num, None)
        if yo:
            cp.set_yo()
        if cya:
            cp.set_cya()
        if ack:
            cp.set_ack(ack_num)
        return cls.compute_checksum(cp)
