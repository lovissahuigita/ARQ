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
        """
        Make a new packet
        :param src_port: the source port of the new packet
        :param dst_port: the destination port of the new packet
        :param seq_num: the sequence number of the new packet
        :param data: the data of the new packet
        :return: the packets that contain the data
        """
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
        """
        Make sure that the carry in from a check sum is being added properly
        :param a: the sum
        :param b: the carry in to carry around
        :return: the sum of the current sum and the carry in
        """
        c = a + b
        return (c & 0xffff) + (c >> 16)

    @classmethod
    def __checksum(cls, packet):  # TODO: is this right?
        """
        Calculate a packet's checksum.
        The method calculates the checksum by binarizing the packet.
        The binarized packet checksum is zeroed before checksummed.
        The method calls the __carry_around method to recount the overflow to the checksum
        :param packet: the packet to be checksummed
        :return: the checksum of the packet
        """
        bytes = cls.__binarize(packet)
        s = 0
        ptr = 0
        while ptr < len(bytes):
            double_byte = bytes[ptr] | (bytes[ptr + 1] << 8) if ptr + 1 < len(bytes) else 0
            ptr += 2
            s = cls.__carry_around(s, double_byte)
        return s

    @classmethod
    def __negated_checksum(cls, packet):
        """
        Calculate the checksum of a packet and negate it.
        This method calls the cls.__checksum method that calculates the checksum of the packet and negates the return
        value.
        :param packet: the packet that needs the negated checksum
        :return: the negated checksum of the packet
        """
        return ~(cls.__checksum(packet)) & 0xffff

    # generate checksum for given data
    @classmethod
    def compute_checksum(cls, packet):
        """
        Calculates the checksum for the packets that are going to be sent.
        The checksum is negated for sending purposes.
        :param packet: the packet to be checksummed
        :return: the packet with the checksum filled with the checksum
        """
        packet.set_checksum(0)
        checksum = cls.__negated_checksum(packet)  # TODO: set this to the right value
        packet.set_checksum(checksum)
        return packet

    # validate data integrity
    @classmethod
    def validate_checksum(cls, packet):
        """
        Returns whether a packet is good based on checksum validation.
        The method returns true if the checksum matches (packet is validated)
        The method returns false if the checksum does not match
        :param packet: the packet to be validated
        :return: True if the packet is a good packet, False otherwise
        """
        checksum = packet.get_checksum()
        packet.set_checksum(0)
        current_checksum = cls.__checksum(packet)
        return (current_checksum + checksum) & 0xffff == 0

    @classmethod
    def control_packet(cls, src_port, dst_port, seq_num, ack_num, yo=False,
                       cya=False, ack=False):
        """
        Make a control packet
        :param src_port: the source port of the new packet
        :param dst_port: the destination port of the new packet
        :param seq_num: the sequence number of the new packet
        :param ack_num: the acknowledgement number of the new packet
        :param yo: True if YO packet, False otherwise
        :param cya: True if CYA packet, False otherwise
        :param ack: True if ACK packet, False otherwise
        :return: return the ready to send packet (checksummed)
        """
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
        """
        Convert anything to binary
        :param segment: anything
        :return: binarized anything
        """
        buff = io.BytesIO()
        pickle.dump(segment, buff)
        return buff.getvalue()

    @staticmethod
    def __objectize(binary):
        """
        Converts binary to anything
        :param binary: the binary
        :return: anything
        """
        return pickle.loads(binary)


