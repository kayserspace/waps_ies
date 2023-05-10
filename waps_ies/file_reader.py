"""
Script: file_reader.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: WAPS Image Extraction Software
         File read methods for WAPS IES testing based on files
Version: 2023-05-25 15:00, version 1.0

Change Log:
2023-04-18 version 0.1
 - initial version
2023-05-25 v 1.0
 - release
"""

from datetime import datetime
import logging
from waps_ies import waps_packet


def read_rt_file(file_path):
    """Takes file path of an rt data file and returns list of packets"""

    start_pointer = 0
    packet_list = []

    # Read the file
    try:
        with open(file_path, 'rb') as file:
            data = file.read()

            # Search the file for packets
            pointer = data.find(b'\x13\x00\x57\x30', start_pointer)  # First packet in the file
            while pointer > -1:

                # Confirm packet by BIOLAB ID
                biolab_id_position = pointer + 28

                if data[biolab_id_position] == 0x40:  # BIOLAB ID 0x40

                    packet_length = data[biolab_id_position + 1] * 2 + 4

                    # Create packet as is
                    packet = waps_packet.WapsPacket(datetime.now(),
                                                    datetime.now(),
                                                    data[biolab_id_position:biolab_id_position +
                                                         packet_length])

                    # If packet matches biolab specification add it to list
                    if packet.in_spec():
                        packet_list.append(packet)

                    # Find next packet packet
                    pointer = data.find(b'\x13\x00\x57\x30', biolab_id_position + packet_length)

                else:
                    # Find next packet packet
                    pointer = data.find(b'\x13\x00\x57\x30', pointer + 1)

        logging.debug(' - File contained: %i BIOLAB Packets', len(packet_list))

    except IOError:
        logging.error('Could not open file: %s', file_path)

    except IndexError:
        logging.debug('Unexpected end of file')

    return packet_list


def read_test_bed_file(file_path):
    """Takes file path for a "test bed" text file and returns list of packets"""

    packet_list = []

    # Read the file
    try:
        with open(file_path, 'r') as file:
            while True:
                # Each line is a packet
                dataline = file.readline()
                if dataline == '':  # end of file
                    break

                byte_dataline = bytearray(list(map(int, dataline.split(' ')[:-1])))

                # Create packet as is
                packet = waps_packet.WapsPacket(datetime.now(),
                                                datetime.now(),
                                                byte_dataline)

                # If packet matches biolab specification add it to list
                if packet.in_spec():
                    packet_list.append(packet)

    except IOError:
        logging.error('Could not open file: %s', file_path)
        return packet_list

    logging.info('File processed successfully')
    logging.info('\t- File contains %i packets', len(packet_list))

    return packet_list
