#!/usr/bin/env python

"""
Script: waps_ies_app.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: WAPS Image Extraction Software for WAPS Payload to be used for operations at MUSC
         This file contains the IES configuration and initialization
Version: 2023-09-27, version 1.1

WAPS Image Extraction Software. Acquires CCSDS packets from a TCP stream and searches for BIOLAB TM
packets. Extracts WAPS PD images from BIOLAB telemetry and informs of missing packets. IP address
and port must be specified either inline or in the configuration file.

This file contains methods:
 * check_config_file()
        Get WAPS IES configuration from file
 * check_arguments(args, config)
        Get WAPS IES configuration from command line arguments
 * run_waps_ies(args)
        Start WAPS IES execution

Change Log:
2023-02-17 version 0.1
 - initial version, file based
 - prototype stage
 2023-03-10 version 0.2
 - moved from file based packet extraction to TCP stream acquisition
 - prototype stage
 2023-05-31 version 1.0
 - First release
2023-09-27 version 1.1
 - Added command delay parameter to the configurtion file
"""

import sys
import configparser
from argparse import ArgumentParser
import logging
import waps_ies.receiver


def check_config_file():
    """Get WAPS IES configuration from file

    No args

    Returns as tuple:
        waps(dictionaty):   IES configuration
        ec_list(list):      List of EC states

    Configuration file example ("waps_ies_config.ini"):
    [WAPS_IES]
    # TCP server to connect
    ip_address = localhost
    port = 12345
    # TCP timeout, notification of inactivity
    tcp_timeout = 2.1
    # Output path. Images are saved here
    output_path = output/
    # Database file to use
    database_file = waps_pd.db
    # Command stack path
    comm_path = comms/
    # Logging path
    log_path = logs/
    # Logging level
    log_level = info
    # Enable Graphical User Interface
    gui_enabled = 1
    # Yamcs command stack delay between missing packet commands
    command_delay = 2500
    # Image timeout in minutes. After this period image is considered OUTDATED.
    # 0 means disable this feature
    image_timeout = 600
    # Enable memory slot change detection from general BIOLAB telemetry
    memory_slot_change_detection = 1
    # Skip checking verify code of the colour image
    skip_verify_code = 0
    """

    # Default WAPS IES configuration
    waps = {"ip_address": None,             # no IP address
            "port": None,                   # no port
            "tcp_timeout": '2.1',           # TCP timeout in seconds
            "output_path": 'output/',       # Output directory
            "database_file": 'waps_pd.db',  # Database file path
            "silent_db_creation": '0',      # Prompt before creating a new database
            "comm_path": 'comms/',          # Command stack directory
            "log_path": 'logs/',            # Logging directory
            "log_level": 'INFO',            # INFO / DEBUG / WARNING / ERROR
            "gui_enabled": '1',             # Graphical User Interface enabled
            "command_delay": '2500',        # Yamcs command stack delay between missing packet commands
            "image_timeout": '600',         # minutes (10h by default)
            "detect_mem_slot": '1',         # Check BIOLAB header and track EC memory slot change
            "skip_verify_code": '0',        # Check colour image verification code
            "ies_instance_name": ' ',       # IES instance name in the GUI title
            "version": "v1.1  2023-09-27"}  # WAPS IES version

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
        waps["database_file"] = config.get('WAPS_IES', 'database_file',
                                           fallback=waps["database_file"])
        waps["silent_db_creation"] = config.get('WAPS_IES', 'silent_db_creation',
                                                fallback=waps["silent_db_creation"])
        waps["comm_path"] = config.get('WAPS_IES', 'comm_path',
                                       fallback=waps["comm_path"])
        waps["log_path"] = config.get('WAPS_IES', 'log_path',
                                      fallback=waps["log_path"])
        waps["log_level"] = config.get('WAPS_IES', 'log_level',
                                       fallback=waps["log_level"])
        waps["gui_enabled"] = config.get('WAPS_IES', 'gui_enabled',
                                         fallback=waps["gui_enabled"])
        waps["command_delay"] = config.get('WAPS_IES', 'command_delay',
                                           fallback=waps["command_delay"])
        waps["image_timeout"] = config.get('WAPS_IES', 'image_timeout',
                                           fallback=waps["image_timeout"])
        waps["detect_mem_slot"] = config.get('WAPS_IES', 'memory_slot_change_detection',
                                             fallback=waps["detect_mem_slot"])
        waps["skip_verify_code"] = config.get('WAPS_IES', 'skip_verify_code',
                                              fallback=waps["skip_verify_code"])
        waps["ies_instance_name"] = config.get('WAPS_IES', 'ies_instance_name',
                                               fallback=waps["ies_instance_name"])
    if 'EC_POSITIONS' in config.sections():
        for ec_addr_pos in config.items('EC_POSITIONS'):
            ec_list.append({"ec_address": int(ec_addr_pos[0]),
                            "ec_position": ec_addr_pos[1],
                            "gui_column": None,
                            "transmission_active": False,
                            "last_memory_slot": None})

    return waps, ec_list


