#!/usr/bin/env python

# Script: TCPReceiver.py
# Author: Georgi Olentsenko
# Purpose: Receiving CCSDS packets over TCP and filtering BIOLAB packets
# Version: 2023-XX-XX 17:00
#
# Change Log:
#  2023-XX-XX
#  - initial version

import logging
import socket
import time
from struct import unpack
from waps_ies import interface

server_address = ( '192.168.56.101', 23456 )

CCSDS1HeaderLength =  6
CCSDS2HeaderLength = 10
CCSDSHeadersLength = CCSDS1HeaderLength + CCSDS2HeaderLength
CCSDS_packet_timeout_notification = 2.1 # seconds

#class CCSDS_packet:
    
    
class TCP_receiver:
    """
    TCP Receiver class

    Attributes
    ----------

    Methods
    -------

    """
    
    # Initialize socket
    socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Packet expected to be received at least once a second.
    # Allowing more than double the time: 2.1 seconds
    socket.settimeout(CCSDS_packet_timeout_notification)
    connected = False
    
    continue_running = True
    packets_since_boot = 0
    
    interface = None
    
    def __init__(self):
        """
        Initialize the TCP connection

        Attributes
        ----------

        Methods
        -------

        """
        
        self.input_folder = 'input/'
        self.output_folder = 'output/'
        self.log_folder = 'log/'
        self.logging_level = logging.INFO
    
        self.continue_running = True
        self.interface = None
        
        # Debugging parameters
        self.timeout_notified = False
        
    def add_interface(self, ies_interface):
        """ Add an interface object to the trackerer """

        # Check interface type before adding
        if (type(ies_interface) is interface.WAPS_interface):
            logging.debug('Interface added')
            self.interface = ies_interface
        else:
            logging.warning('Interface has wrong object type')
    
    def start(self):
    
        try:
        
            while self.continue_running:
            
                if (not self.connected):
                    try:
                        self.socket.connect(server_address)
                        self.connected = True
                        logging.info("TCP connection to %s:%s established",
                                       server_address[0], str(server_address[1]))
                    except Exception as err:
                        logging.error("Could not connect to socket " + str(err))
                        time.sleep(1)
                       
                try:
                    CCSDS_header = self.socket.recv(CCSDSHeadersLength)
                    self.timeout_notified = False
                    
                    if (len(CCSDS_header) != CCSDSHeadersLength):
                        raise Exception( "Header reception failed" )
                        
                    ccsds1PacketLength = unpack( '>H', CCSDS_header[4:6] )[0]
                    
                    # calculate & receive remaining bytes in packet:
                    packetDataLength = ccsds1PacketLength + 1 - CCSDS2HeaderLength
                    
                    packetData = self.socket.recv( packetDataLength )
                    if( len( packetData ) != packetDataLength ):
                        logging.info("Expected data length of " + str(packetDataLength) +
                                        ' vs actual ' + str(len( packetData )))
                        packetData2 = self.socket.recv( packetDataLength - len( packetData ))
                        if( len( packetData2 ) != packetDataLength - len( packetData ) ):
                            raise Exception( "Failed to read complete CCSDS Data Block from TCP link" )
                        else:
                            logging.info("Got the rest")
                            printCCSDSPacket( CCSDS_header + packetData + packetData2 )
                    else:
                        printCCSDSPacket( CCSDS_header + packetData )
                    
                    self.packets_since_boot = self.packets_since_boot + 1
                    logging.info("CCSDS length: " + str(CCSDSHeadersLength + packetDataLength))
                    logging.info("Total nubmer of packets " + str(self.packets_since_boot))
                
                except TimeoutError:
                    if (not self.timeout_notified):
                        logging.warning("No CCSDS packets received for more than " +
                                        str(CCSDS_packet_timeout_notification) +
                                        " seconds")
                        self.timeout_notified = True
                
        except KeyboardInterrupt:
            logging.info(' Keyboard interrupt, closing')

        except Exception as err:
            logging.error(" Error during execution: " + str(err))
            
        finally:
            if (self.interface):
                self.interface.close()
                
            self.socket.close()
            logging.info(" Closed socket")
        
        
