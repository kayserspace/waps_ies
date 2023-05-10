"""
Script: processor.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: WAPS PD image extraction software for operations at MUSC
         WAPS packet sorting and image reconstruction module
Version: 2023-04-18 14:00, version 0.1

Change Log:
2023-04-18 version 0.1
 - initial version
"""

from struct import unpack, pack
import logging
import os
from datetime import datetime
from waps_ies import waps_image


def sort_biolab_packets(packet_list,
                        incomplete_images,
                        receiver,
                        biolab_memory_slot_change_detection=False):
    """Sort given packet list into images
    For each packet:
        1. Note received packet depending on the contents
        2. Get ec_states index for EC status
        3. Check change of memory slot in the EC throguh BIOLAB telemetry
        4. WAPS image init packet:
        4.1. Update EC state
        4.2. Create new image based on this packet
        4.3. Check if this is a duplicate
        4.4. Add image to database
        4.5. Check for existing packets in database
        4.6. Add image to active image list
        4.7. Assign a gui column to the EC is not done so already
        5. WAPS image data packet
        5.1. Find a match in the active image list
        5.2. Find a match in the database if not in active image list
        5.3. Note non-existing image if no active image list found
        6. Add pcaket to the database (with assign image UUID)
        7. Return active image list

    Args:
        packet_list (list): packets to be sorted
        incomplete_images (list): list of active (incomplete) images
        receiver (Receiver type): current waps_ies.Receiver instance
        biolab_memory_slot_change_detection (bool): whether to
                check for change of memory slot in the BIOLAB TM header

    Returns:
        incomplete_images (list): list of active (incomplete) images
    """

    # Go through the packet list
    for packet in packet_list:

        if not packet.in_spec():
            logging.error("%s is not a WAPS Image Packet", packet.packet_name)
            continue
        if packet.is_waps_image_packet:
            status_message = receiver.get_status()
            logging.info(status_message)
            logging.info(str(packet))
        else:
            # Log not relevant BIOLAB TM packets only in DEBUG mode
            status_message = receiver.get_status()
            logging.debug(status_message)
            logging.debug(str(packet))

        # Get index of the ECs in
        ec_i = receiver.get_ec_states_index(packet.ec_address)

        # Check the last writting memory slot
        last_mem_slot = packet.biolab_current_image_memory_slot
        if (biolab_memory_slot_change_detection and
                receiver.ec_states[ec_i]["last_memory_slot"] != last_mem_slot):
            status_message = receiver.get_status()
            logging.info(status_message)
            logging.info('  Update of active Memory slot %i Previous: %s',
                         last_mem_slot,
                         str(receiver.ec_states[ec_i]["last_memory_slot"]))
            for i, image in enumerate(incomplete_images):
                if image.memory_slot == last_mem_slot and image.ec_address == packet.ec_address:
                    incomplete_images[i].overwritten = True
                    logging.warning(' Incomplete image %s has been overwritten', image.image_name)
                    receiver.remove_overwritten_image(i)
            receiver.ec_states[ec_i]["last_memory_slot"] = last_mem_slot

        # Process the packet according to Generic TM ID (packet.data[84])
        # Only TM IDs of interest processed

        # Image initialization packet
        if packet.generic_tm_id in (0x4100, 0x5100):
            # Generic TM ID 0x4100, Generic TM Type set
            # with corresponding Picture ID, 0 to 7, and Packet ID to 0x000

            # Track whether image is being trasmitted
            receiver.ec_states[ec_i]["transmission_active"] = True

            if packet.tm_packet_id != 0:
                logging.warning('%s Packet ID is not zero: %i',
                                packet.packet_name,
                                packet.tm_packet_id)

            # Create an image with the above data
            new_image = waps_image.WapsImage(packet)
            new_image.ec_position = receiver.get_ec_position(new_image.ec_address)

            # Check for a duplicate image
            duplicate_image = False
            new_pkt_num = new_image.number_of_packets
            for index, image in enumerate(incomplete_images):
                if (image.ec_address == new_image.ec_address and
                        image.camera_type == new_image.camera_type and
                        image.memory_slot == new_image.memory_slot and
                        image.number_of_packets == new_pkt_num and
                        image.time_tag == new_image.time_tag):
                    logging.warning(' Duplicated image detected')
                    duplicate_image = True
                elif (image.ec_address == new_image.ec_address and
                        image.memory_slot == new_image.memory_slot):
                    incomplete_images[index].overwritten = True
                    logging.warning(' Memory slot %i of EC %i has been overwritten',
                                    image.memory_slot, packet.ec_address)
                    receiver.remove_overwritten_image(index)

            if duplicate_image:
                continue

            # Add image to the database
            image_added = receiver.database.add_image(new_image)

            # If image already exists in database - skip
            if image_added:
                receiver.total_initialized_images = receiver.total_initialized_images + 1
                logging.info('  New %s image in Memory slot %i with %i packets',
                             new_image.image_name,
                             packet.image_memory_slot,
                             new_image.number_of_packets)

                # Update packet's image uuid
                packet.image_uuid = new_image.uuid

                # Check database for existing packets
                existing_packet_list = receiver.database.retrieve_packets_after(packet)
                if len(existing_packet_list) != 0:
                    # Update all packets with this image uuid
                    for index, existing_packet in enumerate(existing_packet_list):
                        existing_packet_list[index].image_uuid = new_image.uuid
                        receiver.database.update_image_uuid_of_a_packet(existing_packet)
                    new_image.packets = existing_packet_list

                receiver.database.update_image_status(new_image)

                # Add image to the incomplete list
                incomplete_images.append(new_image)

            # On creation of a new image assign a GUI column
            if receiver.gui:
                receiver.assign_ec_column(new_image.ec_address)

        # Image data packet
        elif packet.generic_tm_id in (0x4200, 0x5200):
            # Generic TM ID 0x4200, Generic TM Type set
            # with corresponding Picture ID, 0 to 7, and
            # Packet ID is incremented

            # Track whether image is being trasmitted
            receiver.ec_states[ec_i]["transmission_active"] = True

            # Search through incomplete images, matching image_memory_slot
            found_matching_image = False
            for i, image in enumerate(incomplete_images):
                if (image.ec_address == packet.ec_address and
                        image.memory_slot == packet.image_memory_slot and
                        not image.overwritten):
                    found_matching_image = True

                    packet.image_uuid = incomplete_images[i].uuid
                    incomplete_images[i].add_packet(packet)
                    incomplete_images[i].update = True
                    receiver.database.update_image_status(incomplete_images[i])
                    break

            # Check database for a pre-existing image
            if not found_matching_image:
                old_image = receiver.database.retrieve_image_from_packet(packet)

                if old_image is not None:
                    found_matching_image = True

                    packet.image_uuid = old_image.uuid
                    old_image.add_packet(packet)
                    old_image.update = True
                    incomplete_images.append(old_image)
                    logging.info(" Loaded image %s from database to active memory",
                                 old_image.image_name)

            if not found_matching_image:
                logging.error('%s matching image %i not found',
                              packet.packet_name,
                              packet.image_memory_slot)

        else:
            if receiver.ec_states[ec_i]["transmission_active"]:
                # An image is sent in one telemetry sequence
                # Each single packet request triggers this change as well
                # Status information after all of the processing
                status_message = receiver.get_status()
                logging.info(status_message)
                logging.info(' End of image transmission (EC addr %i)',
                             packet.ec_address)

                # Go through incomplete images and
                # mark that transmission is finished
                for i, image in enumerate(incomplete_images):
                    if image.image_transmission_active and image.ec_address == packet.ec_address:
                        incomplete_images[i].image_transmission_active = False
                        incomplete_images[i].update = True
                        receiver.database.update_image_status(incomplete_images[i])

                # Reset transmission status
                receiver.ec_states[ec_i]["transmission_active"] = False

        if packet.is_waps_image_packet:

            # Increase total WAPS packet count
            receiver.total_waps_image_packets = receiver.total_waps_image_packets + 1

            # Add packet to the database
            receiver.database.add_packet(packet)

        if receiver.gui:
            receiver.gui.update_stats()

    return incomplete_images


