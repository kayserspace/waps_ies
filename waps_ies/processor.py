""" WAPS IES Image Packet processor """

from struct import unpack
import uuid
import logging
from datetime import datetime, timedelta
from waps_ies import waps_image

import os
import numpy as np
from PIL import Image
import io

# Global variables
current_biolab_memory_slot = None
image_transmission_in_progress = False


def sort_biolab_packets(packet_list,
                        incomplete_images,
                        receiver,
                        image_timeout = timedelta(minutes = 60),
                        biolab_memory_slot_change_detection = False):
    """
    Takes packet list and incomplete images. Returns list of incomplete images with sorted packets.

        Parameters:
            file_path (str): Location of the test bench data file

        Returns:
            packet_list (list): list of extracted BIOLAB packets
    """

    # Go through the packet list
    while (len(packet_list)):
        packet = packet_list.pop(0)

        if (not packet.in_spec()):
            logging.error(packet.packet_name + " is not a WAPS Image Packet")
            continue
        else:
            if (packet.is_waps_image_packet):
                status_message = receiver.get_status()
                logging.info(status_message)
                logging.info(str(packet))
            else:
                # Log not relevant BIOLAB TM packets only in DEBUG mode
                status_message = receiver.get_status()
                logging.debug(status_message)
                logging.debug(str(packet))

        global current_biolab_memory_slot
        # Important to recognise when the currently unfinished images are overwritten
        if (biolab_memory_slot_change_detection and
            current_biolab_memory_slot != packet.biolab_current_image_memory_slot):
            status_message = receiver.get_status()
            logging.info(status_message)
            logging.info('  Update of active Memory slot ' + str(packet.biolab_current_image_memory_slot) +
                        ' Previous: ' + str(current_biolab_memory_slot))
            for i in range(len(incomplete_images)):
                if (incomplete_images[i].memory_slot == packet.biolab_current_image_memory_slot):
                    incomplete_images[i].overwritten = True
                    logging.warning(' Incomplete image ' + incomplete_images[i].image_name + ' has been overwritten')
            current_biolab_memory_slot = packet.biolab_current_image_memory_slot

        
        global image_transmission_in_progress

        # Process the packet according to Generic TM ID (packet.data[84])
        # Only TM IDs of interest processed

        # Image initialization packet
        if (packet.generic_tm_id == 0x4100 or packet.generic_tm_id == 0x5100):
            """(Generic TM ID 0x4100, Generic TM Type set with corresponding Picture ID, 0 to 7, and Packet ID to 0x000)."""
            receiver.total_initialized_images = receiver.total_initialized_images + 1

            # Track whether image is being trasmitted
            image_transmission_in_progress = True

            if (packet.tm_packet_id != 0):
                logging.warning(packet.packet_name + ' Packet ID is not zero: ' + str(packet.tm_packet_id))

            # Create an image with the above data
            new_image = waps_image.WAPS_Image(packet)

            # Check for overwritten memory slot and whether this is a duplicate image
            duplicate_image = False
            for index, image in enumerate(incomplete_images):
                if (image.camera_type == new_image.camera_type and
                    image.memory_slot == new_image.memory_slot and
                    image.number_of_packets == new_image.number_of_packets and
                    image.time_tag == new_image.time_tag):
                    logging.warning(' Duplicated image detected')
                    duplicate_image = True
                elif (image.memory_slot == new_image.memory_slot):
                    incomplete_images[index].overwritten = True
                    logging.warning(' Previous image in memory slot ' + str(image.memory_slot) + ' overwritten')
                    check_overwritten_images(incomplete_images, interface)
            if (duplicate_image):
                break

            logging.info('  New ' + new_image.camera_type + ' image in Memory slot ' +  str(packet.image_memory_slot) +
                         ' with ' +  str(new_image.number_of_packets) + ' expected packets (' +
                         new_image.image_name + ')')

            # Add image to the database
            receiver.db.add_image(new_image)
            # Update packet's image uuid
            packet.image_uuid = new_image.uuid

            # Add image to the incomplete list
            incomplete_images.append(new_image)

            

        # Image data packet
        elif (packet.generic_tm_id == 0x4200 or packet.generic_tm_id == 0x5200):
            """(Generic TM ID 0x4200, Generic TM Type set with corresponding Picture ID, 0 to 7, and Packet ID is incremented)."""

            # Track whether image is being trasmitted
            image_transmission_in_progress = True

            # Search through incomplete images, matching image_memory_slot
            found_matching_image = False
            for i in range(len(incomplete_images)):
                if (incomplete_images[i].memory_slot == packet.image_memory_slot and
                    not incomplete_images[i].overwritten):
                    found_matching_image = True

                    incomplete_images[i].add_packet(packet)
                    incomplete_images[i].update = True

                    # Add packet to the database
                    packet.image_uuid = incomplete_images[i].uuid
                    receiver.db.update_image_status(incomplete_images[i])
                    break
            
            if (not found_matching_image):
                logging.error(packet.packet_name + ' matching image with memory slot ' + str(packet.image_memory_slot) + ' not found')


        else:

            if (image_transmission_in_progress):
                # An image is sent in one telemetry sequence
                # Each single packet request triggers this change as well
                # Status information after all of the processing
                status_message = receiver.get_status()
                logging.info(status_message)
                logging.info(' End of image transmission (No WAPS image packets in BIOLAB TM)')

                # Go through incomplete images and mark that transmission is finished
                for i in range(len(incomplete_images)):
                    if (incomplete_images[i].image_transmission_active):
                        incomplete_images[i].image_transmission_active = False
                        receiver.db.update_image_status(incomplete_images[i])

                # Reset transmission status
                image_transmission_in_progress = False

        if (packet.generic_tm_id == 0x4100 or packet.generic_tm_id == 0x5100 or 
            packet.generic_tm_id == 0x4200 or packet.generic_tm_id == 0x5200):
            
            # Increase total WAPS packet count
            receiver.total_waps_image_packets = receiver.total_waps_image_packets + 1

            # Add packet to the database
            receiver.db.add_packet(packet)
    
    if (receiver.interface):
        receiver.interface.update_stats()

    return incomplete_images



