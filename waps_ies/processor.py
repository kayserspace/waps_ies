""" WAPS IES Image Packet processor """

import logging
from datetime import datetime, timedelta

import os
import numpy as np
from PIL import Image
import io

# Global variables
current_biolab_memory_slot = None
image_transmission_in_progress = False

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
    
    def __init__(self, source_file, timestamp, extraction_time, data):
        """Packet initialization with metadata"""
        
        self.source_file = source_file
        self.source_file_timestamp = timestamp
        self.extraction_time = extraction_time
        self.data = data

        # Initialize other parameters
        # Generic
        self.ec_address = -1
        self.time_tag = -1
        self.packet_name = -1
        self.generic_tm_id = -1
        self.generic_tm_type = -1
        self.generic_tm_length = -1
        
        # Image packets
        self.image_memory_slot = -1
        self.tm_packet_id = -1
        
        # FLIR or μCAM Init packet
        self.image_number_of_packets = -1
        self.data_packet_id = -1
        
        # FLIR Data packet
        self.data_packet_crc = -1
        
        # uCAM Data packet
        self.data_packet_size = -1
        self.data_packet_verify_code = -1

        # If the packet is corrupted - declare it only once
        self.packet_corruption_declared = False

        # Other relevant TM data
        self.biolab_current_image_memory_slot = -1

        # And then sort them out from data
        try:
            # EC address
            self.ec_address = self.data[2]
            # Packet time tag
            self.time_tag = BIOLAB_Packet.word(self.data[4:6])*65536 + BIOLAB_Packet.word(self.data[6:8])
            # Packet ID
            file_name_start = self.source_file.rfind('\\') + 1
            if (file_name_start == -1):
                file_name_start = self.source_file.rfind('/')
            if (file_name_start == -1):
                file_name_start = 0
            self.packet_name = 'pkt_' + (self.source_file[file_name_start:] +
                        '_' + self.source_file_timestamp.strftime('%Y%m%d_%H%M')) + '_' + str(self.time_tag);
            # Generic TM ID 0x4100, Generic TM Type set with corresponding Picture ID, 0 to 7, and Packet ID to 0x000
            self.generic_tm_id = BIOLAB_Packet.word(self.data[84:86])
            # Generic TM Type
            self.generic_tm_type = BIOLAB_Packet.word(self.data[86:88])
            # Generic TM data length
            self.generic_tm_length = BIOLAB_Packet.word(self.data[88:90])

            if (self.generic_tm_id == 0x4100 or
                self.generic_tm_id == 0x4200 or
                self.generic_tm_id == 0x5100 or
                self.generic_tm_id == 0x5200 ):
                # WAPS Image Memory slot
                self.image_memory_slot = self.generic_tm_type >> 12
                # WAPS Image Packet ID
                self.tm_packet_id = self.generic_tm_type & 0x3FF
                
                if (self.generic_tm_id == 0x4100 or self.generic_tm_id == 0x5100):
                    # WAPS Image number of packets (FLIR or μCAM)
                    self.image_number_of_packets = BIOLAB_Packet.word(self.data[90:92])
                
                elif (self.generic_tm_id == 0x4200):
                    # WAPS FLIR Data packet ID
                    self.data_packet_id = BIOLAB_Packet.word(self.data[90:92]) & 0x0FFF # 4 upper bits are reserved
                    # WAPS FLIR Data packet CRC
                    self.data_packet_crc = BIOLAB_Packet.word(self.data[92:94])
                
                elif (self.generic_tm_id == 0x5200):
                    # WAPS μCAM Data packet ID
                    self.data_packet_id = BIOLAB_Packet.word(self.data[90:92])
                    # WAPS μCAM Data packet size
                    self.data_packet_size = BIOLAB_Packet.word(self.data[92:94])
                    # WAPS μCAM Data packet verification code
                    self.data_packet_verify_code = BIOLAB_Packet.word(self.data[94 +
                                                                                self.data_packet_size:94 +
                                                                                self.data_packet_size
                                                                                + 2])

            # Other telemetry data
            # Last taken image memory slot
            self.biolab_current_image_memory_slot = BIOLAB_Packet.word(self.data[56:58]) >> 12

        except IndexError:
            logging.warning(str(self.packet_name) + ' - Unexpected end of packet data')

    def __str__(self):
        """Packet metadata"""
        
        out =  ("BIOLAB Packet " + self.packet_name + " metadata:"
                "\n - Source file: " + self.source_file +
                "\n - Source file Timestamp: " + self.source_file_timestamp.strftime('%Y%m%d_%H%M') +
                "\n - Extraction Timestamp: " + self.extraction_time.strftime('%Y%m%d_%H%M') +
                "\n - Packet Time Tag: " + str(self.time_tag) +
                "\n - Generic TM ID: " + hex(self.generic_tm_id) +
                "\n - Generic TM Type: " + hex(self.generic_tm_type) +
                "\n - Generic TM Length: " + str(self.generic_tm_length)
                )
        if (self.generic_tm_id == 0x4100):
            out = out + (
                "\n - FLIR Image Init Packet" +
                "\n --- Image Memory Slot: " + str(self.image_memory_slot) +
                "\n --- Image TM Packet ID: " + str(self.tm_packet_id) +
                "\n --- Image Number of Packets: " + str(self.image_number_of_packets)
                )
        elif (self.generic_tm_id == 0x4200):
            out = out + (
                "\n - FLIR Image Data Packet" +
                "\n --- Image Memory Slot: " + str(self.image_memory_slot) +
                "\n --- Image TM Packet ID: " + str(self.tm_packet_id) +
                "\n --- Image Data Packet ID: " + str(self.data_packet_id) +
                "\n --- Image Data Packet CRC: " + str(self.data_packet_crc)
                )
        elif (self.generic_tm_id == 0x5100):
            out = out + (
                "\n - μCAM Image Init Packet" +
                "\n --- Image Memory Slot: " + str(self.image_memory_slot) +
                "\n --- Image TM Packet ID: " + str(self.tm_packet_id) +
                "\n --- Image Number of Packets: " + str(self.image_number_of_packets)
                )
        elif (self.generic_tm_id == 0x5200):
            out = out + (
                "\n - μCAM Image Data Packet" +
                "\n --- Image Memory Slot: " + str(self.image_memory_slot) +
                "\n --- Image TM Packet ID: " + str(self.tm_packet_id) +
                "\n --- Image Data Packet ID: " + str(self.data_packet_id) +
                "\n --- Image Data Packet Size: " + str(self.data_packet_size) +
                "\n --- Image Verify Code: " + str(self.data_packet_verify_code)
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

        if (not (self.generic_tm_id == 0x4100 or
                 self.generic_tm_id == 0x4200 or
                 self.generic_tm_id == 0x5100 or
                 self.generic_tm_id == 0x5200)):
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
                    self.packet_corruption_declared = True
                return False

        return True

    def word(msb_byte_couple):
        
        """Convert a list of two bytes into a word"""
        return msb_byte_couple[0]*256+msb_byte_couple[1]





class WAPS_Image:
    """
    Image class

    Attributes
    ----------
    camera_type : str
        Source file path where the packet was extracted from

    Methods
    -------
    info(additional=""):
        Checks if the file image is complete.
    """
    
    def __init__(self, camera_type, packet):
        """Image initialization with metadata"""
        
        self.ec_address = packet.ec_address
        self.camera_type = camera_type
        self.memory_slot = packet.image_memory_slot
        self.number_of_packets = packet.image_number_of_packets
        self.timestamp = packet.source_file_timestamp
        self.extraction_timestamp = packet.extraction_time
        self.time_tag = packet.time_tag
        self.image_name = ("EC_" + str(self.ec_address) + '_' +
                            self.camera_type + '_' +
                            self.timestamp.strftime('%H%M%S') + '_' +
                            'm' + str(self.memory_slot) + '_' +
                            str(self.time_tag))
        
        self.packets = []

        # Other variables
        self.overwritten = False
        self.image_transmission_active = True
        self.update = True
        self.latest_saved_file = None
        self.outdated = False

    def __str__(self):
        """ Image metadata printout """
        
        self = self.sort_packets()
        missing_packets = self.get_missing_packets()
        
        out =   ("WAPS Image " + self.image_name + " metadata:"
                "\n - Camera type: " + self.camera_type +
                "\n - Image Memory Slot: " + str(self.memory_slot) +
                "\n - Timestamp of the first processed file: " + self.timestamp.strftime('%Y%m%d_%H%M') +
                "\n - Timestamp of the first processed packet: " + self.extraction_timestamp.strftime('%Y%m%d_%H%M') +
                "\n - Timetag of the first packet: " + str(self.time_tag) +
                "\n - Available Packets: " + str(len(self.packets)-len(self.get_missing_packets())) + r'/' +  str(self.number_of_packets) +
                "\n - Transmission active: " + str(self.image_transmission_active) +
                "\n - Memory Slot overwritten: " + str(self.overwritten))

        if (not self.image_transmission_active and len(missing_packets)):
            first_packet_id = 0
            previous_packet_id = -1
            out = out + '\n - Correct Packets: \t ['
            first_entry = True
            for p in self.packets:
                if (not p.tm_packet_id in missing_packets):
                    current_packet_id = p.tm_packet_id
                    if (not current_packet_id == previous_packet_id + 1):
                        if (not first_entry):
                            out = out + ', '
                        if (first_packet_id == previous_packet_id):
                            out = out + str(first_packet_id)
                        else:
                            out = out + str(first_packet_id) + '-' + str(previous_packet_id)
                        first_packet_id = current_packet_id
                        first_entry = False
                previous_packet_id = current_packet_id
            if (not first_entry):
                out = out + ', '
            if (first_packet_id == previous_packet_id):
                out = out + str(first_packet_id)
            else:
                out = out + str(first_packet_id) + '-' + str(previous_packet_id)
            out = out + ']'
            out = out + '\n - Missing or Incorrect Packets: \t' + str(missing_packets)
            
        if (self.latest_saved_file):
            out = out + '\n - Latest Saved File: \t ' + str(self.latest_saved_file)
        
        return out

    def number_sequence_printout(number_list):
        """ Number sequence printout """
        
        if (len(number_list) < 2):
            return (str(number_list))
        
        previous_number = number_list[0]
        last_number = number_list[0]
        out = '[' + str(previous_number)
        dash_added = False
        for n in number_list[1:]:
            if (n == previous_number + 1 and not dash_added):
                out = out + '-'
                dash_added = True
            elif (n != previous_number + 1):
                if (last_number != previous_number):
                    out = out + str(previous_number)
                out = out + ', ' + str(n)
                last_number = n
                dash_added = False
            previous_number = n
        if (last_number != previous_number):
            out = out + str(previous_number)
        out = out + ']'

        return out
        

    def add_packet(self, packet):
        """Append a new packet to an existing list"""

        # Check that the packet is according to specification
        if (not packet.in_spec):
            return
        self.packets.append(packet)


            
    def is_complete(self):
        """Check completeness of the image"""
        
        # Check total number of packets
        if (len(self.packets) < self.number_of_packets):
            logging.debug(str(self.image_name) + ' is incomplete. ' + str(len(self.packets)) + '/' + str(self.number_of_packets))
            return False

        # Check if all the correct packets are present
        missing_packets = self.get_missing_packets()

        # If any packet is missing
        if (len(missing_packets) != 0):
            return False
        
        return True



    def get_missing_packets(self, exclude_corrupted = False):
        """Get the missing packet list"""

        missing_packets = []
        try:
            # Check if all the correct packets are present
            completeness_array = [0] * self.number_of_packets
            for i in range(len(self.packets)):
                if (self.packets[i].is_good_waps_image_packet() or
                    exclude_corrupted):
                    completeness_array[self.packets[i].tm_packet_id] = 1
            
            for i, present in enumerate(completeness_array):
                if (not present):  
                    missing_packets.append(i)

        except IndexError:
            logging.warning(str(self.packets[i].packet_name) + ' - Unexpected tm packet id ' + str(self.packets[i].tm_packet_id) +
                                '. Number image packets: ' + str(self.number_of_packets) + '. Actual packets:' + str(len(self.packets)))
        
        return missing_packets



    def sort_packets(self):
        """Sort the packets of this image according to data packet number"""

        # Sorting based of data packet number
        def get_packet_number(packet):
            return packet.tm_packet_id
        self.packets.sort(key=get_packet_number)

        # Check for duplicates
        i = 0
        while (i < len(self.packets) - 1):
            if (self.packets[i].tm_packet_id == self.packets[i+1].tm_packet_id):
                # Because the latest packet is likely to be a rerequested one, keep that one
                # TODO proper check on which packet is corrupted
                logging.warning(" Duplicates found: " + str(self.packets[i].packet_name) +
                                ' and ' + str(self.packets[i+1].packet_name) + ". Removing the first one")
                if (self.packets[i].data[90:] != self.packets[i+1].data[90:]):
                    logging.error(" DUPLICATE Image Packet Data is actually not identical")
                    logging.debug(' DUPLICATE #1 '+ str(self.packets[i]))
                    logging.debug(' DUPLICATE #2 '+ str(self.packets[i+1]))
                self.packets.pop(i)
            else:
                i = i + 1
        
        return self



    def reconstruct(self):
        """Reconstruct the image from available packets"""

        # First sort the packets
        self = self.sort_packets()

        # Check for missing packets (reconstruct image in any case)
        accept_corrupted = True
        missing_packets = self.get_missing_packets(True) # Exclude corrupted packets

        image_data = bytearray(0)

        if (self.camera_type == 'uCAM'):

            # Go through all available packets
            available_i = 0
            for i in range(self.number_of_packets):
                # Fill missing packet data
                if (i in missing_packets):
                    if (i == 0):
                        # First packet can be forged
                        image_data = image_data + bytes.fromhex('ffd8ffdb0084000d09090b0a080d0b0a0b0e0e0d0f13201513121213271c1e17202e2931302e292d2c333a4a3e333646372c2d405741464c4e525352323e5a615a50604a51524f010e0e0e131113261515264f352d354f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4fffc401a2000001050101010101010000000000000000')
                    else:
                        image_data = image_data + bytearray(158) # Default image data length
                else:
                    image_data = (image_data +
                            self.packets[available_i].data[94:94+self.packets[available_i].data_packet_size])
                    available_i = available_i + 1

            return image_data

        elif (self.camera_type == 'FLIR'):
            
            # Go through all available packets
            available_i = 0
            for i in range(self.number_of_packets):
                # Fill missing packet data
                if (i in missing_packets):
                    image_data = image_data + bytearray(160) # Default image data length
                else:
                    image_data = (image_data +
                            self.packets[available_i].data[94:])
                    available_i = available_i + 1

            return image_data



def sort_biolab_packets(packet_list,
                        incomplete_images,
                        receiver,
                        image_timeout = timedelta(minutes = 60),
                        biolab_memory_slot_change_detection = False):
    """
    Takes packet list and incomplete images. Returns list of incomplete images with sorted packets.

        Parameters:
            file_path (str): Location of the test bench data file

        Returns:
            packet_list (list): list of extracted BIOLAB packets
    """

    flir_init_packets = []
    flir_data_packets = []
    ucam_init_packets = []
    ucam_data_packets = []
    other_packets =[]

    # Go through the packet list
    while (len(packet_list)):
        packet = packet_list.pop(0)

        if (not packet.in_spec()):
            logging.error(packet.packet_name + " is not a WAPS Image Packet")
            continue

        global current_biolab_memory_slot
        # Important to recognise when the currently unfinished images are overwritten
        if (biolab_memory_slot_change_detection and
            current_biolab_memory_slot != packet.biolab_current_image_memory_slot):
            logging.info('  Update of active Memory slot ' + str(packet.biolab_current_image_memory_slot) + ' Previous: ' + str(current_biolab_memory_slot))
            for i in range(len(incomplete_images)):
                if (incomplete_images[i].memory_slot == packet.biolab_current_image_memory_slot):
                    incomplete_images[i].overwritten = True
                    logging.warning(' Incomplete image ' + incomplete_images[i].image_name + ' has been overwritten')
            current_biolab_memory_slot = packet.biolab_current_image_memory_slot

        
        global image_transmission_in_progress

        # Process the packet according to Generic TM ID (packet.data[84])
        # Only TM IDs of interest processed

        # FLIR camera number of packets (0x4100)
        if (packet.generic_tm_id == 0x4100):
            """(Generic TM ID 0x4100, Generic TM Type set with corresponding Picture ID, 0 to 7, and Packet ID to 0x000)."""
            if (not len(flir_init_packets)):
                flir_init_packets.append([packet.image_memory_slot,1])
            else:
                matching_memory_slot_found = False
                for i in range(len(flir_init_packets)):
                    if (flir_init_packets[i][0] == packet.image_memory_slot):
                        flir_init_packets[i][1] = flir_init_packets[i][1] + 1
                        matching_memory_slot_found = True
                        break
                if (not matching_memory_slot_found):
                    flir_init_packets.append([packet.image_memory_slot,1])
            receiver.total_waps_image_packets = receiver.total_waps_image_packets + 1
            receiver.total_initialized_images = receiver.total_initialized_images + 1

            # Track whether image is being trasmitted
            image_transmission_in_progress = True

            if (packet.tm_packet_id != 0):
                logging.warning(packet.packet_name + ' Packet ID is not zero: ' + str(packet.tm_packet_id))
            
            # Number of packets that contain this image (Byte# 90-91)
            image_number_of_packets = BIOLAB_Packet.word(packet.data[90:92])

            # Create an image with the above data
            new_image = WAPS_Image("FLIR", packet)

            # Check for overwritten memory slot and whether this is a duplicate image
            duplicate_image = False
            for index, image in enumerate(incomplete_images):
                if (image.camera_type == new_image.camera_type and
                    image.memory_slot == new_image.memory_slot and
                    image.number_of_packets == new_image.number_of_packets and
                    image.time_tag == new_image.time_tag):
                    logging.warning(' Duplicated image detected')
                    duplicate_image = True
                elif (image.memory_slot == new_image.memory_slot):
                    incomplete_images[index].overwritten = True
                    logging.warning(' Previous image in memory slot ' + str(image.memory_slot) + ' overwritten')
                    check_image_timeouts(incomplete_images, image_timeout, interface)
            if (duplicate_image):
                break

            logging.info('  New FLIR image in Memory slot ' +  str(packet.image_memory_slot) +
                         ' with ' +  str(image_number_of_packets) + ' expected packets (' +
                         new_image.image_name + ')')

            # Add image to the incomplete list
            incomplete_images.append(new_image)

            

        # FLIR camera picture packet
        elif (packet.generic_tm_id == 0x4200):
            """(Generic TM ID 0x4200, Generic TM Type set with corresponding Picture ID, 0 to 7, and Packet ID is incremented)."""
            if (not len(flir_data_packets)):
                flir_data_packets.append([packet.image_memory_slot,1,[packet.tm_packet_id]])
            else:
                matching_memory_slot_found = False
                for i in range(len(flir_data_packets)):
                    if (flir_data_packets[i][0] == packet.image_memory_slot):
                        flir_data_packets[i][1] = flir_data_packets[i][1] + 1
                        flir_data_packets[i][2].append(packet.tm_packet_id)
                        matching_memory_slot_found = True
                        break
                if (not matching_memory_slot_found):
                    flir_data_packets.append([packet.image_memory_slot,1])
            receiver.total_waps_image_packets = receiver.total_waps_image_packets + 1

            # Track whether image is being trasmitted
            image_transmission_in_progress = True

            # Search through incomplete images, matching image_memory_slot
            found_matching_image = False
            for i in range(len(incomplete_images)):
                if (incomplete_images[i].memory_slot == packet.image_memory_slot and
                    not incomplete_images[i].overwritten and
                    packet.source_file_timestamp < incomplete_images[i].timestamp + image_timeout):
                    found_matching_image = True

                    incomplete_images[i].add_packet(packet)
                    incomplete_images[i].update = True
                    break
            
            if (not found_matching_image):
                logging.error(packet.packet_name + ' matching image with memory slot ' + str(packet.image_memory_slot) + ' not found')

       # μCam number of picture packets
        elif (packet.generic_tm_id == 0x5100):
            """(Generic TM ID 0x5100, Generic TM Type set with corresponding Picture ID, 0 to 7, and Packet ID to 0x000)."""
            if (not len(ucam_init_packets)):
                ucam_init_packets.append([packet.image_memory_slot,1])
            else:
                matching_memory_slot_found = False
                for i in range(len(ucam_init_packets)):
                    if (ucam_init_packets[i][0] == packet.image_memory_slot):
                        ucam_init_packets[i][1] = ucam_init_packets[i][1] + 1
                        matching_memory_slot_found = True
                        break
                if (not matching_memory_slot_found):
                    ucam_init_packets.append([packet.image_memory_slot,1])
            receiver.total_waps_image_packets = receiver.total_waps_image_packets + 1
            receiver.total_initialized_images = receiver.total_initialized_images + 1

            # Track whether image is being trasmitted
            image_transmission_in_progress = True

            if (packet.tm_packet_id != 0):
                logging.error(packet.packet_name + ' - Packet ID is not zero')
                continue

            # Create an image with the above data
            new_image = WAPS_Image("uCAM", packet)

            # Check for overwritten memory slot and whether this is a duplicate image
            duplicate_image = False
            for index, image in enumerate(incomplete_images):
                if (image.camera_type == new_image.camera_type and
                    image.memory_slot == new_image.memory_slot and
                    image.number_of_packets == new_image.number_of_packets and
                    image.time_tag == new_image.time_tag):
                    logging.warning(' Duplicated image detected')
                    duplicate_image = True
                elif (image.memory_slot == new_image.memory_slot):
                    incomplete_images[index].overwritten = True
                    logging.warning(' Previous image in memory slot ' + str(image.memory_slot) + ' overwritten')
                    check_image_timeouts(incomplete_images, image_timeout, receiver.interface)
            if (duplicate_image):
                break

            logging.info('  New uCAM image in Memory slot ' +  str(packet.image_memory_slot) +
                         ' with ' +  str(packet.image_number_of_packets) + ' expected packets (' +
                         new_image.image_name + ')')

            # Add image to the incomplete list
            incomplete_images.append(new_image)


            
        # μCam picture packet
        elif (packet.generic_tm_id == 0x5200):
            """(Generic TM ID 0x5200, Generic TM Type set with corresponding Picture ID, 0 to 7, and Packet ID is incremented)."""
            if (not len(ucam_data_packets)):
                ucam_data_packets.append([packet.image_memory_slot,1,[packet.tm_packet_id]])
            else:
                matching_memory_slot_found = False
                for i in range(len(ucam_data_packets)):
                    if (ucam_data_packets[i][0] == packet.image_memory_slot):
                        ucam_data_packets[i][1] = ucam_data_packets[i][1] + 1
                        ucam_data_packets[i][2].append(packet.tm_packet_id)
                        matching_memory_slot_found = True
                        break
                if (not matching_memory_slot_found):
                    ucam_data_packets.append([packet.image_memory_slot,1])
            receiver.total_waps_image_packets = receiver.total_waps_image_packets + 1

            # Track whether image is being trasmitted
            image_transmission_in_progress = True

            # Search through incomplete images, matching by image_memory_slot
            found_matching_image = False
            for i in range(len(incomplete_images)):
                if (incomplete_images[i].memory_slot == packet.image_memory_slot and
                    not incomplete_images[i].overwritten and
                    packet.source_file_timestamp < incomplete_images[i].timestamp + image_timeout):
                    found_matching_image = True

                    incomplete_images[i].add_packet(packet)
                    incomplete_images[i].update = True
                    break
            
            if (not found_matching_image):
                logging.error(packet.packet_name + ' matching image with image memory slot ' + str(packet.image_memory_slot) + ' not found')

        else:
            if (not len(other_packets)):
                other_packets.append([packet.generic_tm_id,1])
            else:
                matching_generic_tm_id = False
                for i in range(len(other_packets)):
                    if (other_packets[i][0] == packet.generic_tm_id):
                        other_packets[i][1] = other_packets[i][1] + 1
                        matching_generic_tm_id = True
                        break
                if (not matching_generic_tm_id):
                    other_packets.append([packet.generic_tm_id,1])

            if (image_transmission_in_progress):
                # An image is sent in one telemetry sequence
                # Each single packet request triggers this change as well
                logging.debug(' No more image packets in the current sequence')

                # Go through incomplete images and mark that transmission is finished
                for i in range(len(incomplete_images)):
                    if (incomplete_images[i].image_transmission_active):
                        incomplete_images[i].image_transmission_active = False

                # Reset transmission status
                image_transmission_in_progress = False

    # Relevant packet count printout
    if (len(flir_init_packets) or len(flir_data_packets) or len(ucam_init_packets) or len(ucam_data_packets)):
        logging.info('  New WAPS Image packets from "' + packet.source_file + '":')
        if (len(flir_init_packets)):
            for counts in flir_init_packets:
                logging.info('\t FLIR_init Memory slot ' + str(counts[0]) +
                             ' Count: ' + str(counts[1]))
        if (len(flir_data_packets)):
            for counts in flir_data_packets:
                logging.info('\t FLIR_data Memory slot ' + str(counts[0]) +
                             ' Count: ' + str(counts[1]) +
                             ' \t Packet numbers: ' + WAPS_Image.number_sequence_printout(counts[2]))
        if (len(ucam_init_packets)):
            for counts in ucam_init_packets:
                logging.info('\t uCAM_init Memory slot ' + str(counts[0]) +
                             ' Count: ' + str(counts[1]))
        if (len(ucam_data_packets)):
            for counts in ucam_data_packets:
                logging.info('\t uCAM_data Memory slot ' + str(counts[0]) +
                             ' Count: ' + str(counts[1]) +
                             ' \t Packet numbers: ' + WAPS_Image.number_sequence_printout(counts[2]))
    else:
        logging.debug(" - No relevant image packets found")
    if (len(other_packets)):
        logging.debug('  Other BIOLAB packets:')
        for counts in other_packets:
            logging.debug('\t TM ID:  ' + hex(counts[0]) +
                          ' Count: ' + str(counts[1]))
    
    if (receiver.interface):
        receiver.interface.update_stats()

    return incomplete_images



def write_file(image_data, file_path, filetype = 'wb', interface = None):
    """Write image to hard drive"""

    readtype = 'rb'
    if (filetype == 'w'):
        readtype = 'r'

    update_file_path = False
    # Check existing file
    try:
        version_number = 2
        while os.path.exists(file_path):
            with open(file_path, readtype) as file:
                file_data = file.read()
                if (file_data == image_data):
                    logging.info('File ' + file_path + " with identical data exists already. No need to overwrite.")
                    return True
                else:
                    logging.info('File ' + file_path + " exists already but data is different.")
                    # Change file name to indicate new version
                    file_path = file_path[:file_path.rfind('.')] + 'v' + str(version_number) + file_path[file_path.rfind('.'):]

    except IOError:
        pass

    # Write the file
    try:
        with open(file_path, filetype) as file:
            file.write(image_data)
            logging.info("Saved file: " + str(file_path))
            if (interface):
                file_name = file_path[file_path.rfind('/')-8:]
                interface.update_latets_file(file_name)

    except IOError:
        logging.error('Could not open file for writing: ' + file_path)
        return False

    # Successful write
    return True



def save_images(incomplete_images, output_path, receiver, save_incomplete = True):
    """
    Incomplete images and output path. Returns list of incomplete images with sorted packets.

        Parameters:
            

        Returns:
            
    """
    interface = receiver.interface
    finished_image_indexes = []
    
    for index, image in enumerate(incomplete_images):

        # Make sure folder with today's path exists
        date_path = output_path + image.timestamp.strftime('%Y%m%d') + '/'
        if (not os.path.exists(date_path) or
            not os.path.isdir(date_path)):
            os.mkdir(date_path)

        successful_write = False

        # Update interface if available
        if (interface):
            interface.update_image_data(image)

        # Ignore incomplete images
        if (not save_incomplete and
            not image.is_complete() and
            image.image_transmission_active):
            continue

        # Ignore if there is no update on the image
        if (not image.update):
            continue
        
        # Get image binary data first
        image_data = image.reconstruct()
        # Add completion percentage to the file name
        missing_packets = image.get_missing_packets()
        image_percentage = '_'+ str(int(100.0*(image.number_of_packets - len(missing_packets))/image.number_of_packets))
        completeness_message = ('Image ' + image.image_name + ' is ' +
                                 image_percentage[1:] + '% complete (' +
                                 str(image.number_of_packets - len(missing_packets)) +
                                 '/' + str(image.number_of_packets) + ')')
        if (len(missing_packets)):
            completeness_message =  (completeness_message + '. Missing packets: ' +
                         WAPS_Image.number_sequence_printout(missing_packets))
            
        if (not len(missing_packets) or image.image_transmission_active):
            logging.info(completeness_message)
        else:
            logging.warning(completeness_message)

        if (not len(missing_packets)):
            receiver.total_completed_images = receiver.total_completed_images + 1

        
        if (image.camera_type == 'uCAM'):
            # Sanity check the data
            if (image_data[0] != 0xFF or
                image_data[1] != 0xD8 or
                image_data[2] != 0xFF or
                image_data[3] != 0xDB):
                logging.warning(image.image_name + ' does not have a .JPG header')
            
            # Image data is saved as is, binary
            file_path = date_path + image.image_name + image_percentage + '.jpg'
            
            successful_write = write_file(image_data, file_path, 'wb', interface)
            if image.is_complete() and successful_write:
                finished_image_indexes.append(index)
                
        elif (image.camera_type == 'FLIR'):
            # TM data is first 480 bytes, then 9600 bytes of data
            tm_length = 480
            data_length = 9600

            if (len(image_data) != tm_length + data_length):
                logging.warning(str(image.image_name) + ' has incorrect data size: ' + str(len(image_data)))
        
            # FLIR telemetry data is saved into a text file
            file_path_tm = date_path + image.image_name + image_percentage + '_tm.txt'
            
            tm_image_data = ""
            for i in range(int(tm_length/2)):
                if (i < 80):
                    tm_image_data = tm_image_data + 'A'
                elif (i < 160 and i >= 80):
                    tm_image_data = tm_image_data + 'B'
                else:
                    tm_image_data = tm_image_data + 'C'
                tm_image_data = tm_image_data + (str(i%80) + ':' +
                        str(BIOLAB_Packet.word(image_data[i*2:i*2+2])) +
                        '\n')

            successful_write = write_file(tm_image_data, file_path_tm, 'w', interface)
            if not successful_write:
                continue
            
            # FLIR Image data is converted to .csv file
            file_path_csv = date_path + image.image_name + image_percentage + '_data.csv'
            
            csv_image_data = str(BIOLAB_Packet.word(image_data[tm_length:tm_length+2])) # first value
            for i in range(1, int((len(image_data)-tm_length)/2)):
                if (i % 80): # 80 values in one row
                    csv_image_data = csv_image_data + ','
                else: 
                    csv_image_data = csv_image_data + '\n'
                csv_image_data = csv_image_data + str(BIOLAB_Packet.word(image_data[tm_length+i*2:tm_length+i*2+2]))
            csv_image_data = csv_image_data + '\n'
            
            successful_write = write_file(csv_image_data, file_path_csv, 'w', interface)
            if not successful_write:
                continue
            
            
            # FLIR Image data is converted is saved as .bmp file
            file_path = date_path + image.image_name + image_percentage + '.bmp'

            # Structure image data
            array_image_data = []
            for i in range(int((len(image_data)-tm_length)/2)):
                pixel = BIOLAB_Packet.word(image_data[tm_length+i*2:tm_length+i*2+2])
                array_image_data.append([pixel])
            
     
            array_image_data = np.array(array_image_data)
            min_value = min(array_image_data)
            max_value = max(array_image_data)
            array_image_data = np.uint8((array_image_data - min_value) * (256.0/(max_value - min_value)))
            array_image_data = array_image_data.reshape((60,80))
            img = Image.fromarray(array_image_data, 'L')
            output_image = io.BytesIO()
            img.save(output_image, format='BMP')

            successful_write = write_file(output_image.getvalue(), file_path, 'wb', interface)
            if image.is_complete() and successful_write:
                finished_image_indexes.append(index)

        # On a successful file write note that there are not more updates
        if (successful_write):
            incomplete_images[index].update = False
            
            # Since the file write was successful, previous versions of the files
            try:
                if (incomplete_images[index].latest_saved_file):
                    if os.path.exists(incomplete_images[index].latest_saved_file):
                        os.remove(incomplete_images[index].latest_saved_file)
                    if os.path.exists(incomplete_images[index].latest_saved_file[:-4] + '_tm.txt'):
                        os.remove(incomplete_images[index].latest_saved_file[:-4] + '_tm.txt')
                    if os.path.exists(incomplete_images[index].latest_saved_file[:-4] + '_data.csv'):
                        os.remove(incomplete_images[index].latest_saved_file[:-4] + '_data.csv')
                    logging.info('Removed previous version of this file: ' + incomplete_images[index].latest_saved_file)

            except IOError:
                pass

            # And note the latest written down file
            incomplete_images[index].latest_saved_file = file_path

        # Update interface if available
        if (interface):
            interface.update_image_data(image)
            interface.update_stats()

    # Remove fully complete and written down images from the incomplete list
    if (len(finished_image_indexes)):
        for index in finished_image_indexes[::-1]:
            logging.debug(" Image completed and removed from memory:")
            logging.debug(incomplete_images[index])
            incomplete_images.pop(index)

    # Go through incomplete images 

    return incomplete_images



def check_image_timeouts(incomplete_images, image_timeout, interface = None):
    """
    Incomplete images as input. Returns list of incomplete images still within grace period.
    """

    outdated_image_indexes = []

    for index, image in enumerate(incomplete_images):
        if (datetime.now() > incomplete_images[index].timestamp + image_timeout or
            incomplete_images[index].overwritten):
            outdated_image_indexes.append(index)

    # Remove the outdated images from incomplete images list
    if (len(outdated_image_indexes)):
        for index in outdated_image_indexes[::-1]:
            logging.warning(' '+ str(incomplete_images[index].image_name) + ' is incomplete (' +
                            str(len(incomplete_images[index].packets)-len(incomplete_images[index].get_missing_packets())) +
                            '/' + str(incomplete_images[index].number_of_packets) + ') and OUTDATED')
            # Update interface if available
            incomplete_images[index].outdated = True
            if (interface):
                interface.update_image_data(incomplete_images[index])
            incomplete_images.pop(index)

    return incomplete_images
