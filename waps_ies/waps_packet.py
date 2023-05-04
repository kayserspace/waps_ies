"""
Script: packet.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: WAPS PD image extraction software for operations at MUSC
         WAPS packet class
Version: 2023-04-18 14:00, version 0.2

Change Log:
2023-04-18 version 0.1
 - initial version
"""

from struct import unpack
import uuid
import logging


class WapsPacket:
    """
    WAPS Image Packet class

    Attributes
    ----------
    source_file : str
        Source file path where the packet was extracted from
    extraction_time : str
        Time of packet extraction
    data : list
        Packet data stored as list of numbers.
        Each number represents one byte

    Methods
    -------
    info(additional=""):
        Prints the person's name and age.
    """

    # WAPS image data packet values
    image_number_of_packets = -1
    data_packet_id = -1
    data_packet_size = -1
    data_packet_crc = -1
    data_packet_verify_code = -1

    # Unique ID
    image_uuid = -1

    # If the packet is corrupted - declare it only once per packet load
    packet_corruption_declared = False

    def __init__(self, ccsds_time, acquisition_time, data, receiver=None):
        """Packet initialization with metadata"""

        self.uuid = str(uuid.uuid4())  # Random UUID
        self.receiver = receiver

        self.acquisition_time = acquisition_time
        self.ccsds_time = ccsds_time
        self.data = data

        self.packet_name = 'pkt_' + self.ccsds_time.strftime('%Y%m%d_%H%M%S')

        if len(self.data) < 254:
            logging.error(' Unexpectedly short packet data: %i',
                          len(self.data))
            return

        # And then sort them out from data
        # EC address
        self.ec_address = self.data[2]
        # Packet time tag
        self.time_tag = unpack('>i', self.data[4:8])[0]

        # Last taken image memory slot
        val = unpack('>H', self.data[56:58])[0] >> 12
        self.biolab_current_image_memory_slot = val

        # Generic TM ID 0x4100, Generic TM Type set
        # with corresponding Picture ID, 0 to 7, and Packet ID to 0x000
        self.generic_tm_id = unpack('>H', self.data[84:86])[0]
        # Generic TM Type
        self.generic_tm_type = unpack('>H', self.data[86:88])[0]
        # Generic TM data length
        self.generic_tm_length = unpack('>H', self.data[88:90])[0]

        # WAPS Image Memory slot
        self.image_memory_slot = self.generic_tm_type >> 12
        # WAPS Image Packet ID
        self.tm_packet_id = self.generic_tm_type & 0x3FF

        self.packet_name = ('pkt_ec_' + str(self.ec_address) +
                            '_m' + str(self.image_memory_slot) +
                            '_' + self.ccsds_time.strftime('%Y%m%d_%H%M%S') +
                            '_' + str(self.time_tag))

        if self.generic_tm_id in (0x4100, 0x4200, 0x5100, 0x5200):

            self.is_waps_image_packet = True

            if self.generic_tm_id in (0x4100, 0x5100):
                # WAPS Image number of packets (FLIR or uCAM)
                self.image_number_of_packets = unpack('>H',
                                                      self.data[90:92])[0]

            elif self.generic_tm_id == 0x4200:
                # WAPS FLIR Data packet ID
                # 4 upper bits are reserved
                self.data_packet_id = unpack('>H',
                                             self.data[90:92])[0] & 0x0FFF
                # WAPS FLIR Data packet CRC
                self.data_packet_crc = unpack('>H', self.data[92:94])[0]

            elif self.generic_tm_id == 0x5200:
                # WAPS uCAM Data packet ID
                self.data_packet_id = unpack('>H', self.data[90:92])[0]
                # WAPS uCAM Data packet size
                self.data_packet_size = unpack('>H', self.data[92:94])[0]
                # WAPS uCAM Data packet verification code

                val = self.data[94 + self.data_packet_size:94 +
                                self.data_packet_size + 2]
                self.data_packet_verify_code = unpack('>H', val)[0]
        else:
            self.is_waps_image_packet = False

    def __str__(self):
        """Packet metadata"""

        out = ("\nBIOLAB TM Packet " + self.packet_name + " metadata:" +
               "\n - Acquisition Time: " + str(self.acquisition_time) +
               "\n - CCSDS Time: " + str(self.ccsds_time) +
               "\n - Packet Time Tag: " + str(self.time_tag) +
               "\n - EC address: " + str(self.ec_address) +
               "\n - Generic TM ID: " + hex(self.generic_tm_id) +
               "\n - Generic TM Type: " + hex(self.generic_tm_type) +
               "\n - Generic TM Length: " + str(self.generic_tm_length))

        if self.generic_tm_id == 0x4100:
            out = out + ("\n -- FLIR Image Init Packet" +
                         "\n -- Image Memory Slot: " +
                         str(self.image_memory_slot) +
                         "\n -- Image TM Packet ID: " +
                         str(self.tm_packet_id) +
                         "\n -- Image Number of Packets: " +
                         str(self.image_number_of_packets))

        elif self.generic_tm_id == 0x4200:
            out = out + ("\n -- FLIR Image Data Packet" +
                         "\n -- Image Memory Slot: " +
                         str(self.image_memory_slot) +
                         "\n -- Image TM Packet ID: " +
                         str(self.tm_packet_id) +
                         "\n -- Image Data Packet ID: " +
                         str(self.data_packet_id) +
                         "\n -- Image Data Packet CRC: " +
                         str(self.data_packet_crc))

        elif self.generic_tm_id == 0x5100:
            out = out + ("\n -- uCAM Image Init Packet" +
                         "\n -- Image Memory Slot: " +
                         str(self.image_memory_slot) +
                         "\n -- Image TM Packet ID: " +
                         str(self.tm_packet_id) +
                         "\n -- Image Number of Packets: " +
                         str(self.image_number_of_packets))

        elif self.generic_tm_id == 0x5200:
            out = out + ("\n -- uCAM Image Data Packet" +
                         "\n -- Image Memory Slot: " +
                         str(self.image_memory_slot) +
                         "\n -- Image TM Packet ID: " +
                         str(self.tm_packet_id) +
                         "\n -- Image Data Packet ID: " +
                         str(self.data_packet_id) +
                         "\n -- Image Data Packet Size: " +
                         str(self.data_packet_size) +
                         "\n -- Image Verify Code: " +
                         str(self.data_packet_verify_code))
        return out

    def in_spec(self):
        """ Check that essential packet parameters are correct """

        if self.data[0] != 0x40:  # BIOLAB packet ID (0x40) confirmation
            logging.log(1, '%s - BIOLAB ID not found', self.packet_name)
            return False

        if len(self.data) != self.data[1]*2+4:
            # BIOLAB packet data length fixed at 254
            logging.info('%s - Actual data length and corresponding value in the packet do not match. %i vs %i',
                         self.packet_name, len(self.data), self.data[1]*2+4)
            return False

        return True

    def is_good_waps_image_packet(self, count_corruption=False):
        """ Check packet for corruption"""

        if len(self.data) != 254:  # BIOLAB packet data length fixed at 254
            logging.error('%s - Incorrect data length (254). This packet: %i',
                          self.packet_name, len(self.data))
            return False

        if not self.is_waps_image_packet:
            logging.error('%s - Generic TM ID does not match a WAPS Image Packet',
                          self.packet_name)
            return False

        if self.image_memory_slot < 0 or self.image_memory_slot > 7:
            logging.error('%s - Memory slot out of bounds (0 to 7). This packet: %i',
                          self.packet_name, self.image_memory_slot)
            return False

        if self.tm_packet_id < 0:  # Packet number has to be defined
            logging.error('%s - Data packet number not defined',
                          self.packet_name)
            return False

        if self.generic_tm_id == 0x4200:

            if self.data_packet_id != self.tm_packet_id:
                logging.debug('%s - packet id inconsistent: %i vs %i',
                              self.packet_name,
                              self.tm_packet_id,
                              self.data_packet_id)

            # Calculate CRC for FLIR data packets.
            crc_data = bytearray(self.data[90:])
            crc_data[0] = crc_data[0] & 0x0F  # 4 upper bits reserved
            crc_data[2] = 0  # CRC itself is zero for CRC calculation
            crc_data[3] = 0  # CRC itself is zero for CRC calculation

            def crc16_ccitt(crc, data):
                """
                CRC calculation function (16-bit XMODEM CRC-CCITT
                with initial value of zero, over the entire message)
                Width = 16 bits
                Truncated polynomial = 0x1021
                Initial value = 0x0000
                """
                msb = crc >> 8
                lsb = crc & 255
                for c in data:
                    x = int(c) ^ msb
                    x ^= (x >> 4)
                    msb = (lsb ^ (x >> 3) ^ (x << 4)) & 255
                    lsb = (x ^ (x << 5)) & 255
                return (msb << 8) + lsb

            if crc16_ccitt(0, crc_data) != self.data_packet_crc:
                if not self.packet_corruption_declared:
                    logging.warning('%s - CRC mismatch. %i packet is likely corrupted',
                                    self.packet_name, self.tm_packet_id)
                    self.packet_corruption_declared = True

                if self.receiver is not None and count_corruption:
                    self.receiver.total_corrupted_packets = self.receiver.total_corrupted_packets + 1

                return False

        if self.generic_tm_id == 0x5200:

            if self.data_packet_id != self.tm_packet_id + 1:
                logging.warning('%s - packet id inconsistent: %i vs %i',
                                self.packet_name,
                                self.tm_packet_id,
                                self.data_packet_id)

            # Calculate Verify Code for uCAM data packets.
            # (biolab + id and length + data length + verify code + 1)
            verify_data = self.data[90:90+4+self.data_packet_size+2]

            calc_verif_code = 0
            for byte in verify_data[:-2]:
                calc_verif_code = calc_verif_code + byte
            # Only the lower byte is taken
            calc_verif_code = (calc_verif_code & 0x00FF) << 8

            if calc_verif_code != self.data_packet_verify_code:
                if not self.packet_corruption_declared:
                    logging.warning('%s - Verify code mismatch. %i packet is likely corrupted',
                                    self.packet_name, self.tm_packet_id)
                    self.packet_corruption_declared = True

                if self.receiver is not None:
                    if count_corruption:
                        self.receiver.total_corrupted_packets = self.receiver.total_corrupted_packets + 1

                    if not self.receiver.skip_crc:
                        return False

        return True
