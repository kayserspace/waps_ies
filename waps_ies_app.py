#!/usr/bin/env python

"""
Script: waps_ies_app.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: WAPS PD image extraction software for operations at MUSC
Version: 2023-03-10 14:00, version 0.2

Change Log:
2023-02-17 version 0.1
 - initial version, file based
 - prototype stage
 2023-03-10 version 0.2
 - moved from file based packet extraction to TCP stream acquisition
 - prototype stage
"""

import sys
import configparser
from argparse import ArgumentParser
import os
from datetime import datetime, timedelta
import time
import logging
import waps_ies.receiver


def check_config_file():
    """
    Get WAPS IES configuration from file.

    Configuration file example ("waps_ies_config.ini"):
    [WAPS_IES]
    # TCP server to connect
    ip_address = localhost
    port = 12345
    # TCP timeout, notification of inactivity
    tcp_timeout = 2.1
    # Output path. Images are saved here
    output_path = output/
    # Command stack path
    comm_path = comm/
    # Logging path
    log_path = log/
    # Logging level
    log_level = info
    # Enable Graphical User gui
    gui_enabled = 1
    # Image timeout in minutes. After this period image is considered OUTDATED.
    # 0 means disable this feature
    image_timeout = 600
    # Enable memory slot change detection from general BIOLAB telemetry
    memory_slot_change_detection = 1
    # Skip checking colour image CRC
    skip_crc = 0
    """

    # Default WAPS IES configuration
    waps = {"ip_address": None,
            "port": None,
            "tcp_timeout": '2.1',     # seconds
            "output_path": 'output/', # directory
            "comm_path": 'comm/',     # directory
            "log_path": 'log/',       # directory
            "log_level": 'INFO',      # INFO / DEBUG / WARNING / ERROR
            "gui_enabled": '1',       # Graphical User Interface
            "image_timeout": '600',   # minutes (10h by default)
            "detect_mem_slot": '1',   # False
            "skip_crc": '0'}          # Check clour image CRC

    # EC list contains
    # - EC address
    # - EC position
    # - EC column in the GUI
    # - Image transmission is active
    # - Last memory slot used
    ec_list = []

    # Check the configuration file waps_ies_conf.ini
    config = configparser.ConfigParser()
    config.read('waps_ies_config.ini')
    if 'WAPS_IES' in config.sections():  # [WAPS_IES] section is required
        waps["ip_address"] = config.get('WAPS_IES', 'ip_address',
                                        fallback=waps["ip_address"])
        waps["port"] = config.get('WAPS_IES', 'port',
                                  fallback=waps["port"])
        waps["tcp_timeout"] = config.get('WAPS_IES', 'tcp_timeout',
                                         fallback=waps["tcp_timeout"])
        waps["output_path"] = config.get('WAPS_IES', 'output_path',
                                         fallback=waps["output_path"])
        waps["comm_path"] = config.get('WAPS_IES', 'comm_path',
                                       fallback=waps["comm_path"])
        waps["log_path"] = config.get('WAPS_IES', 'log_path',
                                      fallback=waps["log_path"])
        waps["log_level"] = config.get('WAPS_IES', 'log_level',
                                       fallback=waps["log_level"])
        waps["gui_enabled"] = config.get('WAPS_IES', 'gui_enabled',
                                         fallback=waps["gui_enabled"])
        waps["image_timeout"] = config.get('WAPS_IES', 'image_timeout',
                                           fallback=waps["image_timeout"])
        waps["detect_mem_slot"] = config.get('WAPS_IES', 'memory_slot_change_detection',
                                             fallback=waps["detect_mem_slot"])
        waps["skip_crc"] = config.get('WAPS_IES', 'skip_crc',
                                      fallback=waps["skip_crc"])
    if 'EC_POSITIONS' in config.sections():
        for ec_addr_pos in config.items('EC_POSITIONS'):
            ec_list.append({"ec_address": int(ec_addr_pos[0]),
                            "ec_position": ec_addr_pos[1],
                            "gui_column": None,
                            "transmission_active": False,
                            "last_memory_slot": None})

    return waps, ec_list


