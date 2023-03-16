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
from waps_ies import interface, processor
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

        self.ec_address_position_pairs = []

        # Status parameters
        self.timeout_notified = False

        self.logging_level = logging.INFO

        self.total_packets_received = 0
        self.total_biolab_packets = 0
        self.total_waps_image_packets = 0
        self.total_initialized_images = 0
        self.total_completed_images = 0
        self.total_lost_packets = 0
        self.total_corrupted_packets = 0

        # Database initialization
        if (not os.path.exists('waps_pd.db')):
            logging.warning("Database seems to be missing path does not exist. Creating it...")
        self.database = sqlite3.connect("waps_pd.db")
        self.db_cursor = self.database.cursor()
        logging.info(" # Opened database 'waps_pd.db'")

        # Check database tables
        db_request = self.db_cursor.execute("SELECT name FROM sqlite_master")
        db_tables = db_request.fetchall()
        if (not ('packet',) in db_tables):
            logging.debug("Adding packet table to db")
            self.db_cursor.execute("CREATE TABLE packet(packet_name, ec_address, image_memory_slot, tm_packet_id, image_name)")
        if (not ('image',) in db_tables):
            logging.debug("Adding image table to db")
            self.db_cursor.execute("CREATE TABLE image(image_name, ec_address, memory_slot, number_of_packets)")
        db_request = self.db_cursor.execute("SELECT name FROM sqlite_master")
        db_tables = db_request.fetchall()


        
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
        current_time = datetime.now().strftime("%Y/%m/%d, %H:%M:%S")
        status_message = ("### STATUS %s Packets:%d:%d:%d Miss:%d:%d, Images:%d:%d" %
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

        for ec_pair in self.ec_address_position_pairs:
            if (ec_pair[0] == ec_address):
                return ec_pair[1]

        return '?'

        


    def add_packet_to_db(self, packet):
        """ Add packet to database, if not present already """

        packet_data =   [(packet.packet_name,
                        packet.ec_address,
                        packet.image_memory_slot,
                        packet.tm_packet_id,
                        "Unknown"),
                        ]
        self.db_cursor.executemany("INSERT INTO packet VALUES(?, ?, ?, ?, ?)", packet_data)
        self.database.commit()

    def update_packet_image_name_db(self, packet):
        """ Add packet to database, if not present already """

        #TODO




    def add_image_to_db(self, image):
        """ Add image to database, if not present already """

        image_data =    [(image.image_name,
                        image.ec_address,
                        image.memory_slot,
                        image.number_of_packets),
                        ]
        self.db_cursor.executemany("INSERT INTO image VALUES(?, ?, ?, ?)", image_data)
        self.database.commit()



    def start(self):
    
        try:
        
            while self.continue_running:
            
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
                    except Exception as err:
                        logging.error(" Could not connect to socket " + str(err))
                        time.sleep(1)
                        continue
                       
                try:
                    CCSDS_header = self.socket.recv(CCSDSHeadersLength)
                    self.total_packets_received = self.total_packets_received + 1
                    self.timeout_notified = False
                    if (self.interface):
                        self.interface.update_server_active()
                        self.interface.update_stats()
                    
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
                    self.incomplete_images = processor.check_image_timeouts(self.incomplete_images,
                                                                            self.image_timeout,
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
                    self.incomplete_images = processor.check_image_timeouts(self.incomplete_images,
                                                                            self.image_timeout,
                                                                            self.interface)

                except KeyboardInterrupt:
                    raise KeyboardInterrupt

                except Exception as err:
                    logging.error(str(err))
                    self.connected = False
                    self.socket.close()
                    if (self.interface):
                        self.interface.update_server_disconnected()
                    time.sleep(1)
                
        except KeyboardInterrupt:
            logging.info(' # Keyboard interrupt, closing')
            
        finally:
            # Close interface if it is running
            if (self.interface):
                self.interface.close()

            if (self.database):
                self.database.close()
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
        packet =  processor.BIOLAB_Packet(ccsdsTime, currentTime,
                            CCSDS_packet[BIOLAB_ID_position:BIOLAB_ID_position+BIOLAB_packet_length])

        # If packet matches biolab specification add it to list
        if (packet.in_spec()):
            return packet