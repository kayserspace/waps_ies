#!/usr/bin/env python

# Script: readCCSDSFromTCP.py
# Author: Georgi Olentsenko
# Purpose: WAPS PD image extraction for operations at MUSC
# Version: 2023-xx-xx xx:xx
#
# Change Log:
#  2023-xx-xx
#  - initial version

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
    WAPS Image Extractor Software.
    Searches telemetry archive files as binary files for BIOLAB packets and assembles them into images.
    GUI is optional. Options to scan a path for packets once or monitor the path continuously.
    
    On start-up process the input parameters in priority:
    1. Command Line Arguments
    2. Configuation file
    3. Defaults

    After start-up following sequence:
    If GUI is enabled - GUI is started.
    If Scan is enabled - IES processes all files in the correct format into packets and assembled them into images.
    If Tracker is enabled - IES continued to monitor the input folder for new telemetry artchives and processing them into packets and images.
    Additionally a separate telemetry archive can be added manually for processing in the GUI.


    Command Lines Arguments:
      -h, --help            show this help message and exit
      -i INPUT_PATH, --input_path INPUT_PATH
                            Input path to be monitored for TM archives. Must exist. Default: input/
      -o OUTPUT_PATH, --output_path OUTPUT_PATH
                            Output path where extracted images are saved. Must exist. Default: output/
      -lp LOG_PATH, --log_path LOG_PATH
                            Log path where the extraction process log is saved. Must exist. Default: log/
      -er, --errors_only    Show only warnings and errors in the log. Overwritten by debug
      -d, --debug           Debug logging is enabled
      -dg, --disable_gui    Disable Graphical interface
      -ns, --no_scan        Disable the scan of existing files in the input path
      -nt, --no_tracker     Disable the file tracker in the input path
      -f FILE_FORMAT, --file_format FILE_FORMAT
                            Telemetry archive file pattern. Example: '*.dat' Default: '*' as all files. For multiple formats
                            edit the configuration file instead
      -t IMAGE_TIMEOUT, --image_timeout IMAGE_TIMEOUT
                            Image timeout in minutes. After this period image is considered OUTDATED. Default: 60
      -msc, --mem_slot_change
                            Enable memory slot change detection from general BIOLAB telemetry


    Configuration file example ("waps_ies_config.ini"):
    [WAPS_IES]
    input_path = input/
    output_path = output/
    log_path = log/
    # Logging level
    log_level = info
    # User Graphical interface
    gui_enabled = 1
    # Run the initial scan of the folder
    run_scan = 1
    # Run file tracker to get packets from new files
    run_tracker = 1
    # File format pattern to proccess
    file_format = *
    # Image timeout in minutes. After these minutes image is considred outdated and no more packets are added to it.
    image_timeout = 60
    # Detect from general BIOLAB telemetry whether image memory slot is updated
    current_slot_detection = 0


    # Default values
    input_path = 'input/'
    output_path = 'output/'
    log_path = 'log/'
    log_level = 'INFO'          # INFO / DEBUG / WARNING / ERROR
    gui_enabled = '1'           # Graphical Interface
    run_scan = '1'              # Scan existing files for packets
    run_tracker = '1'           # Run file tracker and processor
    file_format = '*'           # all file formats
    image_timeout = '60'        # minutes
    memory_slot_change_detection = '0'# False
    """

    # Default values
    input_path = 'input/'
    output_path = 'output/'
    log_path = 'log/'
    log_level = 'INFO'          # INFO / DEBUG / WARNING / ERROR
    gui_enabled = '1'           # Graphical Interface
    run_scan = '1'              # Scan existing files for packets
    run_tracker = '1'           # Run file tracker and processor
    file_format = '*'           # all file formats
    image_timeout = '60'        # minutes
    memory_slot_change_detection = '0'# False
    
    
    # Check the configuration file waps_ies_conf.ini
    config = configparser.ConfigParser()
    config.read('waps_ies_config.ini')
    if 'WAPS_IES' in config.sections(): # [WAPS_IES] section is required
        input_path = config.get('WAPS_IES','input_path', fallback=input_path)
        output_path = config.get('WAPS_IES','output_path', fallback=output_path)
        log_path = config.get('WAPS_IES','log_path', fallback=log_path)
        log_level = config.get('WAPS_IES','log_level', fallback=log_level)
        gui_enabled = config.get('WAPS_IES','gui_enabled', fallback=gui_enabled)
        run_scan = config.get('WAPS_IES','run_scan', fallback=run_scan)
        run_tracker = config.get('WAPS_IES','run_tracker', fallback=run_tracker)
        file_format = config.get('WAPS_IES','file_format', fallback=file_format)
        image_timeout = config.get('WAPS_IES','image_timeout', fallback=image_timeout)
        memory_slot_change_detection = config.get('WAPS_IES','memory_slot_change_detection', fallback=memory_slot_change_detection)

    
    # Define command line arguments
    parser = ArgumentParser(description='WAPS Image Extractor Software.' +
                            ' Searches telemetry archive files as binary files for BIOLAB packets and assembles them into images.' +
                            ' GUI is optional. Options to scan a path for packets once or monitor the path continuously.')
    parser.add_argument("-i", "--input_path", dest="input_path", default=input_path,
                        help="Input path to be monitored for TM archives. Must exist. Default: input/")
    parser.add_argument("-o", "--output_path", dest="output_path", default=output_path,
                        help="Output path where extracted images are saved. Must exist. Default: output/")
    parser.add_argument("-lp", "--log_path", dest="log_path", default=log_path,
                        help="Log path where the extraction process log is saved. Must exist. Default: log/")
    parser.add_argument("-er", "--errors_only", action="store_true",
                        help="Show only warnings and errors in the log. Overwritten by debug")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Debug logging is enabled")
    parser.add_argument("-dg", "--disable_gui", action="store_true",
                        help="Disable Graphical interface")
    parser.add_argument("-ns", "--no_scan", action="store_true",
                        help="Disable the scan of existing files in the input path")
    parser.add_argument("-nt", "--no_tracker", action="store_true",
                        help="Disable the file tracker in the input path")
    parser.add_argument("-f", "--file_format", dest="file_format", default=file_format,
                        help="Telemetry archive file pattern. Example: '*.dat' Default: '*' as all files. For multiple formats edit the configuration file instead")
    parser.add_argument("-t", "--image_timeout", dest="image_timeout", default=image_timeout,
                        help="Image timeout in minutes. After this period image is considered OUTDATED. Default: 60")
    parser.add_argument("-msc", "--mem_slot_change", action="store_true",
                        help="Enable memory slot change detection from general BIOLAB telemetry")
    args = parser.parse_args()
    
    # Process command line arguments
    input_path = args.input_path
    output_path = args.output_path
    if (args.debug):
        log_level = 'DEBUG'
    elif (args.errors_only):
        log_level = 'ERROR'
    if (args.disable_gui):
        gui_enabled = '0'
    if (args.no_scan):
        run_scan = '0'
    if (args.no_tracker):
        run_tracker = '0'
    file_format = args.file_format
    image_timeout = args.image_timeout
    if (args.mem_slot_change):
        memory_slot_change_detection = '1'

    ##### Check critical parameters
    # TODO check IP and port
    # TODO if do not exist - create
    # Check existence of paths
    elif (not os.path.exists(output_path)):
        logging.error("Output path does not exist")
    elif (not os.path.exists(log_path)):
        logging.error("Log path does not exist")
    #####

    # Logging level definition
    if (log_level.upper() == 'ERROR'):
        log_level = logging.WARNING
    elif (log_level.upper() == 'WARNING'):
        log_level = logging.WARNING
    elif (log_level.upper() == 'DEBUG'):
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # TODO
    # Remove hardcoded IP address and port, add those to the parameters above

    # Initialize the WAPS IES socket
    ies = tcpreceiver.TCP_Receiver('192.168.56.101',
                                    '23456',
                                    output_path,
                                    log_path,
                                    log_level)

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
        print ('#')

    ies.image_timeout = timedelta(minutes = int(image_timeout))
    logging.info(" # Image timeout: " + str(int(image_timeout)) + ' minute(s)')

    if (int(memory_slot_change_detection)):
        logging.info(" # Detecting memory slot change from BIOLAB telemetry")

    logging.info(" # Running IES")
    if (int(gui_enabled)):
        ies.interface.update_tracker_active()
    ies.start()

if __name__ == "__main__":
    run_waps_ies(sys.argv)
