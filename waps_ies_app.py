#!/usr/bin/env python

# Script: waps_ies_app.py
# Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
# Purpose: WAPS PD image extraction software for operations at MUSC
# Version: 2023-03-10 14:00, version 0.2
#
# Change Log:
#  2023-02-17 version 0.1
#  - initial version, file based
#  - prototype stage
#  2023-03-10 version 0.2
#  - moved from file based packet extraction to TCP stream acquisition
#  - prototype stage

import sys
import configparser
from argparse import ArgumentParser
import os
from datetime import datetime
import logging
import time
from datetime import timedelta
from waps_ies import tcpreceiver, interface

def run_waps_ies(args):
    """
    WAPS Image Extraction Software.
    Acquires CCSDS packets from a TCP stream and searches for BIOLAB TM packets.
    Extracts WAPS PD images from BIOLAB telemetry and informs of missing packets. 
    IP address and port must be specified either inline or in the configuration file.
    
    On start-up process the input parameters in priority:
    1. Command Line Arguments
    2. Configuation file
    3. Defaults

    After start-up IES has the following sequence:
    If GUI is enabled - GUI is started.
    IES attempts to establish a connection to the specified TCP server.
    IP address and port must be specified.
    IES acquires CCSDS packets continuously, automatically assembles images
    and checks for missing packets.

    Command Lines Arguments:
      -h, --help            show this help message and exit
      -ip IP_ADDRESS        IP address of the TCP server. Must be specified either inline or in the configuratiuon file.
      -p PORT               Port of the TCP server. Must be specified either inline or in the configuratiuon file.
      -tt TCP_TIMEOUT, --tcp_timeout TCP_TIMEOUT
                            TCP timeout in seconds. After this period user is notified that not CCSDS packets are
                            received. Default: 2.1
      -o OUTPUT_PATH, --output_path OUTPUT_PATH
                            Output path where extracted images are saved. Default: output/
      -l LOG_PATH, --log_path LOG_PATH
                            Log path where the IES process log is saved. Default: log/
      -er, --errors_only    Show only warnings and errors in the log. Overwritten by debug
      -d, --debug           Debug logging level is enabled
      -dg, --disable_gui    Disable Graphical User Interface
      -it IMAGE_TIMEOUT, --image_timeout IMAGE_TIMEOUT
                            Image timeout in minutes. After this period image is considered OUTDATED. Default: 600
      -msc, --memory_slot_change
                            Enable memory slot change detection from general BIOLAB telemetry


    Configuration file example ("waps_ies_config.ini"):
    [WAPS_IES]
    # TCP server to connect
    ip_address = localhost
    port = 12345
    # TCP timeout, notification of inactivity
    tcp_timeout = 2.1
    # Output path. Images are saved here
    output_path = output/
    # Logging path
    log_path = log/
    # Logging level
    log_level = info
    # Enable Graphical User Interface
    gui_enabled = 1
    # Image timeout in minutes. After this period image is considered OUTDATED.
    image_timeout = 600
    # Enable memory slot change detection from general BIOLAB telemetry
    memory_slot_change_detection = 1
    """

    # Default values
    ip_address = None
    port = None
    tcp_timeout = '2.1'                 # seconds
    output_path = 'output/'
    log_path = 'log/'
    log_level = 'INFO'                  # INFO / DEBUG / WARNING / ERROR
    gui_enabled = '1'                   # Graphical Interface
    image_timeout = '600'               # minutes (10h)
    memory_slot_change_detection = '0'  # False

    # ECs state contains
    # - EC address
    # - EC position
    # - EC column in the GUI
    # - Image transmission is active
    # - Last memory slot used
    ECs_state = []
    
    # Check the configuration file waps_ies_conf.ini
    config = configparser.ConfigParser()
    config.read('waps_ies_config.ini')
    if 'WAPS_IES' in    config.sections(): # [WAPS_IES] section is required
        ip_address =    config.get('WAPS_IES','ip_address', fallback=ip_address)
        port =          config.get('WAPS_IES','port', fallback=port)
        tcp_timeout =   config.get('WAPS_IES','tcp_timeout', fallback=tcp_timeout)
        output_path =   config.get('WAPS_IES','output_path', fallback=output_path)
        log_path =      config.get('WAPS_IES','log_path', fallback=log_path)
        log_level =     config.get('WAPS_IES','log_level', fallback=log_level)
        gui_enabled =   config.get('WAPS_IES','gui_enabled', fallback=gui_enabled)
        image_timeout = config.get('WAPS_IES','image_timeout', fallback=image_timeout)
        memory_slot_change_detection = config.get('WAPS_IES','memory_slot_change_detection',
                                                        fallback=memory_slot_change_detection)
    if ('EC_POSITIONS' in config.sections()):
        for ec_addr_pos in config.items('EC_POSITIONS'):
            ec = {  "ec_address": int(ec_addr_pos[0]),
                    "ec_position": ec_addr_pos[1],
                    "gui_column": None, # Update on receipt of packets
                    "transmission_active": False,
                    "last_memory_slot": None
                }
            ECs_state.append(ec)

    # Define command line arguments
    parser = ArgumentParser(description='WAPS Image Extraction Software.' +
                            ' Acquires CCSDS packets from a TCP stream and searches for BIOLAB TM packets.' +
                            ' Extracts WAPS PD images from BIOLAB telemetry and informs of missing packets.' +
                            ' IP address and port must be specified either inline or in the configuration file.')
    parser.add_argument("-ip", dest="ip_address", default=ip_address,
                        help="IP address of the TCP server. Must be specified either inline or in the configuration file.")
    parser.add_argument("-p", dest="port", default=port,
                        help="Port of the TCP server. Must be specified either inline or in the configuration file. ")
    parser.add_argument("-tt", "--tcp_timeout", dest="tcp_timeout", default=tcp_timeout,
                        help="TCP timeout in seconds. After this period user is notified that not CCSDS packets are received. Default: 2.1")
    parser.add_argument("-o", "--output_path", dest="output_path", default=output_path,
                        help="Output path where extracted images are saved. Default: output/")
    parser.add_argument("-l", "--log_path", dest="log_path", default=log_path,
                        help="Log path where the IES process log is saved. Default: log/")
    parser.add_argument("-er", "--errors_only", action="store_true",
                        help="Show only warnings and errors in the log. Overwritten by debug")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Debug logging level is enabled")
    parser.add_argument("-dg", "--disable_gui", action="store_true",
                        help="Disable Graphical User Interface")
    parser.add_argument("-it", "--image_timeout", dest="image_timeout", default=image_timeout,
                        help="Image timeout in minutes. After this period image is considered OUTDATED. Default: 600")
    parser.add_argument("-msc", "--memory_slot_change", action="store_true",
                        help="Enable memory slot change detection from general BIOLAB telemetry")
    args = parser.parse_args()
    
    # Process command line arguments
    ip_address = args.ip_address
    port = args.port
    tcp_timeout = args.tcp_timeout
    output_path = args.output_path
    log_path = args.log_path
    if (args.debug):
        log_level = 'DEBUG'
    elif (args.errors_only):
        log_level = 'ERROR'
    if (args.disable_gui):
        gui_enabled = '0'
    image_timeout = args.image_timeout
    if (args.memory_slot_change):
        memory_slot_change_detection = '1'



    ##### Check critical parameters
    if (not ip_address):
        logging.error("Server IP address not specified\n" +
            "Please specify IP address and port inline or in the configuration file\n" +
            "Example: waps_ies_app.py -ip localhost -p 12345")
        quit()
    if (not port):
        logging.error("Server port not specified\n" +
            "Please specify IP address and port inline or in the configuration file\n" +
            "Example: waps_ies_app.py -ip localhost -p 12345")
        quit()
    #####



    # Logging level definition
    log_level_printout = 'INFO'
    if (log_level.upper() == 'ERROR'):
        log_level = logging.WARNING
        log_level_printout = 'ERROR'
    elif (log_level.upper() == 'DEBUG'):
        log_level = logging.DEBUG
        log_level_printout = 'DEBUG'
    else:
        log_level = logging.INFO

    # Check existence of the log path
    if (not os.path.exists(log_path)):
        print("Log path does not exist. Making it...")
        os.makedirs(log_path)
    # Check existence of output path
    if (not os.path.exists(output_path)):
        print("Output path does not exist. Making it...")
        os.makedirs(output_path)


    # Initialize the WAPS IES socket
    ies = tcpreceiver.TCP_Receiver(ip_address,
                                    port,
                                    output_path,
                                    tcp_timeout)

    # Start logging to file
    ies.log_path = log_path
    ies.log_level = log_level
    ies.start_new_log()

    # Start-up messages
    logging.info(' ##### WAPS Image Extraction Software #####')
    logging.info(' # Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk')
    logging.info(' # Logging path: ' + log_path)
    logging.info(' # Logging level: ' + log_level_printout)
    logging.info(' # Server: %s:%s', ip_address, port)
    logging.info(' # TCP timeout: %s seconds', tcp_timeout)
    logging.info(' # Output path: '+ output_path)

    ies.image_timeout = timedelta(minutes = int(image_timeout))
    ies.logging_level = log_level
    ies.log_path = log_path
    logging.info(" # Image timeout: " + str(int(image_timeout)) + ' minute(s)')

    if (int(memory_slot_change_detection)):
        ies.memory_slot_change_detection = int(memory_slot_change_detection)
        logging.info(" # Detecting memory slot change from BIOLAB telemetry")

    if (len(ECs_state)):
        ec_addr_pos_printout = "   EC address / position"
        for ec in ECs_state:
            ec_addr_pos_printout = (ec_addr_pos_printout +
                "\n   " + str(ec["ec_address"]) + " / " + ec["ec_position"])

        logging.info(" # Configuration file contained the following EC address/position pairs:\n" +
                        ec_addr_pos_printout)

        ies.ECs_state = ECs_state

    # Configure interface
    if (int(gui_enabled)):
        logging.info(" # Running graphical interface")
        ies_interface = interface.WAPS_interface(ies)
        ies.add_interface(ies_interface)
        interface_startup = datetime.now()
        longer_time_message = False
        while (not ies.interface.window_open):
            print ('#', end = '', flush=True)
            time.sleep(0.1)
            if (datetime.now() - interface_startup > timedelta(seconds = 10) and
                not longer_time_message):
                longer_time_message = True
                logging.info("---Interface taking longer than expected to boot")
        logging.debug(" Interface took " +
                        str(datetime.now() - interface_startup) +
                        ' to start')

    logging.info(" # Starting reception")
    ies.start()

if __name__ == "__main__":
    run_waps_ies(sys.argv)
