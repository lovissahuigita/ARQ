import io
import pickle

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
        """Make sure that the carry in from a check sum is being added properly"""
        c = a + b
        return (c & 0xffff) + (c >> 16)

    @classmethod
    def __checksum(cls, packet):  # TODO: is this right?
        """Calculate a data's checksum by binarizing the packet and make sure
        that the carry in are added to the result"""
        bytes = cls.__binarize(packet)
        s = 0
        ptr = 0
        while ptr < len(bytes):
            double_byte = bytes[ptr] | (bytes[ptr + 1] << 8) if ptr + 1 < len(bytes) else 0
            ptr += 2
            s = cls.__carry_around(s, double_byte)
        return s

    @classmethod
    def __negated_checksum(cls, message):
        """Negated the checksum result. The method is used when calculating a checksum
        for a packet that will be sent"""
        return ~(cls.__checksum(message)) & 0xffff

    # generate checksum for given data
    @classmethod
    def compute_checksum(cls, packet):
        """Method to calculate checksum for packets that will be sent.
        The checksum is negated"""
        checksum = cls.__negated_checksum(packet.get_data())  # TODO: set this to the right value
        packet.set_checksum(checksum)
        return packet

    # validate data integrity
    @classmethod
    def validate_checksum(cls, packet):
        """Returns whether a packet is good based on checksum validation.
        The method returns true if the checksum matches (packet is validated)
        The method returns false if the checksum does not match
        """
        checksum = packet.get_checksum()
        current_checksum = cls.__checksum(packet.get_data())
        return (current_checksum + checksum) & 0xffff == 0

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

    @staticmethod
    def __binarize(segment):
        buff = io.BytesIO()
        pickle.dump(segment, buff)
        return buff.getvalue()

    @staticmethod
    def __objectize(binary):
        return pickle.loads(binary)


