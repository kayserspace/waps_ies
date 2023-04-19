"""
Script: waps_image.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: WAPS PD image extraction software for operations at MUSC
         WAPS image class
Version: 2023-04-18 14:00, version 0.1

Change Log:
2023-04-18 version 0.1
 - initial version
"""

import uuid
import logging


class WapsImage:
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

    completion_time = -1

    def __init__(self, packet):
        """Image initialization with metadata"""

        self.uuid = str(uuid.uuid4())  # Random UUID

        self.ec_address = packet.ec_address
        self.ec_position = '?'
        self.memory_slot = packet.image_memory_slot
        if packet.generic_tm_id == 0x4100:
            self.camera_type = "FLIR"
        elif packet.generic_tm_id == 0x5100:
            self.camera_type = "uCAM"
        else:
            logging.debug(" Wrong Generic TM ID: %s",
                          hex(packet.generic_tm_id))
        self.number_of_packets = packet.image_number_of_packets
        self.acquisition_time = packet.acquisition_time
        self.ccsds_time = packet.ccsds_time
        self.time_tag = packet.time_tag
        self.image_name = ("EC_" + str(self.ec_address) + '_' +
                           self.camera_type + '_' +
                           self.ccsds_time.strftime('%H%M%S') + '_' +
                           'm' + str(self.memory_slot) + '_' +
                           str(self.time_tag))

        self.packets = []

        # Other variables
        self.overwritten = False
        self.image_transmission_active = True
        self.update = True
        self.latest_saved_file = None
        self.latest_saved_file_tm = None
        self.latest_saved_file_data = None
        self.outdated = False

    def __str__(self):
        """ Image metadata printout """

        self.packets = self.sort_packets()
        missing_packets = self.get_missing_packets()

        good_packets = self.number_of_packets-len(missing_packets)
        out = ("\nWAPS Image " + self.image_name + " information:"
               "\n - EC address: " + str(self.ec_address) +
               "\n - Camera type: " + self.camera_type +
               "\n - Image Memory Slot: " + str(self.memory_slot) +
               "\n - Acquisition Time: " +
               self.acquisition_time.strftime('%Y%m%d_%H%M') +
               "\n - CCSDS Time: " +
               self.ccsds_time.strftime('%Y%m%d_%H%M') +
               "\n - Initialization time tag: " + str(self.time_tag) +
               "\n - Completion: " +
               str(self.number_of_packets-len(missing_packets)) +
               r'/' + str(self.number_of_packets) +
               ' ' + str(int((good_packets)/self.number_of_packets*100.0)) +
               '%' + "\n - Transmission active: " +
               str(self.image_transmission_active) +
               "\n - Memory Slot overwritten: " + str(self.overwritten))

        if not self.image_transmission_active and len(missing_packets) > 0:
            first_packet_id = 0
            previous_packet_id = -1
            out = out + '\n - Correct Packets: \t ['
            first_entry = True
            for packet in self.packets:
                if packet.tm_packet_id not in missing_packets:
                    current_packet_id = packet.tm_packet_id
                    if not current_packet_id == previous_packet_id + 1:
                        if not first_entry:
                            out = out + ', '
                        if first_packet_id == previous_packet_id:
                            out = out + str(first_packet_id)
                        else:
                            out = out + (str(first_packet_id) +
                                         '-' + str(previous_packet_id))
                        first_packet_id = current_packet_id
                        first_entry = False
                previous_packet_id = current_packet_id
            if not first_entry:
                out = out + ', '
            if first_packet_id == previous_packet_id:
                out = out + str(first_packet_id)
            else:
                out = out + (str(first_packet_id) +
                             '-' + str(previous_packet_id))
            out = out + ']'
            out = out + ('\n - Missing or Incorrect Packets: \t' +
                         str(missing_packets))

        if self.latest_saved_file:
            out = out + ('\n - Latest saved image file: \t ' +
                         str(self.latest_saved_file))
        if self.latest_saved_file_tm:
            out = out + ('\n - Latest saved flir tm file: \t ' +
                         str(self.latest_saved_file_tm))
        if self.latest_saved_file_data:
            out = out + ('\n - Latest saved flir raw data file: \t ' +
                         str(self.latest_saved_file_data))

        return out

    def missing_packets_string(self,  exclude_corrupted=False):
        """ Number sequence printout """

        number_list = self.get_missing_packets(exclude_corrupted)

        if len(number_list) < 2:
            return str(number_list)

        previous_number = number_list[0]
        last_number = number_list[0]
        out = '[' + str(previous_number)
        dash_added = False
        for num in number_list[1:]:
            if (num == previous_number + 1 and not dash_added):
                out = out + '-'
                dash_added = True
            elif num != previous_number + 1:
                if last_number != previous_number:
                    out = out + str(previous_number)
                out = out + ', ' + str(num)
                last_number = num
                dash_added = False
            previous_number = num
        if last_number != previous_number:
            out = out + str(previous_number)
        out = out + ']'

        return out

    def add_packet(self, packet):
        """Append a new packet to an existing list"""

        # Check that the packet is according to specification
        if not packet.in_spec:
            return
        self.packets.append(packet)

    def is_complete(self):
        """ Check completeness of the image """

        # Check total number of packets
        if len(self.packets) < self.number_of_packets:
            logging.debug('%s is incomplete. %i/%i',
                          self.image_name,
                          len(self.packets),
                          self.number_of_packets)
            return False

        # Check if all the correct packets are present
        missing_packets = self.get_missing_packets()

        # If any packet is missing
        if len(missing_packets) != 0:
            return False

        return True

    def get_missing_packets(self, exclude_corrupted=False):
        """Get the missing packet list"""

        missing_packets = []
        try:
            # Check if all the correct packets are present
            completeness_array = [0] * self.number_of_packets
            for i, packet in enumerate(self.packets):
                if (packet.is_good_waps_image_packet() or
                        exclude_corrupted):
                    completeness_array[self.packets[i].tm_packet_id] = 1

            for i, present in enumerate(completeness_array):
                if not present:
                    missing_packets.append(i)

        except IndexError:
            logging.warning('%s - Unexpected tm packet id %i. Number image packets: %i. Actual packets: %i',
                            self.packets[i].packet_name,
                            self.packets[i].tm_packet_id,
                            self.number_of_packets,
                            len(self.packets))

        return missing_packets

    def packets_are_sequential(self):
        """ Check if packets in this image are sequential """

        missing_packets = self.get_missing_packets()

        # Check that the missing packet list is sequenctial
        count = len(missing_packets)
        if count > 1:
            for i in range(count-1):
                if missing_packets[i] + 1 != missing_packets[i + 1]:
                    return False

        # Check that the last packet missing is the last packet number expected
        if (count > 0 and
                missing_packets[count-1] != self.number_of_packets - 1):
            return False

        return True

    def sort_packets(self):
        """ Sort the packets of this image according to data packet number """

        # Sorting based of data packet number
        def get_packet_number(packet):
            return packet.tm_packet_id
        self.packets.sort(key=get_packet_number)

        # Check for duplicates
        i = 0
        while i < len(self.packets) - 1:
            if self.packets[i].tm_packet_id == self.packets[i+1].tm_packet_id:
                # Latest packet is likely to be a re-requested one, keep it
                # TODO proper check on which packet is corrupted
                logging.warning(" Duplicates found: %s and %s",
                                self.packets[i].packet_name,
                                self.packets[i+1].packet_name)
                if self.packets[i].data[90:] != self.packets[i+1].data[90:]:
                    logging.error(" DUPLICATE packets, data not identical:")
                    logging.debug(' DUPLICATE #1 %s', str(self.packets[i]))
                    logging.debug(' DUPLICATE #2 %s', str(self.packets[i+1]))
                self.packets.pop(i)
            else:
                i = i + 1

        return self.packets

    def reconstruct(self):
        """ Reconstruct the image from available packets """

        # First sort the packets
        self.packets = self.sort_packets()

        # Check for missing packets (reconstruct image in any case)
        accept_corrupted = True
        # Exclude corrupted packets
        missing_packets = self.get_missing_packets(accept_corrupted)

        image_data = bytearray(0)

        if self.camera_type == 'uCAM':

            # Go through all available packets
            available_i = 0
            for i in range(self.number_of_packets):
                # Fill missing packet data
                if i in missing_packets:
                    if i == 0:
                        # First packet can be forged
                        image_data = image_data + bytes.fromhex('ffd8ffdb0084000d09090b0a080d0b0a0b0e0e0d0f13201513121213271c1e17202e2931302e292d2c333a4a3e333646372c2d405741464c4e525352323e5a615a50604a51524f010e0e0e131113261515264f352d354f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4f4fffc401a2000001050101010101010000000000000000')
                    else:  # Default length
                        image_data = image_data + bytearray(158)
                else:
                    packet_size = self.packets[available_i].data_packet_size
                    image_data = (image_data +
                                  self.packets[available_i].data[94:94 +
                                                                 packet_size])
                    available_i = available_i + 1

        elif self.camera_type == 'FLIR':

            # Go through all available packets
            available_i = 0
            for i in range(self.number_of_packets):
                # Fill missing packet data
                if i in missing_packets:
                    image_data = image_data + bytearray(160)  # Default length
                else:
                    image_data = (image_data +
                                  self.packets[available_i].data[94:])
                    available_i = available_i + 1

        return image_data
