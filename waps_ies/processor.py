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
from waps_ies import waps_image


def sort_biolab_packets(packet_list,
                        incomplete_images,
                        receiver,
                        biolab_memory_slot_change_detection=False):
    """
    Takes packet list and incomplete images.
    Returns list of incomplete images with sorted packets.

        Parameters:
            file_path (str): Location of the test bench data file

        Returns:
            packet_list (list): list of extracted BIOLAB packets
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
                if image.memory_slot == last_mem_slot:
                    incomplete_images[i].overwritten = True
                    logging.warning(' Incomplete image %s has been %s',
                                    image.image_name,
                                    "overwritten")
            receiver.ec_states[ec_i]["last_memory_slot"] = last_mem_slot

        # Process the packet according to Generic TM ID (packet.data[84])
        # Only TM IDs of interest processed

        # Image initialization packet
        if packet.generic_tm_id in (0x4100, 0x5100):
            # Generic TM ID 0x4100, Generic TM Type set
            # with corresponding Picture ID, 0 to 7, and Packet ID to 0x000
            val = receiver.total_initialized_images + 1
            receiver.total_initialized_images = val

            # Track whether image is being trasmitted
            receiver.ec_states[ec_i]["transmission_active"] = True

            if packet.tm_packet_id != 0:
                logging.warning('%s Packet ID is not zero: %i',
                                packet.packet_name,
                                packet.tm_packet_id)

            # Create an image with the above data
            new_image = waps_image.WapsImage(packet)

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
                    logging.warning(' Memory slot %i overwritten',
                                    image.memory_slot)
                    check_overwritten_images(incomplete_images,
                                             receiver.gui)
            if duplicate_image:
                break

            logging.info('  New %s image in Memory slot %i with %i packets',
                         new_image.image_name,
                         packet.image_memory_slot,
                         new_image.number_of_packets)

            # Add image to the database
            receiver.database.add_image(new_image)
            # Update packet's image uuid
            packet.image_uuid = new_image.uuid

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

                    incomplete_images[i].add_packet(packet)
                    incomplete_images[i].update = True

                    # Add packet to the database
                    packet.image_uuid = incomplete_images[i].uuid
                    receiver.database.update_image_status(incomplete_images[i])
                    break

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
                    if image.image_transmission_active:
                        incomplete_images[i].image_transmission_active = False
                        incomplete_images[i].update = True
                        receiver.database.update_image_status(incomplete_images[i])

                # Reset transmission status
                receiver.ec_states[ec_i]["transmission_active"] = False

        if packet.is_waps_image_packet:

            # Increase total WAPS packet count
            val = receiver.total_waps_image_packets + 1
            receiver.total_waps_image_packets = val

            # Add packet to the database
            receiver.database.add_packet(packet)

        if receiver.gui:
            receiver.gui.update_stats()

    return incomplete_images


def write_file(image_data, file_path, filetype='wb', gui=None):
    """ Write image to local storage """

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
    """ Log image completeness status """

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


def save_images(images, output_path, receiver, save_incomplete=True):
    """
    Incomplete images and output path.
    Returns list of incomplete images with sorted packets.
        Parameters:
        Returns:
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

        if len(missing_packets) == 0:
            val = receiver.total_completed_images + 1
            receiver.total_completed_images = val
            image.image_transmission_active = False
        elif not image.latest_saved_file:  # Only during first transmission
            val = (receiver.total_lost_packets +
                   len(image.get_missing_packets(True)))
            receiver.total_lost_packets = val

        # Print detailed image information
        logging.info(image)

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
                if image.latest_saved_file:
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


def check_overwritten_images(images, gui=None):
    """
    Incomplete images as input.
    Returns list of incomplete images still within grace period.
    """

    overwritten_images = []

    for index, image in enumerate(images):
        if image.overwritten:
            overwritten_images.append(index)

    # Remove the outdated images from incomplete images list
    if len(overwritten_images) > 0:
        for index in overwritten_images[::-1]:
            logging.warning(' %s is incomplete (%i/%i) and OVERWRITTEN',
                            images[index].image_name,
                            len(images[index].packets) -
                            len(images[index].get_missing_packets()),
                            images[index].number_of_packets)
            if gui:
                gui.update_image_data(images[index])
            images.pop(index)

    return images