def write_file(image_data, file_path, filetype='wb', gui=None):
    """Write image to the output path
    Before writing check existence of an identical file or filename.
    Change filename if already exists

    Args:
        image_data (data array): binary data or string data depending on the file format
        file_path (str): file path where to save the file
        filetype (str): binary or text file
        gui (gui type): for latest written file name update

    Returns:
        succesful_write (bool)
    """

    readtype = 'rb'
    if filetype == 'w':
        readtype = 'r'

    # Check existing file
    try:
        version_number = 2
        while os.path.exists(file_path):
            with open(file_path, readtype) as file:
                file_data = file.read()
                exists = " exists already "
                if file_data == image_data:
                    logging.info('File %s%s and is identical. %s',
                                 file_path,
                                 exists,
                                 "No need to overwrite.")
                    return True
                logging.info('File %s%s but contents is different',
                             file_path,
                             exists)
                # Change file name to indicate new version
                file_path = (file_path[:file_path.rfind('.')] + 'v' +
                             str(version_number) +
                             file_path[file_path.rfind('.'):])

    except IOError:
        pass

    # Write the file
    try:
        with open(file_path, filetype) as file:
            file.write(image_data)
            logging.info("Saved file: %s", str(file_path))
            if gui:
                file_name = file_path[file_path.rfind('/')-8:]
                gui.update_latets_file(file_name)

    except IOError:
        logging.error('Could not open file for writing: %s', file_path)
        return False

    # Successful write
    return True


