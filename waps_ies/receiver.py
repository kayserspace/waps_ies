#!/usr/bin/env python

# Script: TCPReceiver.py
# Author: Georgi Olentsenko
# Purpose: Receiving CCSDS packets over TCP and filtering BIOLAB packets
# Version: 2023-XX-XX xx:xx
#
# Change Log:
#  2023-XX-XX
#  - initial version

import logging
from datetime import datetime
import socket
import time
from struct import unpack
from waps_ies import interface, processor, database, waps_packet
from datetime import timedelta
import os
import sqlite3

CCSDS1HeaderLength =  6
CCSDS2HeaderLength = 10
CCSDSHeadersLength = CCSDS1HeaderLength + CCSDS2HeaderLength

BIOLAB_ID_position = 40

#class CCSDS_packet:
    
    
class TCP_Receiver:
    """
    TCP Receiver class

    Attributes
    ----------

    Methods
    -------

    """

    socket_connection_failure_count = 0

    log_path = 'log/'
    log_level = logging.INFO
    log_file = None
    log_start = 0

    last_packet_CCSDS_time = datetime(1980, 1, 6)

    ECs_state = []
    
    def __init__(self, address, port, output_path, tcp_timeout = '2.1'):
        """
        Initialize the TCP connection

        Attributes
        ----------

        Methods
        -------

        """

        self.socket = None
        self.server_address = ( address, int(port) )
        self.tcp_timeout = tcp_timeout
        self.connected = False
        
        self.output_path = output_path

        self.incomplete_images = []
    
        self.continue_running = True
        self.interface = None

        # TODO implement
        self.image_timeout = timedelta(minutes = 60)

        self.memory_slot_change_detection = False

        # Status parameters
        self.timeout_notified = False

        self.total_packets_received = 0
        self.total_biolab_packets = 0
        self.total_waps_image_packets = 0
        self.total_initialized_images = 0
        self.total_completed_images = 0
        self.total_lost_packets = 0
        self.total_corrupted_packets = 0

        self.db = database.WAPS_Database()
        

    def start_new_log(self):
        """ Start a new log file """

        # Set up logging
        new_log_filename = (self.log_path + 'WAPS_IES_' +
                            datetime.now().strftime('%Y%m%d_%H%M%S') + '.log')
        if (self.log_file):
            logging.info( " Closing this log file. Next one is: " + new_log_filename)
        logging.basicConfig(filename = new_log_filename,
                            format='%(asctime)s:%(levelname)s:%(message)s',
                            level=self.log_level,
                            force=True)
        logging.getLogger().addHandler(logging.StreamHandler())
        if (self.log_file):
            logging.info( " Previos log file: " + self.log_file)

        self.log_start = datetime.now()
        self.log_file = new_log_filename


    def add_interface(self, ies_interface):
        """ Add an interface object to the trackerer """

        # Check interface type before adding
        if (type(ies_interface) is interface.WAPS_interface):
            logging.debug(' # Interface added linked to IES')
            self.interface = ies_interface
        else:
            logging.warning(' Interface has wrong object type')

    def get_status(self):
        """ Get receiver status message """
        current_time = self.last_packet_CCSDS_time.strftime("%Y/%m/%d %H:%M:%S")
        status_message = ("# CCSDS Time: %s P:%d:%d:%d M:%d:%d, I:%d:%d" %
                                    (current_time,
                                    self.total_packets_received,
                                    self.total_biolab_packets,
                                    self.total_waps_image_packets,
                                    self.total_lost_packets,
                                    self.total_corrupted_packets,
                                    self.total_initialized_images,
                                    self.total_completed_images))
        return status_message

    def get_ec_position(self, ec_address):
        """ Get EC position from address """

        for ec in self.ECs_state:
            if (ec["ec_address"] == ec_address):
                return ec["ec_position"]

        return '?'

    def get_ecs_state_index(self, ec_address):
        """ Get EC index in the ECs_state table """

        # Find existing entry
        for i in range(len(self.ECs_state)):
            if (self.ECs_state[i]["ec_address"] == ec_address):
                return i

        # Create a new entry
        ec = {  "ec_address": ec_address,
                "ec_position": '?',
                "gui_column": None, # Update on receipt of packets
                "transmission_active": False,
                "last_memory_slot": None
                }
        self.ECs_state.append(ec)

        return len(self.ECs_state) - 1

    def assign_ec_column(self, ec_address):
        """ Assign an EC column in the WAPS GUI """

        index = self.get_ecs_state_index(ec_address)
        if (self.ECs_state[index]["gui_column"] == None):

            # Get current column occupation
            column_occupation = [None, None, None, None]
            for i, ec in enumerate(self.ECs_state):
                if(ec["gui_column"] != None):
                    if (ec["gui_column"] < 4 and ec["gui_column"] >= 0):
                        column_occupation[ec["gui_column"]] = ec["ec_address"]

            # Assign an empty column
            for i in range(4):
                if(not column_occupation[i]):
                    self.ECs_state[index]["gui_column"] = i
                    break

            if(self.ECs_state[index]["gui_column"] == None):
                logging.warning(' All GUI columns are occupied already')
            elif (self.interface):
                logging.info( " EC address " + str(self.ECs_state[index]["ec_address"]) +
                            " with position " + self.ECs_state[index]["ec_position"] +
                            " occupies GUI column " + str(self.ECs_state[index]["gui_column"]))
                self.interface.update_column_occupation(self.ECs_state[index]["gui_column"],
                                                        self.ECs_state[index]["ec_address"],
                                                        self.ECs_state[index]["ec_position"])

    def start(self):
    
        try:
        
            while self.continue_running:

                # On change of date move on to a new log file
                if (datetime.now().strftime('%d') != self.log_start.strftime('%d')):
                    self.start_new_log()
            
                if (not self.connected):
                    try:
                        # Initialize socket
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        # Packet expected to be received at least once a second.
                        # Allowing more than double the time: 2.1 seconds
                        self.socket.settimeout(float(self.tcp_timeout))
                        self.socket.connect(self.server_address)
                        self.connected = True
                        if (self.interface):
                            self.interface.update_server_connected()

                        logging.info(" # TCP connection to %s:%s established",
                                       self.server_address[0], str(self.server_address[1]))
                        self.socket_connection_failure_count = 0

                    except Exception as err:
                        self.socket_connection_failure_count = self.socket_connection_failure_count + 1
                        if (self.socket_connection_failure_count < 10):
                            logging.error(" Could not connect to socket. Error:" + str(err))
                        else:
                            if (not self.socket_connection_failure_count%60):
                                logging.error(" Connection failed " +
                                            str(self.socket_connection_failure_count) + " times. Error:" + str(err))
                            print(" Connection failed " + str(self.socket_connection_failure_count)
                                            + " times\r", end='')
                        time.sleep(1)
                        continue
                
                       
                try:
                    # Get the next packet
                    CCSDS_header = self.socket.recv(CCSDSHeadersLength)
                    self.timeout_notified = False

                    # Increase packet count
                    if (len(CCSDS_header)):
                        self.total_packets_received = self.total_packets_received + 1

                    # Update interfeace status
                    if (self.interface):
                        self.interface.update_server_active()
                        self.interface.update_CCSDS_count()
                    
                    if (len(CCSDS_header) != CCSDSHeadersLength):
                        raise Exception("Header reception failed")
                        
                    ccsds1PacketLength = unpack( '>H', CCSDS_header[4:6] )[0]
                    
                    # calculate & receive remaining bytes in packet:
                    packetDataLength = ccsds1PacketLength + 1 - CCSDS2HeaderLength
                    
                    waps_packet = None
                    packetData = self.socket.recv( packetDataLength )
                    # TODO see if this is actually needed
                    if( len( packetData ) != packetDataLength ):
                        logging.debug("Expected data length of " + str(packetDataLength) +
                                        ' vs actual ' + str(len( packetData )))
                        packetData2 = self.socket.recv( packetDataLength - len( packetData ))
                        if( len( packetData2 ) != packetDataLength - len( packetData ) ):
                            logging.error("Failed to read complete CCSDS Data Block from TCP link")
                        else:
                            logging.debug("Got the rest with a new request")
                            waps_packet = self.process_CCSDS_packet( CCSDS_header + packetData + packetData2 )
                    else:
                        waps_packet = self.process_CCSDS_packet( CCSDS_header + packetData )


                    
                    if (waps_packet):
                        # Sort packets into images
                        self.incomplete_images = processor.sort_biolab_packets([waps_packet],
                                                                               self.incomplete_images,
                                                                               self,
                                                                               self.image_timeout,
                                                                               self.memory_slot_change_detection)

                        # Reconstruct and save images, keeping in memory the incomplete ones
                        self.incomplete_images = processor.save_images(self.incomplete_images,
                                                                       self.output_path,
                                                                       self,
                                                                       False) # Do not save incomplete images

                        # Show current state of incomplete images if a WAPS image packet has been received
                        if (waps_packet.is_waps_image_packet):
                            processor.print_incomplete_images_status(self.incomplete_images)

                    # Check if any image times out
                    self.incomplete_images = processor.check_overwritten_images(self.incomplete_images,
                                                                                self.interface)

                    # Status information after all of the processing
                    status_message = self.get_status() + '\r'
                    if (self.logging_level == logging.DEBUG):
                        logging.debug(status_message)
                    else:
                        print(status_message, end='')

                
                except TimeoutError:
                    if (not self.timeout_notified):
                        logging.warning("\nNo CCSDS packets received for more than " +
                                        str(self.tcp_timeout) +
                                        " seconds")
                        self.timeout_notified = True
                        if (self.interface):
                            self.interface.update_server_connected()

                    # Check if any image times out
                    self.incomplete_images = processor.check_overwritten_images(self.incomplete_images,
                                                                            self.interface)

                except KeyboardInterrupt:
                    raise KeyboardInterrupt

                except Exception as err:
                    logging.error(str(err))
                    self.connected = False
                    self.socket.close()
                    if (self.interface):
                        self.interface.update_server_disconnected()
                    raise err
                    time.sleep(1)
                
        except KeyboardInterrupt:
            logging.info(' # Keyboard interrupt, closing')
            
        finally:
            # Close interface if it is running
            if (self.interface):
                self.interface.close()

            if (self.db):
                self.db.database.close()
                logging.info(" # Closed database")
                
            self.socket.close()
            logging.info(" # Disconnected from server")
            logging.info("      Sessions total numbers")
            logging.info("  CCSDS packets received:      %d", self.total_packets_received)
            logging.info("  BIOLAB TM packets received:  %d", self.total_biolab_packets)
            logging.info("  WAPS image packets received: %d", self.total_waps_image_packets)
            logging.info("  Initializaed images:         %d", self.total_initialized_images)
            logging.info("  Completed images:            %d", self.total_completed_images)
            logging.info("  Lost packets:                %d", self.total_lost_packets)
            logging.info("  Corrupted packets:           %d", self.total_corrupted_packets)

        

    def process_CCSDS_packet(self, CCSDS_packet):
        """
        Takes a CCSDS packet, extracts WAPS image packet if present

            Parameters:
                file_path (str): Location of the archive data file

            Returns:
                packet_list (list): list of extracted BIOLAB packets
        """

        CCSDS_packet_length = len(CCSDS_packet)
        
        
        if( len( CCSDS_packet ) < CCSDSHeadersLength ):
            logging.error(" CCSDS packet is too short for a full CCSDS header: %d bytes" % len( CCSDS_packet ))
            return
            
        try:
            # CCSDS primary header:
            word1 = unpack( '>H', CCSDS_packet[0:2] )[0]
            ccsds1VersionNumber  = ( word1 >> 13 ) & 0x0007 # bits 0-2
            ccsds1Type           = ( word1 >> 12 ) & 0x0001 # bit 3
            ccsds1SecondaryHdr   = ( word1 >> 11 ) & 0x0001 # bit 4
            ccsds1APID           = ( word1 >>  0 ) & 0x03ff # bits 5-15
            word2 = unpack( '>H', CCSDS_packet[2:4] )[0]
            ccsds1SeqFlags       = ( word2 >> 14 ) & 0x0003 # bits 0-1
            ccsds1SeqCounter     = ( word2 >>  0 ) & 0x3fff # bits 2-15
            ccsds1PacketLength = unpack( '>H', CCSDS_packet[4:6] )[0]

            # CCSDS secondary header:
            ccsds2CoarseTime = unpack( '>L', CCSDS_packet[6:10] )[0]
            word3 = unpack( '>H', CCSDS_packet[10:12] )[0]
            ccsds2FineTime = ( ( word3 >> 8 ) & 0x00ff ) * 1000 / 256 # calculate into milliseconds from bits 0-7
            currentTime = datetime.now()
            ccsdsTime = datetime(1980, 1, 6) + timedelta(seconds=ccsds2CoarseTime+ccsds2FineTime/1000.0)
            ccsds2TimeID     = ( word3 >> 6 ) & 0x0003   # bits 8-9
            ccsds2CW         = ( word3 >> 5 ) & 0x0001   # bit 10
            ccsds2ZOE        = ( word3 >> 4 ) & 0x0001   # bit 11
            ccsds2PacketType = ( word3 >> 0 ) & 0x000f   # bits 12-15

            ccsds2PacketID32 = unpack( '>L', CCSDS_packet[12:16] )[0]
            ccsds2Spare         = ( ccsds2PacketID32 >> 31 ) & 0x00000000
            ccsds2ElementID     = ( ccsds2PacketID32 >> 27 ) & 0x0000000f
            ccsds2PacketID27    = ( ccsds2PacketID32 >>  0 ) & 0x07ffffff

            CCSDS_str = (" New CCSDS packet (%d bytes)\n      Received at %s\n" %
                    (len( CCSDS_packet ), str(currentTime)))

            strType = "System"
            if( ccsds1Type == 1 ): strType = "Payload"
            CCSDS_str = CCSDS_str + ("      Type: %s " % strType)
            CCSDS_str = CCSDS_str + ("APID: %d " % ccsds1APID)
            CCSDS_str = CCSDS_str + ("Length: %d\n" % ccsds1PacketLength)
            strElementID = "not mapped"
            if( ccsds2ElementID == 2 ): strElementID = "Columbus"
            CCSDS_str = CCSDS_str + ( "      Element ID: %d (%s) " % ( int( ccsds2ElementID ), strElementID ) )
            CCSDS_str = CCSDS_str + ( "Packet ID 27: %d\n" % ( ccsds2PacketID27 ) )
            CCSDS_str = CCSDS_str + ("      Packet timestamp: (coarse: %d fine: %d) %s" %
                            (ccsds2CoarseTime, ccsds2FineTime, str(ccsdsTime)) )

            logging.debug(CCSDS_str)

        except Exception as err:
            logging.debug(str(err))
            return

        # TODO more checks on teh CCSDS packet

        self.last_packet_CCSDS_time = ccsdsTime

        # Check packet length and BIOLAB ID
        if (CCSDS_packet_length < 42 or CCSDS_packet[BIOLAB_ID_position] != 0x40):
            logging.debug("      Not a BIOLAB TM packet")
            return

        BIOLAB_packet_length = CCSDS_packet[BIOLAB_ID_position + 1] * 2 + 4
        if (BIOLAB_packet_length < 254):
            logging.warning(" Unexpected BIOLAB packet length: %d", BIOLAB_packet_length)
        
        # Count BIOLAB packets
        self.total_biolab_packets = self.total_biolab_packets + 1
        if (self.interface):
            self.interface.update_stats()

        # Create BIOLAB packet as is
        packet =  waps_packet.BIOLAB_Packet(ccsdsTime, currentTime,
                            CCSDS_packet[BIOLAB_ID_position:BIOLAB_ID_position+BIOLAB_packet_length],
                            self)

        # If packet matches biolab specification add it to list
        if (packet.in_spec()):
            return packet