def write_file(image_data, file_path, filetype = 'wb', interface = None):
    """Write image to hard drive"""

    readtype = 'rb'
    if (filetype == 'w'):
        readtype = 'r'

    update_file_path = False
    # Check existing file
    try:
        version_number = 2
        while os.path.exists(file_path):
            with open(file_path, readtype) as file:
                file_data = file.read()
                if (file_data == image_data):
                    logging.info('File ' + file_path + " with identical data exists already. No need to overwrite.")
                    return True
                else:
                    logging.info('File ' + file_path + " exists already but data is different.")
                    # Change file name to indicate new version
                    file_path = file_path[:file_path.rfind('.')] + 'v' + str(version_number) + file_path[file_path.rfind('.'):]

    except IOError:
        pass

    # Write the file
    try:
        with open(file_path, filetype) as file:
            file.write(image_data)
            logging.info("Saved file: " + str(file_path))
            if (interface):
                file_name = file_path[file_path.rfind('/')-8:]
                interface.update_latets_file(file_name)

    except IOError:
        logging.error('Could not open file for writing: ' + file_path)
        return False

    # Successful write
    return True




def print_incomplete_images_status(incomplete_images):

    for index, image in enumerate(incomplete_images):
        missing_packets = image.get_missing_packets()
        image_percentage = '_'+ str(int(100.0*(image.number_of_packets - len(missing_packets))/image.number_of_packets))
        completeness_message = ('Image ' + image.image_name + ' is ' +
                                 image_percentage[1:] + '% complete (' +
                                 str(image.number_of_packets - len(missing_packets)) +
                                 '/' + str(image.number_of_packets) + ')')
        if (len(missing_packets)):
            completeness_message =  (completeness_message + '. Missing packets: ' +
                         image.missing_packets_string())
            
        logging.info(completeness_message)




