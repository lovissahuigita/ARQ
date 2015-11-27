import re

from FxA.util import Util
import io
import pickle
from RxP.Packet import Packet

__author__ = 'Lovissa Winyoto'


class Packeter:
    __logger = Util.setup_logger()
    MSS = 1024  # in bytes

    @classmethod
    def packetize(cls, src_port, dst_port, seq_num, data):
        """ Breaks down data into packets. The input data is already in binary.
        This method breaks the binary to 544 bytesdef.
        :param src_port: the source port of the new packet
        :param dst_port: the destination port of the new packet
        :param seq_num: the sequence number of the new packet
        :param data: the data needs to be packetized
        :return: the packets that contain the data
        """
        packet_list = []
        if data:
            leftover = len(data)
            start = 0
            end = (cls.MSS if len(data) >= cls.MSS else len(data)) - 1
            while leftover > 0:
                new_packet = cls.compute_checksum(
                    Packet(src_port, dst_port, seq_num, data[start:end+1]))
                packet_list.append(new_packet)
                seq_num += end
                leftover -= (end - start + 1)
                # update the index
                start = end + 1
                end += cls.MSS if leftover >= cls.MSS else leftover
                cls.__logger.info("Packetize: seq_num: %d" % seq_num)
        else:
            new_packet = cls.compute_checksum(
                Packet(src_port, dst_port, seq_num))
            packet_list.append(new_packet)
        return packet_list

    @classmethod
    def __carry_around(cls, a, b):
        """
        Make sure that the carry in from a check sum is being added properly
        :param a: the sum
        :param b: the carry in to carry around
        :return: the sum of the current sum and the carry in
        """
        c = a + b
        return (c & 0xffff) + (c >> 16)

    @classmethod
    def __checksum(cls, packet):
        """
        Calculate a packet's checksum.
        The method calculates the checksum by binarizing the packet.
        The binarized packet checksum is zeroed before checksummed.
        The method calls the __carry_around method to recount the overflow
        to the checksum
        :param packet: the packet to be checksummed
        :return: the checksum of the packet
        """
        orig = packet.get_checksum()
        packet.set_checksum(0)
        bytes = cls.binarize(packet)
        s = 0
        ptr = 0
        while ptr < len(bytes):
            double_byte = bytes[ptr] | (bytes[ptr + 1] << 8) if ptr + 1 < len(
                bytes) else 0
            ptr += 2
            s = cls.__carry_around(s, double_byte)
        packet.set_checksum(orig)
        return s

    @classmethod
    def __negated_checksum(cls, packet):
        """
        Calculate the checksum of a packet and negate it.
        This method calls the cls.__checksum method that calculates the
        checksum of the packet and negates the return
        value.
        :param packet: the packet that needs the negated checksum
        :return: the negated checksum of the packet
        """
        return ~(cls.__checksum(packet)) & 0xffff

    @classmethod
    def compute_checksum(cls, packet):
        """
        Calculates the checksum for the packets that are going to be sent.
        The checksum is negated for sending purposes.
        :param packet: the packet to be checksummed
        :return: the packet with the checksum filled with the checksum
        """

        checksum = cls.__checksum(packet)
        packet.set_checksum(checksum)
        cls.__logger.info("SET packet checksum: %d" % checksum)
        return packet

    @classmethod
    def validate_checksum(cls, packet):
        """ Returns whether a packet is good based on checksum validation.
        The method returns true if the checksum matches (packet is validated)
        The method returns false if the checksum does not match
        :param packet: the packet to be validated
        :return: True if the packet is a good packet, False otherwise
        """
        checksum = packet.get_checksum()
        actual_checksum = cls.__checksum(packet)
        cls.__logger.info(
            "checksum %d current checksum %d" % (checksum, actual_checksum))
        cls.__logger.info("VALIDATE checksum: %s" % str((actual_checksum +
                                                         checksum) & 0xffff
                                                        == 0xffff))
        ret = cls.__carry_around(actual_checksum, checksum) & 0xffff == 0xffff
        assert checksum == packet.get_checksum()
        return checksum == actual_checksum

    @classmethod
    def control_packet(cls, src_port, dst_port, seq_num, ack_num=0, yo=False,
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
            cls.__logger.info("CREATED YO packet")
        if cya:
            cp.set_cya()
            cls.__logger.info("CREATED CYA packet")
        if ack:
            cp.set_ack(ack_num)
            cls.__logger.info("CREATED ACK packet")
        return cls.compute_checksum(cp)

    @classmethod
    def binarize(cls, segment):
        """
        Convert anything to binary
        :param segment: anything
        :return: binarized anything
        """
        return segment._stringify().encode('utf-8') #buff.getvalue()

    @classmethod
    def objectize(cls, binary):
        """
        Converts binary to anything
        :param binary: the binary
        :return: anything
        """
        # loggers = cls.__logger
        # loggers.info("OBJECTIZE: %d %s" % (len(binary), binary))
        # ret = pickle.loads(binary)
        # loggers.debug(ret)
        return cls._objectify(binary) #ret

    @classmethod
    def __print_bin(cls, bin):

        cls.__logger.debug(str(len(bin)))
        a = []
        for byte in bin:
            a.append("0x{:02x}".format(byte))
        return ''#a

    @classmethod
    def _objectify(cls, packet):
        cls.__logger.info("OBJECTIFY")
        res = re.match('<src>(.+?)</src><dst>(.+?)</dst><seq>('
                       '.+?)</seq><ack>(.+?)</ack><wind>(.+?)</wind><chk>('
                       '.+?)</chk><cyo>(.+?)</cyo><ccya>(.+?)</ccya><cack>('
                       '.+?)</cack><data>(.+?)</data>', packet.decode('utf-8'))
        if not res:
            cls.__logger.info("corrupted object")
            return Packet()
        cls.__logger.debug(res.group(0))
        datalist = res.group(10)
        i = int(0)
        done = False
        data = []
        while not done:
            datares = re.search('<' + str(i) + '>(.+?)</' + str(i) + '>',
                             datalist)
            if datares:
                data.append(int(datares.group(1)))
            else:
                done = True
            i += 1

        pack = Packet()
        pack._copy(
            src=int(res.group(1)),
            dst=int(res.group(2)),
            seq=int(res.group(3)),
            ack=int(res.group(4)),
            wind=int(res.group(5)),
            chk=int(res.group(6)),
            cyo=True if res.group(7) == 'True' else False,
            ccya=True if res.group(8) == 'True' else False,
            cack=True if res.group(9) == 'True' else False,
            data=data
        )
        cls.__logger.info("OBJ done")
        return pack