def printCCSDSPacket( CCSDS_Packet ):
    if( len( CCSDS_Packet ) < CCSDSHeadersLength ):
        return

    # sys.stderr.write( "CCSDS_Header is %s\n" % ( CCSDS_Header.encode( 'hex' ) ) )

    # extract data from assembled packet:

    # CCSDS primary header:
    word1 = unpack( '>H', CCSDS_Packet[0:2] )[0]
    ccsds1VersionNumber  = ( word1 >> 13 ) & 0x0007 # bits 0-2
    ccsds1Type           = ( word1 >> 12 ) & 0x0001 # bit 3
    ccsds1SecondaryHdr   = ( word1 >> 11 ) & 0x0001 # bit 4
    ccsds1APID           = ( word1 >>  0 ) & 0x03ff # bits 5-15
    word2 = unpack( '>H', CCSDS_Packet[2:4] )[0]
    ccsds1SeqFlags       = ( word2 >> 14 ) & 0x0003 # bits 0-1
    ccsds1SeqCounter     = ( word2 >>  0 ) & 0x3fff # bits 2-15
    ccsds1PacketLength = unpack( '>H', CCSDS_Packet[4:6] )[0]

    # CCSDS secondary header:
    ccsds2CoarseTime = unpack( '>L', CCSDS_Packet[6:10] )[0]
    word3 = unpack( '>H', CCSDS_Packet[10:12] )[0]
    ccsds2FineTime = ( ( word3 >> 8 ) & 0x00ff ) * 1000 / 256 # calculate into milliseconds from bits 0-7
    ccsds2TimeID     = ( word3 >> 6 ) & 0x0003   # bits 8-9
    ccsds2CW         = ( word3 >> 5 ) & 0x0001   # bit 10
    ccsds2ZOE        = ( word3 >> 4 ) & 0x0001   # bit 11
    ccsds2PacketType = ( word3 >> 0 ) & 0x000f   # bits 12-15

    ccsds2PacketID32 = unpack( '>L', CCSDS_Packet[12:16] )[0]
    ccsds2Spare         = ( ccsds2PacketID32 >> 31 ) & 0x00000000
    ccsds2ElementID     = ( ccsds2PacketID32 >> 27 ) & 0x0000000f
    ccsds2PacketID27    = ( ccsds2PacketID32 >>  0 ) & 0x07ffffff

    logging.info( "success: read a CCSDS packet of %d bytes in full\n" % len( CCSDS_Packet ) )
    logging.info( "  CCSDS primary header:\n")
    logging.info( "         version number: %d\n" % ccsds1VersionNumber )
    strType = "system"
    if( ccsds1Type == 1 ): strType = "payload"
    logging.info( "         type: %s\n" % strType )
    logging.info( "         secondary header present: %r\n" % ( bool( ccsds1SecondaryHdr ) ) )
    logging.info( "         APID: %d\n" % ccsds1APID )
    strSequenceFlags = "b" + str( int ( ccsds1SeqFlags > 1 ) ) + str( int( ccsds1SeqFlags & 0x1 ) )
    logging.info( "         sequence flags: %s\n" % strSequenceFlags )
    logging.info( "         sequence count: %d\n" % ccsds1SeqCounter )
    logging.info( "         packet length: %d\n" % ccsds1PacketLength )
    logging.info( "  CCSDS secondary header:\n")
    logging.info( "         coarse time: %d\n" % ccsds2CoarseTime )
    logging.info( "         fine time: %d\n" % ccsds2FineTime )
    strTimeID = "b" + str( int ( ccsds2TimeID > 1 ) ) + str( int( ccsds2TimeID & 0x1 ) )
    logging.info( "         time ID: %s\n" % strTimeID )
    logging.info( "         checkword present: %r\n" % ( bool( ccsds2CW ) ) )
    logging.info( "         ZOE: %r\n" % ( bool( ccsds2ZOE ) ) )
    logging.info( "         packetType: %d\n" % ( ccsds2PacketType ) )
    logging.info( "         spare: %d\n" % ( int( ccsds2Spare ) ) )
    strElementID = "not mapped"
    if( ccsds2ElementID == 2 ): strElementID = "Columbus"
    logging.info( "         element ID: %d (%s)\n" % ( int( ccsds2ElementID ), strElementID ) )
    logging.info( "         packet ID 27: %d\n" % ( ccsds2PacketID27 ) )