def check_arguments(args, config):
    """Get WAPS IES configuration from command line arguments

    Args:
        *args:              Command line parameters, described below
        config(dictionary): IES configuration

    Returns:
        config(dictionaty): IES configuration

    Command Lines Arguments:
      -h, --help            show this help message and exit
      -ip IP_ADDRESS        IP address of the TCP server.
                            Must be specified either inline or in the configuratiuon file.
                            Otherwise throws error.
      -p PORT               Port of the TCP server.
                            Must be specified either inline or
                            in the configuratiuon file.
      -tt TCP_TIMEOUT, --tcp_timeout TCP_TIMEOUT
                            TCP timeout in seconds.
                            After this period user is notified that
                            CCSDS packets are not being received. Default: 2.1
      -o OUTPUT_PATH, --output_path OUTPUT_PATH
                            Output path where extracted images are saved. Default: output/
      -db DATABASE_FILE, --database_file DATABASE_FILE
                            Databse file to use. Default: output/
      -c COMM_PATH, --comm_path COMM_PATH
                            Command stack path where missing packet lists are created. Default: comms/
      -l LOG_PATH, --log_path LOG_PATH
                            Log path where the IES process log is saved. Default: logs/
      -er, --errors_only    Show only warnings and errors in the log.
                            Overwritten by debug
      -d, --debug           Debug logging level is enabled
      -dg, --disable_gui    Disable Graphical User Interface (gui)
      -it IMAGE_TIMEOUT, --image_timeout IMAGE_TIMEOUT
                            Image timeout in minutes. After this period image is considered OUTDATED.
                            Default: 600
      -msc, --memory_slot_change
                            Enable memory slot change detection from
                            general BIOLAB telemetry
    """

    # Define command line arguments
    parser = ArgumentParser(description='WAPS Image Extraction Software v' + str(config["version"]) +
                            '. Acquires CCSDS packets from a TCP stream' +
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
    parser.add_argument("-db", "--database_file", dest="database_file",
                        default=config["database_file"],
                        help="Databse file to use. Default: output/")
    parser.add_argument("-c", "--comm_path", dest="comm_path",
                        default=config["comm_path"],
                        help="Command stack path where missing packet lists are created." +
                        " Default: comms/")
    parser.add_argument("-l", "--log_path", dest="log_path",
                        default=config["log_path"],
                        help="Log path where the IES process log is saved." +
                        " Default: logs/")
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
    config["database_file"] = args.database_file
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
    WAPS Image Extraction Software. Acquires CCSDS packets from a TCP stream and
    searches for BIOLAB TM packets. Extracts WAPS PD images from BIOLAB telemetry and
    informs of missing packets. IP address and port must be specified either inline or
    in the configuration file.

    On start-up process the input parameters in priority:
    1. Command Line Arguments
    2. Configuation file
    3. Defaults (except ip address and port)

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

    # Initialize the WAPS IES
    ies = waps_ies.receiver.Receiver(waps_config)

    if len(ec_list) > 0:
        ec_addr_pos_printout = "   EC addr / pos"
        for ec_state in ec_list:
            ec_addr_pos_printout = (ec_addr_pos_printout +
                                    "\n       " + str(ec_state["ec_address"]) +
                                    " / " + ec_state["ec_position"])

        logging.info(" # Config contains EC address/position pairs:\n%s",
                     ec_addr_pos_printout)

        ies.ec_states = ec_list

    logging.info(" # Starting reception")
    ies.start()


if __name__ == "__main__":
    run_waps_ies(sys.argv)
