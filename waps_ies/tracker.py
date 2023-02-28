import logging
from datetime import datetime
import os
from waps_ies import processor, interface
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer
import time
from datetime import timedelta




class WAPS_tracker:
    """
    WAPS Image Packet class

    Attributes
    ----------
    source_file : str
        Source file path where the packet was extracted from
    extraction_time : str
        Time of packet extraction
    data : list
        Packet data stored as list of numbers. Each number represents one byte

    Methods
    -------
    info(additional=""):
        Prints the person's name and age.
    """

    def __init__(self, inf = 'input/', outf = 'output/', logf = 'log/', logging_level = logging.INFO):
        """
        Takes file path and returns list of packets

            Parameters:
                file_path (str): Location of the test bench data file

            Returns:
                packet_list (list): list of extracted BIOLAB packets
        """

        # Input parameters
        self.input_folder = inf
        self.output_folder = outf
        self.log_folder = logf
        self.logging_level = logging_level

        self.current_file = None

        self.file_queue = []
        self.processed_file_list = []
        self.incomplete_images = []

        # Set up logging
        log_filename = self.log_folder + 'WAPS_IES_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.log'
        logging.basicConfig(filename = log_filename, format='%(asctime)s:%(levelname)s:%(message)s', level=self.logging_level)
        logging.getLogger().addHandler(logging.StreamHandler())

        # Start-up messages
        logging.info(' ##### WAPS IES by Georgi Olentsenko at Kayser Space Ltd. #####')
        logging.info(' # Log file: ' + log_filename)
        logging.info(' # Monitored TM archive folder: '+ self.input_folder)
        logging.info(' # Extracted image folder: '+ self.output_folder)

        self.continue_running = True
        self.interface = None

        self.match_patterns = ["*"]
        self.ignore_patterns = None
        self.ignore_directories = False
        self.case_sensitive = True

        self.image_timeout = timedelta(minutes = 60)

        self.memory_slot_change_detection = False

    def add_interface(self, ies_interface):
        """ Add an interface object to the trackerer """

        # Check interface type before adding
        if (type(ies_interface) is interface.WAPS_interface):
            logging.debug('Interface added')
            self.interface = ies_interface
        else:
            logging.warning('Interface has wrong object type')

    def add_file_for_processing(self, file_path):
        """ Add a file for processing to the queue """

        self.file_queue.append(file_path)

    def start(self, run_tracker = True):
        """
        Takes file path and returns list of packets

            Parameters:
                file_path (str): Location of the test bench data file

            Returns:
                packet_list (list): list of extracted BIOLAB packets
        """
        
        # Create an observer
        folder_event_handler = PatternMatchingEventHandler(self.match_patterns,
                                                           self.ignore_patterns,
                                                           self.ignore_directories,
                                                           self.case_sensitive)

        # Monitored events
        def on_created(event):
            if (event.src_path in self.file_queue):
                logging.debug('"' + str(event.src_path) + ' already in the queue')
                return
            if (os.path.isdir(event.src_path)):
                logging.debug('"' + str(event.src_path) + ' is a folder, not added to the queue')
                return
            self.file_queue.append(event.src_path)
            logging.debug('"' + str(event.src_path) + ' has been created. Added to processing queue')

        def on_modified(event):
            if (event.src_path in self.file_queue):
                logging.debug('"' + str(event.src_path) + ' already in the queue')
                return
            if (os.path.isdir(event.src_path)):
                logging.debug('"' + str(event.src_path) + '" is a folder')
                return
            if (self.current_file != event.src_path):
                # In case of modification packets could have been potentially added
                # So if file is not currenly being processed, don't add it to the queue
                logging.debug('"' + str(event.src_path) + ' is modified but not currently being processed')
                return
            self.file_queue.append(event.src_path)
            logging.debug('"' + str(event.src_path) + ' has been modified. Added to processing queue')

        def on_moved(event):
            if (event.dest_path in self.file_queue):
                logging.debug('"' + str(event.dest_path) + ' already in the queue')
                return
            if (os.path.isdir(event.dest_path)):
                logging.debug('"' + str(event.dest_path) + ' is a folder')
                return
            self.file_queue.append(event.dest_path);
            logging.debug('"' + str(event.dest_path) + ' has been moved. Added to processing queue')

        folder_event_handler.on_created = on_created
        folder_event_handler.on_modified = on_modified
        folder_event_handler.on_moved = on_moved

        go_recursively = True
        ies_observer = Observer()
        ies_observer.schedule(folder_event_handler, self.input_folder, recursive=go_recursively)


        # Main loop with TM archive processing on the file queue
        try:
            if (run_tracker):
                ies_observer.start()
            
            while self.continue_running:
                
                # Processing delay
                time.sleep(1)
                
                # Process the file queue
                previous_file = None
                previous_file_size = 0
                while (len(self.file_queue)):

                    try:
                        start_pointer = 0
                        # Check if the file just had packets added
                        global current_file
                        current_file = self.file_queue.pop(0)
                        current_file_size = os.stat(current_file)
                        if ((current_file, current_file_size) in self.processed_file_list):
                            logging.debug(' File with the exactly name and size has been already processed. Skipping')
                            continue

                        # Get a list of packets from current file
                        packet_list = process_archive(current_file, start_pointer)
                        if (len(packet_list)): # If there are relevant packets in the file, note the file and its length
                            self.processed_file_list.append((current_file, current_file_size))
                        if (self.interface): # Update interface if available
                            if (current_file[len(self.input_folder)-1:] == self.input_folder):
                                self.interface.update_latest_file_processed(current_file[len(self.input_folder)-1:])
                            else:
                                longest_path_visible = current_file[-63:].find('/')
                                self.interface.update_latest_file_processed(current_file[-63+longest_path_visible:])

                        previous_file = current_file
                        previous_file_size = current_file_size

                        if (len(packet_list)):
                            # Sort packets into images
                            self.incomplete_images = processor.sort_biolab_packets(packet_list,
                                                                                   self.incomplete_images,
                                                                                   self.image_timeout,
                                                                                   self.interface,
                                                                                   self.memory_slot_change_detection)

                            # Reconstruct and save images, keeping in memory the incomplete ones
                            save_incomplete = True
                            self.incomplete_images = processor.save_images(self.incomplete_images,
                                                                           self.output_folder,
                                                                           save_incomplete,
                                                                           self.interface)
                    except FileNotFoundError:
                        logging.error("File '" + current_file + "' processing error")

                # After processing all files, check if images are outdated
                self.incomplete_images = processor.check_image_timeouts(self.incomplete_images,
                                                                        self.image_timeout,
                                                                        self.interface)
        
        except KeyboardInterrupt:
            logging.info(' Console quit')

        finally:
            try:
                ies_observer.stop()
                ies_observer.join()
                
            except RuntimeError as error:
                logging.error(' Thread error: ' + str(error))
            
            logging.info(' File tracker has been stopped')
            if (self.interface):
                self.interface.close()

            # TODO save image buffer to file in log folder for recovery



    def process_folder(self, save_incomplete = True):
        """
        Takes a directory, processes all files in it, saving extracted images

            Parameters:
                file_path (str): Location of the archive data file

            Returns:
                packet_list (list): list of extracted BIOLAB packets
        """

        try:
            for root, dirs, files in os.walk(self.input_folder):
                for file in files:

                    try:
                        if (self.match_patterns[0] != '*'):
                            no_match_found = True
                            for pattern in self.match_patterns:
                                if (file.find(pattern.replace('*', '')) != -1):
                                    no_match_found = False
                                    break
                            if no_match_found:
                                continue
                        
                        # From each file
                        filepath = os.path.join(root, file)

                        # Get a list of BIOLAB packets
                        packet_list = process_archive(filepath)
                        if (self.interface): # Update interface if available
                            self.interface.update_latest_file_processed(filepath[len(self.input_folder)-1:])

                        # Sort packets into images
                        self.incomplete_images = processor.sort_biolab_packets(packet_list,
                                                                               self.incomplete_images,
                                                                               self.image_timeout,
                                                                               self.interface,
                                                                               self.memory_slot_change_detection)

                        # Reconstruct and save images, keeping in memory the incomplete ones
                        self.incomplete_images = processor.save_images(self.incomplete_images,
                                                                       self.output_folder,
                                                                       save_incomplete,
                                                                       self.interface)
                    except FileNotFoundError:
                        logging.error("File '" + current_file + "' processing error")

            # After processing all files, check if images are outdated
            if (save_incomplete):
                self.incomplete_images = processor.check_image_timeouts(self.incomplete_images,
                                                                        self.image_timeout,
                                                                        self.interface)

        except KeyboardInterrupt:
            logging.warning(' Directory processing has been interrupted')
            


def process_archive(file_path, start_pointer = 0):
    """
    Takes file path and returns list of packets

        Parameters:
            file_path (str): Location of the archive data file

        Returns:
            packet_list (list): list of extracted BIOLAB packets
    """
    
    logging.debug('Processing: ' + file_path)
    
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
                    packet =  processor.BIOLAB_Packet(file_path, timestamp,
                                        datetime.now(),
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



def process_test_bench(file_path):
    """
    Takes file path and returns list of packets

        Parameters:
            file_path (str): Location of the test bench data file

        Returns:
            packet_list (list): list of extracted BIOLAB packets
    """

    logging.debug('Processing: ' + file_path)

    timestamp = datetime.fromtimestamp(os.path.getmtime(file_path))
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
                packet = processor.BIOLAB_Packet(file_path, timestamp,
                                        datetime.now(),
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
