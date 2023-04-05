#!/usr/bin/env python

# Script: file_reader.py
# Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
# Purpose: Contains functions for extraction of packets from files
# Version: 2023-04-05 16:00, version 0.1
#
# Change Log:
#  2023-04-05 version 0.1
#  - initial version

from datetime import datetime
from waps_ies import waps_packet
import os
from struct import unpack
import logging

def read_rt_file(file_path):
    """
    Takes file path and returns list of packets

        Parameters:
            file_path (str): Location of the archive data file

        Returns:
            packet_list (list): list of extracted BIOLAB packets
    """
    
    start_pointer = 0
    packet_list = []
    
    # Read the file
    try:
        with open(file_path, 'rb') as file:
            data = file.read()
            timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))

            # Search the file for packets
            pointer = data.find(b'\x13\x00\x57\x30', start_pointer) # First packet in the file
            while (pointer > -1):

                # Confirm packet by BIOLAB ID
                biolab_id_position = pointer + 28
                
                if (data[biolab_id_position] == 0x40): # BIOLAB ID 0x40

                    packet_length = data[biolab_id_position + 1] * 2 + 4

                    # Create packet as is
                    packet =  waps_packet.BIOLAB_Packet(datetime.now(), datetime.now(),
                                        data[biolab_id_position : biolab_id_position + packet_length])

                    # If packet matches biolab specification add it to list
                    if (packet.in_spec()):
                        packet_list.append(packet)

                    # Find next packet packet
                    pointer = data.find(b'\x13\x00\x57\x30', biolab_id_position + packet_length)
                        
                
                else:
                    # Find next packet packet
                    pointer = data.find(b'\x13\x00\x57\x30', pointer + 1)

        logging.debug(' - File contained: ' + str(len(packet_list)) + ' BIOLAB Packets')

    except IOError:
        logging.error('Could not open file: ' + file_path)

    except IndexError:
        logging.debug('Unexpected end of file')
    
    return packet_list



def read_test_bed_file(file_path):
    """
    Takes file path and returns list of packets

        Parameters:
            file_path (str): Location of the test bench data file

        Returns:
            packet_list (list): list of extracted BIOLAB packets
    """

    packet_list = []

    # Read the file
    try:
        with open(file_path, 'r') as file:
            while True:
                # Each line is a packet
                dataline = file.readline()
                if (dataline == ''): # end of file
                    break
                    
                byte_dataline = bytearray(list(map(int, dataline.split(' ')[:-1])))

                # Create packet as is
                packet = waps_packet.BIOLAB_Packet(datetime.now(), datetime.now(),
                                                        byte_dataline)

                # If packet matches biolab specification add it to list
                if (packet.in_spec()):
                    packet_list.append(packet)

    except IOError:
        logging.error('Could not open file: ' + file_path)
        return packet_list

    logging.info('File processed successfully')
    logging.info('\t- File contains ' + str(len(packet_list)) + " packets")
    
    return packet_list
