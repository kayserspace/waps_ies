"""
Script: receiver.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: WAPS PD image extraction software for operations at MUSC
         Receiver class. Receives and processes CCSDS packets
Version: 2023-04-18 14:00, version 0.1

Change Log:
2023-04-18 version 0.1
 - initial version
"""

import logging, os, sys
from datetime import datetime, timedelta
import socket
import time
from struct import unpack
from waps_ies import interface, processor, database, waps_packet

# CCSDS header lengths
CCSDS1_HEADER_LENGTH = 6
CCSDS2_HEADER_LENGTH = 10
CCSDS_HEADERS_LENGTH = CCSDS1_HEADER_LENGTH + CCSDS2_HEADER_LENGTH

# BIOLAB TM id position in CCSDS packet
BIOLAB_ID_POSITION = 40


class Receiver:
    """
    TCP Receiver class

    Attributes
    ----------

    Methods
    -------

    """

    failed_connection_count = 0
    tcp_rerequest_count = 0

    comm_path = '/'

    log_level = logging.INFO
    log_file = None
    log_start = 0

    last_packet_ccsds_time = datetime(1980, 1, 6)

    last_status_update = datetime.now()
    last_outdated_images_check = datetime.now()

    ec_states = []

    refresh_gui_list_window = False

    memory_slot_change_detection = False
    skip_crc = False

    # Main loop enabled
    continue_running = True

    def __init__(self, waps_config):
        """
        Initialize the TCP connection

        Attributes
        ----------

        Methods
        -------

        """

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
            logging.info("Log path does not exist. Creating it...\n...")
            os.makedirs(waps_config["log_path"])

        # Enable logging
        self.log_path = waps_config["log_path"]
        self.log_level = waps_config["log_level"]
        self.start_new_log()

        # Start-up message
        logging.info(' ##### WAPS Image Extraction Software #####')
        logging.info(' # Logging path: %s', waps_config["log_path"])
        logging.info(' # Logging level: %s', log_level_printout)

        # Check critical parameters
        if not waps_config["ip_address"] or not waps_config["port"]:
            logging.error("%s%s%s%s", "Server IP address or port not specified\n",
                          "Please specify IP address and port",
                          " inline or in the configuration file\n",
                          "Example: waps_ies_app.py -ip localhost -p 12345")
            sys.exit()

        # TCP client
        self.socket = None
        self.server_address = (waps_config["ip_address"], int(waps_config["port"]))
        logging.info(' # Server: %s:%s',
                     waps_config["ip_address"],
                     waps_config["port"])
        self.tcp_timeout = float(waps_config["tcp_timeout"])
        logging.info(' # TCP timeout: %s seconds', waps_config["tcp_timeout"])
        self.connected = False

        # Check existence of output path
        if not os.path.exists(waps_config["output_path"]):
            logging.info("Output path does not exist. Creating it...\n...")
            os.makedirs(waps_config["output_path"])

        # Check existence of output path
        if not os.path.exists(waps_config["comm_path"]):
            logging.info("Command stack path does not exist. Creating it...\n...")
            os.makedirs(waps_config["comm_path"])

        self.output_path = waps_config["output_path"]
        logging.info(' # Output path: %s', waps_config["output_path"])
        self.comm_path = waps_config["comm_path"]
        logging.info(' # Command stack path: %s', waps_config["comm_path"])
        self.database_file = waps_config["database_file"]
        logging.info(' # Database file: %s', waps_config["database_file"])

        self.image_timeout = timedelta(0)
        if int(waps_config["image_timeout"]) != 0:
            self.image_timeout = timedelta(minutes=int(waps_config["image_timeout"]))
            logging.info(' # Image timeout: %i minute(s)', int(waps_config["image_timeout"]))

        if waps_config["detect_mem_slot"] == '1':
            self.memory_slot_change_detection = True
            logging.info(" # Detecting memory slot change from BIOLAB telemetry")

        if waps_config["skip_crc"] == '1':
            skip_crc = True
            if skip_crc:
                logging.info(" # IES shall not report failed CRC checks")

        # Configure gui
        self.gui = None
        if waps_config["gui_enabled"] == '1':
            logging.info(" # Running Graphical User Interface")
            self.gui = interface.WapsIesGui(self)
            gui_startup = datetime.now()
            longer_time_message = False
            while not self.gui.window_open:
                print('#', end='', flush=True)
                time.sleep(0.1)
                if (datetime.now() - gui_startup > timedelta(seconds=10) and
                        not longer_time_message):
                    longer_time_message = True
                    logging.info("--- GUI taking longer than expected to boot")
                if datetime.now() - gui_startup > timedelta(seconds=60):
                    longer_time_message = True
                    logging.error("--- Something precents GUI from starting")
                    break
            logging.info("# GUI opened")
            logging.debug(' GUI took %s to start', str(datetime.now() - gui_startup))

        # Active image storage
        self.images = []

        # Status parameters
        self.timeout_notified = False

        # Restart every session
        self.total_packets_received = 0
        self.total_biolab_packets = 0
        self.total_waps_image_packets = 0
        self.total_initialized_images = 0
        self.total_completed_images = 0
        self.total_lost_packets = 0
        self.total_corrupted_packets = 0
        self.total_received_bytes = 0

        self.database = database.Database(self.database_file)

    def start_new_log(self):
        """ Start a new log file """

        # Set up logging
        new_log_filename = (self.log_path + 'WAPS_IES_' +
                            datetime.now().strftime('%Y%m%d_%H%M%S') + '.log')
        if self.log_file is not None:
            logging.info(" Closing this log file. Next one is: %s",
                         new_log_filename)
        logging.basicConfig(filename=new_log_filename,
                            format='%(asctime)s:%(levelname)s:%(message)s',
                            level=self.log_level,
                            force=True)
        logging.getLogger().addHandler(logging.StreamHandler())
        if self.log_file is not None:
            logging.info(" Previos log file: %s", self.log_file)

        self.log_start = datetime.now()
        self.log_file = new_log_filename

    def get_status(self):
        """ Get receiver status message """

        current_time = self.last_packet_ccsds_time.strftime("%Y/%m/%d %H:%M:%S")
        status_message = ("# CCSDS Time: %s Pkts:%d:%d:%d Miss:%d:%d, Imgs:%d:%d" %
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

        for ec_state in self.ec_states:
            if ec_state["ec_address"] == ec_address:
                return ec_state["ec_position"]

        return '?'

    def get_ec_states_index(self, ec_address):
        """ Get EC index in the ec_states table """

        # Find existing entry
        for i, ec_state in enumerate(self.ec_states):
            if ec_state["ec_address"] == ec_address:
                return i

        # Create a new entry
        ec_state = {"ec_address": ec_address,
                    "ec_position": '?',
                    "gui_column": None,  # Assign on first packet
                    "transmission_active": False,
                    "last_memory_slot": None}
        self.ec_states.append(ec_state)

        return len(self.ec_states) - 1

    def assign_ec_column(self, ec_address):
        """ Assign an EC column in the WAPS GUI """

        index = self.get_ec_states_index(ec_address)
        if self.ec_states[index]["gui_column"] is None:

            # Get current column occupation
            column_occupation = [None, None, None, None]
            for i, ec_state in enumerate(self.ec_states):
                if ec_state["gui_column"] is not None:
                    if 4 > ec_state["gui_column"] >= 0:
                        column_occupation[ec_state["gui_column"]] = ec_state["ec_address"]

            # Assign an empty column
            for i in range(4):
                if not column_occupation[i]:
                    self.ec_states[index]["gui_column"] = i
                    break

            if self.ec_states[index]["gui_column"] is None:
                logging.warning(' All GUI columns are occupied already')
            elif self.gui:
                logging.info(" EC address " + str(self.ec_states[index]["ec_address"]) +
                             " with position " + self.ec_states[index]["ec_position"] +
                             " occupies GUI column " + str(self.ec_states[index]["gui_column"]))
                self.gui.update_column_occupation(self.ec_states[index]["gui_column"],
                                                  self.ec_states[index]["ec_address"],
                                                  self.ec_states[index]["ec_position"])

    def clear_gui_column(self, column):
        """ Clear GUI column assignment """

        # Get current column occupation
        for i, ec_state in enumerate(self.ec_states):
            if ec_state["gui_column"] == int(column):
                self.ec_states[i]["gui_column"] = None

    def check_outdated_images(self):
        """
        Check if any image is outdatedbased on CCSDS packet time once a minute.
        This is purely cosmetic fo the GUI
        """

        current_time = datetime.now()
        if (self.last_outdated_images_check > current_time + timedelta(minutes=1) and
                self.image_timeout != timedelta(0)):
            self.last_outdated_images_check = current_time
            for index, image in enumerate(self.images):
                if self.last_packet_ccsds_time > image.last_update + self.image_timeout:
                    self.images[index].outdated = True
                    if self.gui:
                        self.gui.update_image_data(self.images[index])

    def remove_overwritten_image(self, index):
        """ Remove and overwritten image from active image list """

        logging.warning(' %s is incomplete (%i/%i) and OVERWRITTEN',
                        self.images[index].image_name,
                        len(self.images[index].packets) -
                        len(self.images[index].get_missing_packets()),
                        self.images[index].number_of_packets)
        if self.gui:
            self.gui.update_image_data(self.images[index])
        self.images.pop(index)

    def connect_to_server(self):
        """ Connect to TCP server and configure keepalive """

        try:
            # Initialize socket
            self.socket = socket.socket(socket.AF_INET,
                                        socket.SOCK_STREAM)

            # BIOLAB TM expected at 1Hz per EC
            # Allowing more than double the time by default: 2.1 seconds
            self.socket.settimeout(float(self.tcp_timeout))
            self.socket.connect(self.server_address)
            self.connected = True
            if self.gui:
                self.gui.update_server_connected()

            # Set TCP keepalive on an open socket
            if hasattr(socket, "SO_KEEPALIVE"):
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            # Activate after 1 second of idleness
            if hasattr(socket, "TCP_KEEPIDLE"):
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
            # Send a keepalive ping once every 3 seconds
            if hasattr(socket, "TCP_KEEPINTVL"):
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 3)
            # Close the connection after 5 failed pings, or 15 seconds in this case
            if hasattr(socket, "TCP_KEEPCNT"):
                self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)

            logging.info(" # TCP connection to %s:%s established",
                         self.server_address[0],
                         str(self.server_address[1]))
            self.failed_connection_count = 0

            return True

        except Exception as err:
            self.failed_connection_count = self.failed_connection_count + 1
            if self.failed_connection_count < 5:
                logging.error(" Could not connect to socket.%s%s",
                              " Error: ",
                              str(err))
            else:
                if not self.failed_connection_count % 100:
                    logging.error(" Connection failed %i times. Error: %s",
                                  self.failed_connection_count,
                                  str(err))
                print(" Connection failed " + str(self.failed_connection_count)
                      + " times\r", end='')
            return False

        return False

    def receive_from_server(self, expected_length):
        """
        Receive data as a TCP client
        In case of failure to receive the correct amount retry set amount of times
        """

        # In most cases one reception should be enough
        data = self.socket.recv(expected_length)
        data_length = len(data)
        if data_length == expected_length:
            return data

        # Try again
        # Number of attempts to receive the expected data
        allowed_attempts = 3
        attempt = 1  # One already done

        while attempt <= allowed_attempts:
            attempt = attempt + 1
            self.tcp_rerequest_count = self.tcp_rerequest_count + 1
            logging.debug('Expected data length of %i vs actual %i. Retry attempts: %i',
                          expected_length, data_length, attempt)
            recv_length = expected_length - data_length
            data = data + self.socket.recv(recv_length)

            data_length = len(data)
            if data_length == expected_length:
                return data

        raise ValueError("Unexpected reception length: %i bytes", data_length)

    def start(self):
        """ Main receiver loop """

        try:
            while self.continue_running:

                # On change of date move on to a new log file
                if datetime.now().strftime('%d') != self.log_start.strftime('%d'):
                    self.start_new_log()

                # Check if any image is outdated
                self.check_outdated_images()

                if self.refresh_gui_list_window:
                    self.refresh_gui_list_window = False
                    self.gui.refresh_image_list()

                if not self.connected:
                    self.connected = self.connect_to_server()

                    # If still not connected
                    if not self.connected:
                        time.sleep(1)  # Delay before trying to connect again
                        continue

                try:
                    # Get the next packet
                    ccsds_header = self.receive_from_server(CCSDS_HEADERS_LENGTH)
                    self.timeout_notified = False

                    received_header_length = len(ccsds_header)
                    if received_header_length != CCSDS_HEADERS_LENGTH:
                        raise Exception("Unexpected length of CCSDS header: %i bytes",
                                        received_header_length)

                    # Increase packet count
                    if received_header_length > 0:
                        self.total_packets_received = self.total_packets_received + 1
                        self.total_received_bytes = (self.total_received_bytes +
                                                     received_header_length)

                    # Update interfeace status
                    if self.gui:
                        self.gui.update_server_active()
                        self.gui.update_ccsds_count()

                    ccsds1_packet_length = unpack('>H', ccsds_header[4:6])[0]

                    # calculate & receive remaining bytes in packet:
                    packet_data_length = ccsds1_packet_length + 1 - CCSDS2_HEADER_LENGTH

                    biolab_packet = None
                    packet_data = self.receive_from_server(packet_data_length)
                    biolab_packet = self.process_ccsds_packet(ccsds_header + packet_data)

                    if biolab_packet is not None:
                        # Sort packets into images
                        self.images = processor.sort_biolab_packets([biolab_packet],
                                                                    self.images,
                                                                    self,
                                                                    self.memory_slot_change_detection)

                        # Reconstruct and save images, keeping in memory the incomplete ones
                        self.images = processor.save_images(self.images,
                                                            self.output_path,
                                                            self,
                                                            False)  # Not incomplete

                        # Show current state of incomplete images
                        # if a WAPS image packet has been received
                        if biolab_packet.is_waps_image_packet:
                            processor.print_images_status(self.images)

                    # Status information after all of the processing
                    status_message = self.get_status() + '\r'
                    if self.log_level == logging.DEBUG:
                        logging.debug(status_message)
                    else:
                        current_time = datetime.now()
                        if (current_time > self.last_status_update +
                                timedelta(milliseconds=20)):             # 50 Hz max
                            self.last_status_update = current_time
                            print(status_message, end='')

                except TimeoutError:
                    if not self.timeout_notified:
                        self.timeout_notified = True
                        if self.gui:
                            self.gui.update_server_connected()
                            self.gui.update_stats()

                            # Status information after all of the processing
                            status_message = self.get_status() + '\r'
                            if self.log_level == logging.DEBUG:
                                logging.debug(status_message)
                            else:
                                current_time = datetime.now()
                                if (current_time > self.last_status_update +
                                        timedelta(milliseconds=20)):             # 50 Hz max
                                    self.last_status_update = current_time
                                    print(status_message, end='')
                        logging.warning("\nNo CCSDS packets received for more than %s seconds",
                                        self.tcp_timeout)

                except KeyboardInterrupt:
                    raise KeyboardInterrupt

                except Exception as err:
                    logging.error(str(err))
                    self.connected = False
                    self.socket.close()
                    if self.gui:
                        self.gui.update_server_disconnected()

        except KeyboardInterrupt:
            logging.info(' # Keyboard interrupt, closing')

        finally:
            # Close gui if it is running
            if self.gui:
                self.gui.close()

            if self.database:
                self.database.database.close()
                logging.info(" # Closed database")

            self.socket.close()
            logging.info(" # Disconnected from server")
            logging.info("      Sessions total numbers")
            logging.info("  ccsds packets received:      %d",
                         self.total_packets_received)
            logging.info("  biolab TM packets received:  %d",
                         self.total_biolab_packets)
            logging.info("  WAPS image packets received: %d",
                         self.total_waps_image_packets)
            logging.info("  Initializaed images:         %d",
                         self.total_initialized_images)
            logging.info("  Completed images:            %d",
                         self.total_completed_images)
            logging.info("  Lost packets:                %d",
                         self.total_lost_packets)
            logging.info("  Corrupted packets:           %d",
                         self.total_corrupted_packets)
            logging.info("  Total received bytes:        %d",
                         self.total_received_bytes)
            logging.info("  TCP re-request needed:       %d",
                         self.tcp_rerequest_count)

    def process_ccsds_packet(self, ccsds_packet):
        """
        Takes a ccsds packet, extracts WAPS image packet if present

            Parameters:
                file_path (str): Location of the archive data file

            Returns:
                packet_list (list): list of extracted biolab packets
        """

        ccsds_packet_length = len(ccsds_packet)

        if len(ccsds_packet) < CCSDS_HEADERS_LENGTH:
            logging.error(" ccsds packet is too short: %d bytes",
                          len(ccsds_packet))
            return None

        try:
            # ccsds primary header:
            word1 = unpack('>H', ccsds_packet[0:2])[0]
            # ccsds1_version_number = (word1 >> 13) & 0x0007  # bits 0-2
            ccsds1_type = (word1 >> 12) & 0x0001  # bit 3
            # ccsds1_secondary_hdr = (word1 >> 11) & 0x0001  # bit 4
            ccsds1_apid = (word1 >> 0) & 0x03ff  # bits 5-15
            # word2 = unpack('>H', ccsds_packet[2:4])[0]
            # ccsds1_seq_flags = (word2 >> 14) & 0x0003  # bits 0-1
            # ccsds1_seq_counter = (word2 >>  0) & 0x3fff  # bits 2-15
            ccsds1_packet_length = unpack('>H', ccsds_packet[4:6])[0]

            # ccsds secondary header:
            ccsds2_coarse_time = unpack('>L', ccsds_packet[6:10])[0]
            word3 = unpack('>H', ccsds_packet[10:12])[0]
            # calculate into milliseconds from bits 0-7
            ccsds2_fine_time = ((word3 >> 8) & 0x00ff) * 1000 / 256
            current_time = datetime.now()
            ccsds_time = (datetime(1980, 1, 6) +
                          timedelta(seconds=ccsds2_coarse_time +
                                    ccsds2_fine_time / 1000.0))
            # ccsds2TimeID = (word3 >> 6) & 0x0003   # bits 8-9
            # ccsds2CW = (word3 >> 5) & 0x0001   # bit 10
            # ccsds2ZOE = (word3 >> 4 ) & 0x0001   # bit 11
            # ccsds2PacketType = (word3 >> 0) & 0x000f   # bits 12-15

            ccsds2_packet_id32 = unpack('>L', ccsds_packet[12:16])[0]
            # ccsds2Spare = (ccsds2PacketID32 >> 31) & 0x00000000
            ccsds2_element_id = (ccsds2_packet_id32 >> 27) & 0x0000000f
            ccsds2_packet_id27 = (ccsds2_packet_id32 >> 0) & 0x07ffffff

            ccsds_str = (" New ccsds packet (%d b)\n      Received at %s\n",
                         len(ccsds_packet), str(current_time))

            str_type = "System"
            if ccsds1_type == 1:
                str_type = "Payload"
            ccsds_str = ccsds_str + ("      Type: %s ", str_type)
            ccsds_str = ccsds_str + ("APID: %d ", ccsds1_apid)
            ccsds_str = ccsds_str + ("Length: %d\n", ccsds1_packet_length)
            str_element_id = "not mapped"
            if ccsds2_element_id == 2:
                str_element_id = "Columbus"
            ccsds_str = ccsds_str + ("      Element ID: %d (%s) ",
                                     int(ccsds2_element_id),
                                     str_element_id)
            ccsds_str = ccsds_str + ("Packet ID 27: %d\n", ccsds2_packet_id27)
            ccsds_str = ccsds_str + ("      Packet timestamp: (%s %s) %s",
                                     "coarse: " + str(ccsds2_coarse_time),
                                     "fine: " + str(ccsds2_fine_time),
                                     str(ccsds_time))

            logging.debug(ccsds_str)

        except Exception as err:
            logging.debug(str(err))
            return None

        self.last_packet_ccsds_time = ccsds_time

        # Check packet length and biolab ID
        if (ccsds_packet_length < 42 or
                ccsds_packet[BIOLAB_ID_POSITION] != 0x40):
            logging.debug("      Not a biolab TM packet")
            return None

        biolab_packet_length = ccsds_packet[BIOLAB_ID_POSITION + 1] * 2 + 4
        if biolab_packet_length < 254:
            logging.warning(" Unexpected biolab packet length: %d",
                            biolab_packet_length)

        # Count biolab packets
        self.total_biolab_packets = self.total_biolab_packets + 1

        # Create biolab packet as is
        biolab_tm_data = ccsds_packet[BIOLAB_ID_POSITION:BIOLAB_ID_POSITION +
                                      biolab_packet_length]
        packet = waps_packet.WapsPacket(ccsds_time,
                                        current_time,
                                        biolab_tm_data,
                                        self)  # receiver

        # If packet matches biolab specification add it to list
        if packet.in_spec():
            return packet
        return None