def check_arguments(args, config):
    """
    Check command line arguments for WAPS IES configuration.

    Command Lines Arguments:
      -h, --help            show this help message and exit
      -ip IP_ADDRESS        IP address of the TCP server.
                            Must be specified either inline or
                            in the configuratiuon file.
      -p PORT               Port of the TCP server.
                            Must be specified either inline or
                            in the configuratiuon file.
      -tt TCP_TIMEOUT, --tcp_timeout TCP_TIMEOUT
                            TCP timeout in seconds.
                            After this period user is notified that
                            CCSDS packets are not being received. Default: 2.1
      -o OUTPUT_PATH, --output_path OUTPUT_PATH
                            Output path where extracted images are saved.
                            Default: output/
      -l LOG_PATH, --log_path LOG_PATH
                            Log path where the IES process log is saved.
                            Default: log/
      -er, --errors_only    Show only warnings and errors in the log.
                            Overwritten by debug
      -d, --debug           Debug logging level is enabled
      -dg, --disable_gui    Disable Graphical User Interface (gui)
      -it IMAGE_TIMEOUT, --image_timeout IMAGE_TIMEOUT
                            Image timeout in minutes.
                            After this period image is considered OUTDATED.
                            Default: 600
      -msc, --memory_slot_change
                            Enable memory slot change detection from
                            general BIOLAB telemetry
    """

    # Define command line arguments
    parser = ArgumentParser(description='WAPS Image Extraction Software.' +
                            ' Acquires CCSDS packets from a TCP stream' +
                            ' and searches for BIOLAB TM packets.' +
                            ' Extracts WAPS PD images from BIOLAB' +
                            ' telemetry and informs of missing packets.' +
                            ' IP address and port must be specified' +
                            ' either inline or in the configuration file.')
    parser.add_argument("-ip", dest="ip_address", default=config["ip_address"],
                        help="IP address of the TCP server." +
                        " Must be specified either inline or" +
                        " in the configuration file.")
    parser.add_argument("-p", dest="port", default=config["port"],
                        help="Port of the TCP server." +
                        " Must be specified either inline or" +
                        " in the configuration file. ")
    parser.add_argument("-tt", "--tcp_timeout", dest="tcp_timeout",
                        default=config["tcp_timeout"],
                        help="TCP timeout in seconds. After this period" +
                        " user is notified that CCSDS packets" +
                        " are not being received. Default: 2.1")
    parser.add_argument("-o", "--output_path", dest="output_path",
                        default=config["output_path"],
                        help="Output path where extracted images are saved." +
                        " Default: output/")
    parser.add_argument("-c", "--comm_path", dest="comm_path",
                        default=config["comm_path"],
                        help="Command stack path where missing packet lists are created." +
                        " Default: comm/")
    parser.add_argument("-l", "--log_path", dest="log_path",
                        default=config["log_path"],
                        help="Log path where the IES process log is saved." +
                        " Default: log/")
    parser.add_argument("-er", "--errors_only", action="store_true",
                        help="Show only warnings and errors in the log." +
                        " Overwritten by debug")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Debug logging level is enabled")
    parser.add_argument("-dg", "--disable_gui", action="store_true",
                        help="Disable Graphical User Interface (gui)")
    parser.add_argument("-it", "--image_timeout", dest="image_timeout",
                        default=config["image_timeout"],
                        help="Image timeout in minutes. After this period" +
                        " image is considered OUTDATED. Default: 600")
    parser.add_argument("-msc", "--memory_slot_change", action="store_true",
                        help="Enable memory slot change detection from" +
                        " general BIOLAB telemetry")
    args = parser.parse_args()

    # Process command line arguments
    config["ip_address"] = args.ip_address
    config["port"] = args.port
    config["tcp_timeout"] = args.tcp_timeout
    config["output_path"] = args.output_path
    config["comm_path"] = args.comm_path
    config["log_path"] = args.log_path
    if args.debug:
        config["log_level"] = 'DEBUG'
    elif args.errors_only:
        config["log_level"] = 'ERROR'
    if args.disable_gui:
        config["gui_enabled"] = '0'
    config["image_timeout"] = args.image_timeout
    if args.memory_slot_change:
        config["detect_mem_slot"] = '1'

    return config


