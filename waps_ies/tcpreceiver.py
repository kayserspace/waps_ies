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

CCSDS1HeaderLength =  6
CCSDS2HeaderLength = 10
CCSDSHeadersLength = CCSDS1HeaderLength + CCSDS2HeaderLength
CCSDS_packet_timeout_notification = 2.1 # seconds

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
    
    def __init__(self, address, port, output_path, log_path, log_level):
        """
        Initialize the TCP connection

        Attributes
        ----------

        Methods
        -------

        """

        self.socket = None
        self.server_address = ( address, int(port) )
        self.connected = False
        
        self.output_path = output_path
        self.log_path = log_path
        self.log_level = log_level

        self.incomplete_images = []
    
        self.continue_running = True
        self.interface = None

        # TODO implement
        self.image_timeout = timedelta(minutes = 60)

        self.memory_slot_change_detection = False

        # Set up logging
        log_filename = (self.log_path + 'WAPS_IES_' +
                            datetime.now().strftime('%Y%m%d_%H%M%S') + '.log')
        logging.basicConfig(filename = log_filename,
                            format='%(asctime)s:%(levelname)s:%(message)s',
                            level=self.log_level)
        logging.getLogger().addHandler(logging.StreamHandler())

        # Start-up messages
        logging.info(' ##### WAPS Image Extraction Software #####')
        logging.info(' # Author: Georgi Olentsenko')
        logging.info(' # Started log file: ' + log_filename)
        logging.info(' # Path to extracted images: '+ self.output_path)

        # Status parameters
        self.timeout_notified = False

        self.total_packets_received = 0
        self.total_biolab_packets = 0
        self.total_waps_image_packets = 0
        self.total_initialized_images = 0
        self.total_completed_images = 0
        self.total_lost_packets = 0
        self.total_corrupted_packets = 0

        
    def add_interface(self, ies_interface):
        """ Add an interface object to the trackerer """

        # Check interface type before adding
        if (type(ies_interface) is interface.WAPS_interface):
            logging.debug(' # Interface added')
            self.interface = ies_interface
        else:
            logging.warning(' Interface has wrong object type')
    
    def start(self):
    
        try:
        
            while self.continue_running:
            
                if (not self.connected):
                    try:
                        # Initialize socket
                        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        # Packet expected to be received at least once a second.
                        # Allowing more than double the time: 2.1 seconds
                        self.socket.settimeout(CCSDS_packet_timeout_notification)
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
                        logging.info("Expected data length of " + str(packetDataLength) +
                                        ' vs actual ' + str(len( packetData )))
                        packetData2 = self.socket.recv( packetDataLength - len( packetData ))
                        if( len( packetData2 ) != packetDataLength - len( packetData ) ):
                            raise Exception( "Failed to read complete CCSDS Data Block from TCP link" )
                        else:
                            logging.info("Got the rest")
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
                
                except TimeoutError:
                    if (not self.timeout_notified):
                        logging.warning("No CCSDS packets received for more than " +
                                        str(CCSDS_packet_timeout_notification) +
                                        " seconds")
                        self.timeout_notified = True
                        if (self.interface):
                            self.interface.update_server_connected()

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
                
            self.socket.close()
            logging.info(" # Disconnected from server")
            logging.info(" Total nubmer of packets received: %d", self.total_packets_received)
            logging.info(" BIOLAB packets processed:         %d", self.total_biolab_packets)
        

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
            logging.error(" CCSDS packet is too short: %d bytes", CCSDS_packet_length)
            return

        # TODO more checks on teh CCSDS packet

        # Check packet length and BIOLAB ID
        if (CCSDS_packet_length < 287 or CCSDS_packet[BIOLAB_ID_position] != 0x40):
            logging.debug(" Not a BIOLAB packet")
            return

        BIOLAB_packet_length = CCSDS_packet[BIOLAB_ID_position + 1] * 2 + 4
        if (BIOLAB_packet_length < 254):
            logging.warning(" Unexpected BIOLAB packet length: %d", BIOLAB_packet_length)
        
        # Count BIOLAB packets
        self.total_biolab_packets = self.total_biolab_packets + 1
        if (self.interface):
            self.interface.update_stats()

        


        # extract data from assembled packet:

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
        ccsds2TimeID     = ( word3 >> 6 ) & 0x0003   # bits 8-9
        ccsds2CW         = ( word3 >> 5 ) & 0x0001   # bit 10
        ccsds2ZOE        = ( word3 >> 4 ) & 0x0001   # bit 11
        ccsds2PacketType = ( word3 >> 0 ) & 0x000f   # bits 12-15

        ccsds2PacketID32 = unpack( '>L', CCSDS_packet[12:16] )[0]
        ccsds2Spare         = ( ccsds2PacketID32 >> 31 ) & 0x00000000
        ccsds2ElementID     = ( ccsds2PacketID32 >> 27 ) & 0x0000000f
        ccsds2PacketID27    = ( ccsds2PacketID32 >>  0 ) & 0x07ffffff

        logging.debug( "success: read a CCSDS packet of %d bytes in full" % len( CCSDS_packet ) )
        strType = "system"
        if( ccsds1Type == 1 ): strType = "payload"
        logging.debug( "         type: %s" % strType )
        logging.debug( "         secondary header present: %r" % ( bool( ccsds1SecondaryHdr ) ) )
        logging.debug( "         APID: %d" % ccsds1APID )
        strSequenceFlags = "b" + str( int ( ccsds1SeqFlags > 1 ) ) + str( int( ccsds1SeqFlags & 0x1 ) )
        logging.debug( "         packet length: %d" % ccsds1PacketLength )
        logging.debug( "  CCSDS secondary header:")
        logging.debug( "         coarse time: %d" % ccsds2CoarseTime )
        logging.debug( "         fine time: %d" % ccsds2FineTime )
        strTimeID = "b" + str( int ( ccsds2TimeID > 1 ) ) + str( int( ccsds2TimeID & 0x1 ) )
        logging.debug( "         time ID: %s" % strTimeID )
        logging.debug( "         checkword present: %r" % ( bool( ccsds2CW ) ) )
        logging.debug( "         ZOE: %r" % ( bool( ccsds2ZOE ) ) )
        logging.debug( "         packetType: %d" % ( ccsds2PacketType ) )
        logging.debug( "         spare: %d" % ( int( ccsds2Spare ) ) )
        strElementID = "not mapped"
        if( ccsds2ElementID == 2 ): strElementID = "Columbus"
        logging.debug( "         element ID: %d (%s)" % ( int( ccsds2ElementID ), strElementID ) )
        logging.debug( "         packet ID 27: %d" % ( ccsds2PacketID27 ) )

        # TODO proper timestamps
        # Create BIOLAB packet as is
        packet =  processor.BIOLAB_Packet("None", datetime.now(),
                            datetime.now(),
                            CCSDS_packet[BIOLAB_ID_position:BIOLAB_ID_position+BIOLAB_packet_length])

        # If packet matches biolab specification add it to list
        if (packet.in_spec()):
            return packet