def print_images_status(images):
    """Logs image completeness status

    Args:
        images (list): list of images for completeness status message
    """

    for image in images:
        missing_packets = image.get_missing_packets()
        completeness_message = ('Image %s is %s complete' %
                                (image.image_name,
                                 image.get_completeness_str()))
        if len(missing_packets) > 0:
            completeness_message = (completeness_message +
                                    '. Missing packets: ' +
                                    image.missing_packets_string())

        logging.info(completeness_message)


def create_command_stack(image, receiver):
    """Creates a command stack file
    Generate a new text file with current timestamp
    The command stack is to be used to re-request missing image packets

    Args:
        image (WapsImage type): image from which to generate the command stack
        receiver (Receiver type): current waps_ies.Receiver instance
    """

    ec_position = receiver.get_ec_position(image.ec_address)
    current_time = datetime.now()
    missing_packets = image.get_missing_packets()
    missing_packets_excluding_corrupted = image.get_missing_packets(True)

    data = ("Command stack for missing packet list re-request by\n" +
            "\tWAPS Image Extraction Software for WAPS payload\n" +
            f"Image initialization timestamp: {image.ccsds_time.strftime('%Y-%m-%d %H:%M:%S')}\n" +
            f"Last received packet timestamp: {image.last_update.strftime('%Y-%m-%d %H:%M:%S')}\n\n" +
            "ec_address\tec_position\tmemory_slot\tmissing_packet\treason\n")

    for packet in missing_packets:
        reason = "lost"
        if packet not in missing_packets_excluding_corrupted:
            reason = "corrupted"
        data = data + ("%i\t\t\t%s\t\t\t%i\t\t\t%i\t\t\t\t%s\n" %
                       (image.ec_address, ec_position, image.memory_slot, packet, reason))

    data = data + ("Total commands to issue: %i\n" % len(missing_packets))
    data = data + ("Generated by WAPS IES, %s" % current_time.strftime('%Y-%m-%d %H:%M:%S'))

    file_path = (receiver.comm_path + f"ec_{image.ec_address}_m{image.memory_slot}_" +
                 current_time.strftime('%Y-%m-%d_%H%M%S') + ".txt")

    try:
        with open(file_path, 'w') as file:
            file.write(data)
            logging.info("Command stack for %i %s m%i with %i missing packets",
                         image.ec_address, ec_position, image.memory_slot, len(missing_packets))
    except IOError:
        logging.error('Could not open file for writing: %s', file_path)