def run_waps_ies(args):
    """
    WAPS Image Extraction Software (IES)
    Acquires CCSDS packets from a TCP stream and searches for TM packets.
    Extracts WAPS PD images from BIOLAB telemetry and
        declares and highlights missing packets.
    IP address and port must be specified either inline or
        in the configuration file.

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
    """

    # Config file
    waps_config, ec_list = check_config_file()
    # Command line arguments
    waps_config = check_arguments(args, waps_config)

    # Check critical parameters
    if not waps_config["ip_address"] or not waps_config["port"]:
        logging.error("%s%s%s%s", "Server IP address or port not specified\n",
                      "Please specify IP address and port",
                      " inline or in the configuration file\n",
                      "Example: waps_ies_app.py -ip localhost -p 12345")
        sys.exit()

    # Logging level definition
    log_level_printout = 'INFO'
    if waps_config["log_level"].upper() == 'ERROR':
        waps_config["log_level"] = logging.WARNING
        log_level_printout = 'ERROR'
    elif waps_config["log_level"].upper() == 'DEBUG':
        waps_config["log_level"] = logging.DEBUG
        log_level_printout = 'DEBUG'
    else:
        waps_config["log_level"] = logging.INFO

    # Check existence of the log path
    if not os.path.exists(waps_config["log_path"]):
        print("Log path does not exist. Creating it...\n...")
        os.makedirs(waps_config["log_path"])

    # Check existence of output path
    if not os.path.exists(waps_config["output_path"]):
        print("Output path does not exist. Creating it...\n...")
        os.makedirs(waps_config["output_path"])

    # Check existence of output path
    if not os.path.exists(waps_config["comm_path"]):
        print("Command stack path does not exist. Creating it...\n...")
        os.makedirs(waps_config["comm_path"])

    # Initialize the WAPS IES socket
    ies = waps_ies.receiver.Receiver(waps_config["ip_address"],
                                     waps_config["port"],
                                     waps_config["output_path"],
                                     waps_config["tcp_timeout"])

    # Add command stack path
    ies.comm_path = waps_config["comm_path"]

    # Start logging to file
    ies.log_path = waps_config["log_path"]
    ies.log_level = waps_config["log_level"]
    ies.start_new_log()

    # Start-up messages
    logging.info(' ##### WAPS Image Extraction Software #####')
    logging.info(' # Logging path: %s', waps_config["log_path"])
    logging.info(' # Logging level: %s', log_level_printout)
    logging.info(' # Server: %s:%s',
                 waps_config["ip_address"],
                 waps_config["port"])
    logging.info(' # TCP timeout: %s seconds', waps_config["tcp_timeout"])
    logging.info(' # Output path: %s', waps_config["output_path"])
    logging.info(' # Command stack path: %s', waps_config["comm_path"])

    ies.image_timeout = timedelta(minutes=int(waps_config["image_timeout"]))
    ies.skip_crc = waps_config["skip_crc"] == '1'
    logging.info(' # Image timeout: %i minute(s)',
                 int(waps_config["image_timeout"]))

    if int(waps_config["detect_mem_slot"]):
        ies.memory_slot_change_detection = int(waps_config["detect_mem_slot"])
        logging.info(" # Detecting memory slot change from BIOLAB telemetry")

    if len(ec_list) > 0:
        ec_addr_pos_printout = "   EC address / position"
        for ec_state in ec_list:
            ec_addr_pos_printout = (ec_addr_pos_printout +
                                    "\n   " + str(ec_state["ec_address"]) +
                                    " / " + ec_state["ec_position"])

        logging.info(" # Config contains EC address/position pairs:\n%s",
                     ec_addr_pos_printout)

        ies.ec_states = ec_list

    # Configure gui
    if int(waps_config["gui_enabled"]):
        logging.info(" # Running graphical gui")
        ies_gui = waps_ies.interface.WapsIesGui(ies)
        ies.add_gui(ies_gui)
        gui_startup = datetime.now()
        longer_time_message = False
        while not ies.gui.window_open:
            print('#', end='', flush=True)
            time.sleep(0.1)
            if (datetime.now() - gui_startup > timedelta(seconds=10) and
                    not longer_time_message):
                longer_time_message = True
                logging.info("--- GUI taking longer than expected to boot")
            if datetime.now() - gui_startup > timedelta(seconds=60):
                longer_time_message = True
                logging.error("---Something precents GUI from starting")
                break
        logging.debug(' gui took %s to start',
                      str(datetime.now() - gui_startup))

    logging.info(" # Starting reception")
    ies.start()


if __name__ == "__main__":
    run_waps_ies(sys.argv)
