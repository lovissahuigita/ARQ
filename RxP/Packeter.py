from RxP.Packet import Packet

__author__ = 'Lovissa Winyoto'


class Packeter:
    MSS = 544  # in bytes

    # breakdown data into packets
    #  input data is already in binary 
    # this method breaks the binary to 544 bytes def
    @classmethod
    def packetize(cls, src_port, dst_port, seq_num, ack_num, data):
        packet_list = []
        leftover = len(data)
        start = 0
        end = (cls.MSS if len(data) >= cls.MSS else len(data)) - 1
        while leftover > 0:
            seq_num += end
            new_packet = cls.__compute_checksum(
                Packet(src_port, dst_port, seq_num, ack_num, data[start:end]))
            packet_list.append(new_packet)
            leftover -= (end - start + 1)
            # update the index
            start = end + 1
            end += cls.MSS if leftover >= cls.MSS else leftover
        return packet_list

    # generate checksum for given data
    @classmethod
    def __compute_checksum(cls, packet):
        checksum = 0  # TODO: set this to the right value
        packet.set_checksum(checksum)
        return packet

    # validate data integrity
    @classmethod
    def validate_checksum(cls, packet):
        checksum = packet.get_checksum()
        packet.setCheckSum(0)
        return checksum == cls.__compute_checksum(packet)

    def control_packet(self, src_port, dst_port, seq_num, ack_num, yo=False,
                       cya=False, ack=False):
        cp = Packet(src_port, dst_port, seq_num, ack_num, None)
        if yo:
            cp.set_yo()
        if cya:
            cp.set_cya()
        if ack:
            cp.set_ack()
        return self.__compute_checksum(cp)