def save_images(images, output_path, receiver, save_incomplete=True):
    """ Reconstruct and save images to files
    For each image in the list
    1. Check whether it needs update. Skip if not.
    2. Get image completeness from missing packet list
    3. For uCAM image
    3.1. Reconstruct JPEG image from availlable packets
    4. Fof FLIR image
    4.1. Reconstrcut telemetry text file
    4.2. Reconstruct .csv file with image data
    4.3. Create BMP image based on image data
    5. On successful reconstruction remove previous file version(s)
    6. Update gui with image status
    7. Remove completed images from active image list

    Args:
        images (list): list of active (incomplete) images
        output_path (str): root output path where to save the images
        receiver (Receiver type): current waps_ies.Receiver instance
        save_incomplete (bool): whether to save incomplete images to file

    Returns:
        images (list): list of active (incomplete) images
    """

    gui = receiver.gui
    finished_images = []

    for index, image in enumerate(images):

        # Make sure folder with today's path exists
        date_path = output_path + image.ccsds_time.strftime('%Y%m%d') + '/'
        if (not os.path.exists(date_path) or
                not os.path.isdir(date_path)):
            os.mkdir(date_path)

        successful_write = False

        # Ignore if there is no update on the image
        if not image.update:
            continue

        # Update gui if available
        if gui:
            gui.update_image_data(image)

        # Ignore incomplete images
        if (not save_incomplete and
                not image.is_complete() and
                image.image_transmission_active):
            image.update = False
            continue

        # Get image binary data first
        image_data = image.reconstruct()
        # Add completion percentage to the file name
        missing_packets = image.get_missing_packets()
        completeness_str = image.get_completeness_str()
        image_percentage = '_' + completeness_str[:completeness_str.find('%')]
        completeness_message = ('Image %s is %s complete' %
                                (image.image_name,
                                 completeness_str))
        if len(missing_packets) > 0:
            completeness_message = (completeness_message +
                                    '. Missing packets: ' +
                                    image.missing_packets_string())

        if len(missing_packets) == 0 or image.image_transmission_active:
            logging.info(completeness_message)
        else:
            logging.warning(completeness_message)

            # Create command stack for missing packets
            create_command_stack(image, receiver)

        if len(missing_packets) == 0:
            image.image_transmission_active = False
            if image.latest_saved_file is None or image.latest_saved_file[-7:-4] != '100':
                receiver.total_completed_images = receiver.total_completed_images + 1

        if image.latest_saved_file is None:  # Only after the initial image transmission
            # Count lost packets

            receiver.total_lost_packets = (receiver.total_lost_packets +
                                           len(image.get_missing_packets(True)))

        # Print detailed image information
        logging.info(image)

        # Now save the image to file(s)
        if image.camera_type == 'uCAM':
            # Sanity check the data
            if (image_data[0] != 0xFF or
                    image_data[1] != 0xD8 or
                    image_data[2] != 0xFF or
                    image_data[3] != 0xDB):
                logging.warning('%s does not have a .JPG header',
                                image.image_name)

            # Image data is saved as is, binary
            file_path = (date_path + image.image_name +
                         image_percentage + '.jpg')

            successful_write = write_file(image_data, file_path, 'wb', gui)
            if image.is_complete() and successful_write:
                finished_images.append(index)

        elif image.camera_type == 'FLIR':
            # TM data is first 480 bytes, then 9600 bytes of data
            tm_length = 480
            data_length = 9600

            if len(image_data) != tm_length + data_length:
                logging.warning('%s has incorrect data size: %i',
                                image.image_name, len(image_data))

            # FLIR telemetry data is saved into a text file
            file_path_tm = (date_path + image.image_name +
                            image_percentage + '_tm.txt')

            tm_image_data = ""
            for i in range(int(tm_length/2)):
                if i < 80:
                    tm_image_data = tm_image_data + 'A'
                elif 160 > i >= 80:
                    tm_image_data = tm_image_data + 'B'
                else:
                    tm_image_data = tm_image_data + 'C'
                tm_image_data = (tm_image_data + str(i % 80) + ':' +
                                 str(unpack('>H', image_data[i*2:i*2+2])[0]) +
                                 '\n')

            successful_write = write_file(tm_image_data,
                                          file_path_tm,
                                          'w',
                                          gui)
            if not successful_write:
                continue

            # FLIR Image data is converted to .csv file
            file_path_csv = (date_path + image.image_name +
                             image_percentage + '_data.csv')

            csv_image_data = str(unpack('>H',
                                 image_data[tm_length:tm_length+2])[0])
            for i in range(1, int((len(image_data)-tm_length)/2)):
                if i % 80:  # 80 values in one row
                    csv_image_data = csv_image_data + ','
                else:
                    csv_image_data = csv_image_data + '\n'
                val = tm_length+i*2
                csv_image_data = (csv_image_data +
                                  str(unpack('>H', image_data[val:val+2])[0]))
            csv_image_data = csv_image_data + '\n'

            successful_write = write_file(csv_image_data,
                                          file_path_csv,
                                          'w',
                                          gui)
            if not successful_write:
                continue

            # FLIR Image data is converted is saved as .bmp file
            file_path = (date_path + image.image_name +
                         image_percentage + '.bmp')

            # Structure BMP image data
            array_image_data = []
            bmp_image_data = []
            for i in range(int((len(image_data)-tm_length)/2)):
                val = tm_length+i*2
                pixel = unpack('>H', image_data[val:val+2])[0]
                array_image_data.append(pixel)
            max_pixel = max(array_image_data)
            min_pixel = min(array_image_data)
            range_pixel = max_pixel - min_pixel
            # Restructure because BMP is flipped
            for y_i in range(60):
                for x_i in range(80):
                    pixel = array_image_data[(59-y_i)*80+x_i]
                    bmp_pixel = int((pixel - min_pixel)/range_pixel*255)
                    bmp_image_data.append(bmp_pixel)
                    bmp_image_data.append(bmp_pixel)
                    bmp_image_data.append(bmp_pixel)
                    bmp_image_data.append(255)
            bmp_image_data = bytearray(bmp_image_data)

            bmp_header = (bytes("BM", 'utf-8') +
                          pack('IHHIIIIHHIIIIII',
                               19200 + 54,  # file size
                               0, 0,        # reserved
                               54,          # offset
                               40,          # header size
                               80,          # image width
                               60,          # image height
                               1,           # planes
                               32,          # bits per pixel
                               0, 0,        # no compression
                               3780, 3780,  # pixel per meter
                               0, 0))       # unused
            bmp_data = bmp_header + bmp_image_data

            successful_write = write_file(bmp_data, file_path, 'wb', gui)
            if image.is_complete() and successful_write:
                finished_images.append(index)

        # On a successful file write note that there are not more updates
        if successful_write:
            image.update = False

            # Since the file write was successful,
            # remove previous versions of the files
            try:
                if image.latest_saved_file is not None and image.latest_saved_file != file_path:
                    filename = image.latest_saved_file
                    if os.path.exists(filename):
                        os.remove(filename)
                    filename = image.latest_saved_file[:-4] + '_tm.txt'
                    if os.path.exists(filename):
                        os.remove(filename)
                    filename = image.latest_saved_file[:-4] + '_data.csv'
                    if os.path.exists(filename):
                        os.remove(filename)
                    logging.info('Removed previous version of this file: %s',
                                 image.latest_saved_file)

            except IOError:
                pass

            # And note the latest written down file
            image.latest_saved_file = file_path
            if image.camera_type == "FLIR":
                image.latest_saved_file_tm = file_path[:-4] + '_tm.txt'
                image.latest_saved_file_data = file_path[:-4] + '_data.csv'

        # Update gui if available
        if gui:
            gui.update_image_data(image)
            gui.update_stats()

        # Update image in database
        receiver.database.update_image_status(image)
        receiver.database.update_image_filenames(image)

    # Remove fully complete and written down images from the incomplete list
    if len(finished_images) > 0:
        for index in finished_images[::-1]:
            receiver.database.update_image_status(images[index])
            images.pop(index)

    return images