def save_images(incomplete_images, output_path, receiver, save_incomplete = True):
    """
    Incomplete images and output path. Returns list of incomplete images with sorted packets.

        Parameters:
            

        Returns:
            
    """
    interface = receiver.interface
    finished_image_indexes = []
    
    for index, image in enumerate(incomplete_images):

        # Make sure folder with today's path exists
        date_path = output_path + image.CCSDS_time.strftime('%Y%m%d') + '/'
        if (not os.path.exists(date_path) or
            not os.path.isdir(date_path)):
            os.mkdir(date_path)

        successful_write = False

        # Update interface if available
        if (interface):
            interface.update_image_data(image)

        # Ignore incomplete images
        if (not save_incomplete and
            not image.is_complete() and
            image.image_transmission_active):
            continue

        # Ignore if there is no update on the image
        if (not image.update):
            continue
        
        # Get image binary data first
        image_data = image.reconstruct()
        # Add completion percentage to the file name
        missing_packets = image.get_missing_packets()
        image_percentage = '_'+ str(int(100.0*(image.number_of_packets - len(missing_packets))/image.number_of_packets))
        completeness_message = ('Image ' + image.image_name + ' is ' +
                                 image_percentage[1:] + '% complete (' +
                                 str(image.number_of_packets - len(missing_packets)) +
                                 '/' + str(image.number_of_packets) + ')')
        if (len(missing_packets)):
            completeness_message =  (completeness_message + '. Missing packets: ' +
                         image.missing_packets_string())
            
        if (not len(missing_packets) or image.image_transmission_active):
            logging.info(completeness_message)
        else:
            logging.warning(completeness_message)

        if (not len(missing_packets)):
            receiver.total_completed_images = receiver.total_completed_images + 1
            incomplete_images[index].image_transmission_active = False
        elif (not image.latest_saved_file): # Only during first transmission
            receiver.total_lost_packets = receiver.total_lost_packets + len(image.get_missing_packets(True))

        # Print detailed image information
        logging.info(incomplete_images[index])
        
        if (image.camera_type == 'uCAM'):
            # Sanity check the data
            if (image_data[0] != 0xFF or
                image_data[1] != 0xD8 or
                image_data[2] != 0xFF or
                image_data[3] != 0xDB):
                logging.warning(image.image_name + ' does not have a .JPG header')
            
            # Image data is saved as is, binary
            file_path = date_path + image.image_name + image_percentage + '.jpg'
            
            successful_write = write_file(image_data, file_path, 'wb', interface)
            if image.is_complete() and successful_write:
                finished_image_indexes.append(index)
                
        elif (image.camera_type == 'FLIR'):
            # TM data is first 480 bytes, then 9600 bytes of data
            tm_length = 480
            data_length = 9600

            if (len(image_data) != tm_length + data_length):
                logging.warning(str(image.image_name) + ' has incorrect data size: ' + str(len(image_data)))
        
            # FLIR telemetry data is saved into a text file
            file_path_tm = date_path + image.image_name + image_percentage + '_tm.txt'
            
            tm_image_data = ""
            for i in range(int(tm_length/2)):
                if (i < 80):
                    tm_image_data = tm_image_data + 'A'
                elif (i < 160 and i >= 80):
                    tm_image_data = tm_image_data + 'B'
                else:
                    tm_image_data = tm_image_data + 'C'
                tm_image_data = tm_image_data + (str(i%80) + ':' +
                        str(unpack( '>H', image_data[i*2:i*2+2] )[0]) +
                        '\n')

            successful_write = write_file(tm_image_data, file_path_tm, 'w', interface)
            if not successful_write:
                continue
            
            # FLIR Image data is converted to .csv file
            file_path_csv = date_path + image.image_name + image_percentage + '_data.csv'
            
            csv_image_data = str(unpack( '>H', image_data[tm_length:tm_length+2] )[0]) # first value
            for i in range(1, int((len(image_data)-tm_length)/2)):
                if (i % 80): # 80 values in one row
                    csv_image_data = csv_image_data + ','
                else: 
                    csv_image_data = csv_image_data + '\n'
                csv_image_data = csv_image_data + str(unpack( '>H', image_data[tm_length+i*2:tm_length+i*2+2])[0])
            csv_image_data = csv_image_data + '\n'
            
            successful_write = write_file(csv_image_data, file_path_csv, 'w', interface)
            if not successful_write:
                continue
            
            
            # FLIR Image data is converted is saved as .bmp file
            file_path = date_path + image.image_name + image_percentage + '.bmp'

            # Structure image data
            array_image_data = []
            for i in range(int((len(image_data)-tm_length)/2)):
                pixel = unpack( '>H', image_data[tm_length+i*2:tm_length+i*2+2] )[0]
                array_image_data.append([pixel])
            
     
            array_image_data = np.array(array_image_data)
            min_value = min(array_image_data)
            max_value = max(array_image_data)
            array_image_data = np.uint8((array_image_data - min_value) * (256.0/(max_value - min_value)))
            array_image_data = array_image_data.reshape((60,80))
            img = Image.fromarray(array_image_data, 'L')
            output_image = io.BytesIO()
            img.save(output_image, format='BMP')

            successful_write = write_file(output_image.getvalue(), file_path, 'wb', interface)
            if image.is_complete() and successful_write:
                finished_image_indexes.append(index)

        # On a successful file write note that there are not more updates
        if (successful_write):
            incomplete_images[index].update = False
            
            # Since the file write was successful, previous versions of the files
            try:
                if (incomplete_images[index].latest_saved_file):
                    if os.path.exists(incomplete_images[index].latest_saved_file):
                        os.remove(incomplete_images[index].latest_saved_file)
                    if os.path.exists(incomplete_images[index].latest_saved_file[:-4] + '_tm.txt'):
                        os.remove(incomplete_images[index].latest_saved_file[:-4] + '_tm.txt')
                    if os.path.exists(incomplete_images[index].latest_saved_file[:-4] + '_data.csv'):
                        os.remove(incomplete_images[index].latest_saved_file[:-4] + '_data.csv')
                    logging.info('Removed previous version of this file: ' + incomplete_images[index].latest_saved_file)

            except IOError:
                pass

            # And note the latest written down file
            incomplete_images[index].latest_saved_file = file_path
            if (incomplete_images[index].camera_type == "FLIR"):
                incomplete_images[index].latest_saved_file_tm = file_path[:-4] + '_tm.txt'
                incomplete_images[index].latest_saved_file_data = file_path[:-4] + '_data.csv'

        # Update interface if available
        if (interface):
            interface.update_image_data(image)
            interface.update_stats()

        # Update image filenames in database
        receiver.db.update_image_status(incomplete_images[index])
        receiver.db.update_image_filenames(incomplete_images[index])

    # Remove fully complete and written down images from the incomplete list
    if (len(finished_image_indexes)):
        for index in finished_image_indexes[::-1]:
            receiver.db.update_image_status(incomplete_images[index])
            incomplete_images.pop(index)

    return incomplete_images



def check_overwritten_images(incomplete_images, interface = None):
    """
    Incomplete images as input. Returns list of incomplete images still within grace period.
    """

    outdated_image_indexes = []

    for index, image in enumerate(incomplete_images):
        if (incomplete_images[index].overwritten):
            outdated_image_indexes.append(index)

    # Remove the outdated images from incomplete images list
    if (len(outdated_image_indexes)):
        for index in outdated_image_indexes[::-1]:
            logging.warning(' '+ str(incomplete_images[index].image_name) + ' is incomplete (' +
                            str(len(incomplete_images[index].packets)-len(incomplete_images[index].get_missing_packets())) +
                            '/' + str(incomplete_images[index].number_of_packets) + ') and OUTDATED')
            # Update interface if available
            incomplete_images[index].outdated = True
            if (interface):
                interface.update_image_data(incomplete_images[index])
            incomplete_images.pop(index)

    return incomplete_images
