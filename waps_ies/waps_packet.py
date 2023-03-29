""" WAPS IES Image Packet processor """

from struct import unpack
import uuid
import logging
from datetime import datetime, timedelta

class BIOLAB_Packet:
    """
    WAPS Image Packet class

    Attributes
    ----------
    source_file : str
        Source file path where the packet was extracted from
    extraction_time : str
        Time of packet extraction
    data : list
        Packet data stored as list of numbers. Each number represents one byte

    Methods
    -------
    info(additional=""):
        Prints the person's name and age.
    """

    image_number_of_packets = -1
    data_packet_id = -1
    data_packet_size = -1
    data_packet_crc = -1
    data_packet_verify_code = -1

    image_uuid = -1
    
    def __init__(self, CCSDS_time, acquisition_time, data, receiver=None):
        """Packet initialization with metadata"""

        self.uuid = str(uuid.uuid4()) # Random UUID
        self.receiver = receiver
        
        self.acquisition_time = acquisition_time
        self.CCSDS_time = CCSDS_time
        self.data = data

        # Initialize other parameters

        # If the packet is corrupted - declare it only once
        self.packet_corruption_declared = False

        # Other relevant TM data
        self.biolab_current_image_memory_slot = -1

        # And then sort them out from data
        try:
            # EC address
            self.ec_address = self.data[2]
            # Packet time tag
            self.time_tag = unpack( '>i', self.data[4:8] )[0]
            
            # Generic TM ID 0x4100, Generic TM Type set with corresponding Picture ID, 0 to 7, and Packet ID to 0x000
            self.generic_tm_id = unpack( '>H', self.data[84:86] )[0]
            # Generic TM Type
            self.generic_tm_type = unpack( '>H', self.data[86:88] )[0]
            # Generic TM data length
            self.generic_tm_length = unpack( '>H', self.data[88:90] )[0]

            # WAPS Image Memory slot
            self.image_memory_slot = self.generic_tm_type >> 12
            # WAPS Image Packet ID
            self.tm_packet_id = self.generic_tm_type & 0x3FF

            self.packet_name = ('pkt_ec_' + str(self.ec_address) + '_m' + str(self.image_memory_slot) +
                        '_' + self.acquisition_time.strftime('%Y%m%d_%H%M%S') + '_' + str(self.time_tag));

            if (self.generic_tm_id == 0x4100 or
                self.generic_tm_id == 0x4200 or
                self.generic_tm_id == 0x5100 or
                self.generic_tm_id == 0x5200 ):
                self.is_waps_image_packet = True
            else:
                self.is_waps_image_packet = False

            if (self.is_waps_image_packet):
                
                if (self.generic_tm_id == 0x4100 or self.generic_tm_id == 0x5100):
                    # WAPS Image number of packets (FLIR or uCAM)
                    self.image_number_of_packets = unpack( '>H', self.data[90:92] )[0]
                
                elif (self.generic_tm_id == 0x4200):
                    # WAPS FLIR Data packet ID
                    self.data_packet_id = unpack( '>H', self.data[90:92] )[0] & 0x0FFF # 4 upper bits are reserved
                    # WAPS FLIR Data packet CRC
                    self.data_packet_crc = unpack( '>H', self.data[92:94] )[0]
                
                elif (self.generic_tm_id == 0x5200):
                    # WAPS uCAM Data packet ID
                    self.data_packet_id = unpack( '>H', self.data[90:92] )[0]
                    # WAPS uCAM Data packet size
                    self.data_packet_size = unpack( '>H', self.data[92:94] )[0]
                    # WAPS uCAM Data packet verification code
                    self.data_packet_verify_code = unpack( '>H', self.data[94 + self.data_packet_size:
                                                                            94 + self.data_packet_size + 2] )[0]

            # Other telemetry data
            # Last taken image memory slot
            self.biolab_current_image_memory_slot = unpack( '>H', self.data[56:58] )[0] >> 12

        except IndexError:
            logging.warning(str(self.packet_name) + ' - Unexpected end of packet data')

    def __str__(self):
        """Packet metadata"""
        
        out =  ("\nBIOLAB TM Packet " + self.packet_name + " metadata:"
                "\n - Acquisition Time: " + self.acquisition_time.strftime('%Y%m%d_%H%M') +
                "\n - CCSDS Time: " + self.CCSDS_time.strftime('%Y%m%d_%H%M') +
                "\n - Packet Time Tag: " + str(self.time_tag) +
                "\n - EC address: " + str(self.ec_address) +
                "\n - Generic TM ID: " + hex(self.generic_tm_id) +
                "\n - Generic TM Type: " + hex(self.generic_tm_type) +
                "\n - Generic TM Length: " + str(self.generic_tm_length)
                )
        if (self.generic_tm_id == 0x4100):
            out = out + (
                "\n -- FLIR Image Init Packet" +
                "\n -- Image Memory Slot: " + str(self.image_memory_slot) +
                "\n -- Image TM Packet ID: " + str(self.tm_packet_id) +
                "\n -- Image Number of Packets: " + str(self.image_number_of_packets)
                )
        elif (self.generic_tm_id == 0x4200):
            out = out + (
                "\n -- FLIR Image Data Packet" +
                "\n -- Image Memory Slot: " + str(self.image_memory_slot) +
                "\n -- Image TM Packet ID: " + str(self.tm_packet_id) +
                "\n -- Image Data Packet ID: " + str(self.data_packet_id) +
                "\n -- Image Data Packet CRC: " + str(self.data_packet_crc)
                )
        elif (self.generic_tm_id == 0x5100):
            out = out + (
                "\n -- uCAM Image Init Packet" +
                "\n -- Image Memory Slot: " + str(self.image_memory_slot) +
                "\n -- Image TM Packet ID: " + str(self.tm_packet_id) +
                "\n -- Image Number of Packets: " + str(self.image_number_of_packets)
                )
        elif (self.generic_tm_id == 0x5200):
            out = out + (
                "\n -- uCAM Image Data Packet" +
                "\n -- Image Memory Slot: " + str(self.image_memory_slot) +
                "\n -- Image TM Packet ID: " + str(self.tm_packet_id) +
                "\n -- Image Data Packet ID: " + str(self.data_packet_id) +
                "\n -- Image Data Packet Size: " + str(self.data_packet_size) +
                "\n -- Image Verify Code: " + str(self.data_packet_verify_code)
                )
        return out

    def in_spec(self):
        """Check that the packet parameters are correct"""

        # Parameters for packet sorting and sanity check first
        
        if (self.data[0] != 0x40): # BIOLAB packet ID (0x40) confirmation
            logging.log(1, str(self.packet_name) + ' - BIOLAB ID not found')
            return False

        if (len(self.data) != self.data[1]*2+4): # BIOLAB packet data length fixed at 254
            logging.info(str(self.packet_name) + ' - Actual data length and corresponding value in the packet do not match. '
                        + str(len(self.data)) + ' vs ' + self.data[1]*2+4)
            return False
            
        return True

    def is_good_waps_image_packet(self):

        if (len(self.data) != 254): # BIOLAB packet data length fixed at 254
            logging.error(str(self.packet_name) + ' - Incorrect data length (254). This packet:' + str(len(self.data)))
            return False

        if (not (self.is_waps_image_packet)):
            logging.error(str(self.packet_name) + ' - Generic TM ID does not match a WAPS Image Packet')
            return False

        if (self.image_memory_slot < 0 and self.image_memory_slot > 7): # Memory slot between 0 and 7
            logging.error(str(self.packet_name) + ' - Memory slot out of bounds (0 to 7). This packet: ' + str(self.image_memory_slot))
            return False

        if (self.tm_packet_id < 0): # Packet number has to be defined
            logging.error(str(self.packet_name) + ' - Data packet number not defined')
            return False

        if (self.data_packet_id != self.tm_packet_id and self.data_packet_id != self.tm_packet_id + 1):
            # Currently packet id in image data packets are inconsistent
            logging.debug(str(self.packet_name) + ' - packet id inconsistent: ' + str(self.tm_packet_id) + ' vs ' + str(self.data_packet_id))

        if (self.generic_tm_id == 0x4200):
            # Calculate CRC for FLIR data packets.
            crc_data = bytearray(self.data[90:])
            crc_data[0] = crc_data[0] & 0x0F # 4 upper bits of the packet ID are reserved
            crc_data[2] = 0 # CRC itself is zero for CRC calculation
            crc_data[3] = 0 # CRC itself is zero for CRC calculation

            # CRC calculation function (16-bit XMODEM CRC- CCITT with initial value of zero, over the entire message)
            def crc16_ccitt(crc, data):
                # Width = 16 bits
                # Truncated polynomial = 0x1021
                # Initial value = 0x0000
                msb = crc >> 8
                lsb = crc & 255
                for c in data:
                    x = int(c) ^ msb
                    x ^= (x >> 4)
                    msb = (lsb ^ (x >> 3) ^ (x << 4)) & 255
                    lsb = (x ^ (x << 5)) & 255
                return (msb << 8) + lsb

            if (crc16_ccitt(0, crc_data) != self.data_packet_crc):
                if (not self.packet_corruption_declared):
                    logging.warning(str(self.packet_name) + ' - CRC mismatch. ' + str(self.tm_packet_id) + ' packet is likely corrupted')
                    self.receiver.total_corrupted_packets = self.receiver.total_corrupted_packets + 1
                    self.packet_corruption_declared = True
                return False

        if (self.generic_tm_id == 0x5200):
            # Calculate Verify Code for uCAM data packets.
            verify_data = self.data[90:90+4+self.data_packet_size+2] # biolab + id and length + data length + verify code + 1
            #print(len(self.data), self.data_packet_size, len(verify_data), 90+4+self.data_packet_size+2+1)
            calc_verif_code = 0
            for byte in verify_data[:-2]:
                calc_verif_code = calc_verif_code + byte
            calc_verif_code = (calc_verif_code & 0x00FF) << 8 # Only the lower byte is taken
            # TODO confirm that this is LSB
            
            if (calc_verif_code !=self.data_packet_verify_code):
                if (not self.packet_corruption_declared):
                    logging.warning(str(self.packet_name) + ' - Verify code mismatch. ' + str(self.tm_packet_id) + ' packet is likely corrupted')
                    self.receiver.total_corrupted_packets = self.receiver.total_corrupted_packets + 1
                    self.packet_corruption_declared = True
                return False

        return True