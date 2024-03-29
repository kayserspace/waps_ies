"""
Script: processor.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: WAPS PD image extraction software for operations at MUSC
         WAPS packet sorting and image reconstruction module
Version: 2023-09-27 version 1.1

Change Log:
2023-04-18 version 0.1
 - initial version
2023-05-31 v 1.0
 - release
2023-09-27 version 1.1
 - Disabled command stack generation in case there are no missing packets
 - Added EC position to the extracted file name format
 - Changed command stack format to be compatible with Yamcs input format
 - Added directory creating in case the output directory was removed during operation
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
                    receiver.database.update_image_status(incomplete_images[i])
                    logging.warning(' Incomplete image %s has been overwritten', image.image_name)
                    incomplete_images = receiver.remove_overwritten_image(i)
            receiver.ec_states[ec_i]["last_memory_slot"] = last_mem_slot
            # Update all previous database entries in this memory slot as overwritten
            receiver.database.update_overwritten_images(packet)

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
                    incomplete_images = receiver.remove_overwritten_image(index)

            if duplicate_image:
                continue

            # Add image to the database
            uuid = receiver.database.add_image(new_image)

            # Update packet's image uuid
            packet.image_uuid = uuid

            # If image already exists in database - skip
            if uuid == new_image.uuid:
                receiver.total_initialized_images = receiver.total_initialized_images + 1
                logging.info('  New %s image in Memory slot %i with %i packets',
                             new_image.image_name,
                             packet.image_memory_slot,
                             new_image.number_of_packets)

                # Check database for existing packets
                existing_packet_list = receiver.database.retrieve_packets_after(packet)
                if len(existing_packet_list) != 0:
                    # Update all packets with this image uuid
                    for index, existing_packet in enumerate(existing_packet_list):
                        # Since image_uuid of the packet is changed, make sure the previous image is updated too.
                        if (existing_packet.image_uuid is not None and
                                existing_packet.image_uuid not in receiver.recover_image_uuids):
                            receiver.recover_image_uuids.append(existing_packet_list[index].image_uuid)
                        existing_packet_list[index].image_uuid = new_image.uuid
                        receiver.database.update_image_uuid_of_a_packet(existing_packet)
                        new_image.add_packet(existing_packet)

                # Add image to the incomplete list
                incomplete_images.append(new_image)

            receiver.database.update_image_status(new_image)

            # Update all previous database entries in this memory slot as overwritten
            receiver.database.update_overwritten_images(packet)

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
                        (not image.overwritten or packet.ccsds_time < image.last_update)):
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
                logging.error('%s matching image in memory slot %i not found',
                              packet.packet_name,
                              packet.image_memory_slot)
                logging.info(" Forging a placeholder image")
                forged_init_packet = receiver.forge_init_packet(packet)
                packet_list.append(forged_init_packet)

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
        file_path (str): Actual written file
                         None if could not write the file
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
                    return file_path
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
        return None

    # Successful write
    return file_path


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

    command_delay = receiver.command_delay
    # Handle if EC position is missing
    ec_position = image.ec_position
    if ec_position == '?':
        ec_position = '.EC_XX'
    missing_packets = image.get_missing_packets()

    # Start of the Yamcs command stack
    data = '''{
  "$schema": "https://yamcs.org/schema/command-stack.schema.json",
  "advancement": {
    "wait": 0
  },
  "commands": [\n'''

    # Add a section of parameters per missing packet
    for i, packet in enumerate(missing_packets):
        data = data + '''    {
      "namespace": "MDB:OPS Name",
      "name": "Biolab_Cmd_EC_Send_Message",
      "arguments": [
        {
          "name": "timeTag_0xYYYYMMDD",
          "value": "-1"
        },
        {
          "name": "timeTag_0xhhmmss00",
          "value": "-1"
        },
        {
          "name": "ECName",
          "value": "'''
        data = data + ec_position
        data = data + '''"
        },
        {
          "name": "dataInFile",
          "value": "0"
        },
        {
          "name": "returnAnswer",
          "value": "0"
        },
        {
          "name": "recordAnswerTo",
          "value": "0"
        },
        {
          "name": "data",
          "value": "40F3'''
        data = data + f'{((image.memory_slot << 12) + packet):04X}'
        data = data + '''"\n        },
        {
          "name": "ph-ack-acceptance",
          "value": "True"
        },
        {
          "name": "ph-ack-exec-start",
          "value": "True"
        }
      ],
      "advancement": {\n'''
        data = data + f'        "wait": {command_delay}\n'
        data = data + '''      }
    }'''

        if len(missing_packets)-1 != i:
            data = data + ','
        data = data + '\n'

    # End of the command stack
    data = data + '''  ]
}'''

    file_path = (receiver.comm_path + f"{ec_position[1:]}_{image.ec_address}_m{image.memory_slot}_" +
                 image.last_update.strftime('%Y-%m-%d_%H%M%S') + ".ycs")

    try:
        with open(file_path, 'w') as file:
            file.write(data)
            logging.info("Created Yamcs command stack for %s %i m%i with %i missing packets: %s",
                         ec_position, image.ec_address, image.memory_slot, len(missing_packets),
                         file_path)
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
            if not os.path.exists(output_path):
                os.mkdir(output_path)
            os.mkdir(date_path)

        successful_write = False

        # Ignore if there is no update on the image
        if not image.update:
            continue

        # Get number of packets associated with this image
        image.total_packets = receiver.database.get_image_packet_number(image.uuid)

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
            image.image_transmission_active = False
            if image.latest_saved_file is None or image.latest_saved_file[-7:-4] != '100':
                receiver.total_completed_images = receiver.total_completed_images + 1

        if image.latest_saved_file is None:  # Only after the initial image transmission
            # Count lost packets
            receiver.total_lost_packets = (receiver.total_lost_packets +
                                           len(image.get_missing_packets(True)))

            if len(missing_packets) > 0:
                # Create command stack for missing packets
                create_command_stack(image, receiver)

        # Print detailed image information
        logging.info(image)

        written_image_file_path = None
        written_image_tm_file_path = None
        written_image_data_file_path = None

        # Handle if EC position is missing
        position = image.ec_position
        if position == '?':
            position = '.EC_XX'

        # File anme base for any file type
        file_path_base = date_path + position[1:] + '_' + image.image_name[3:] + image_percentage

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
            file_path = file_path_base + '.jpg'

            written_image_file_path = write_file(image_data, file_path, 'wb', gui)

            if written_image_file_path is not None:
                successful_write = True
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
            file_path_tm = file_path_base + '_tm.txt'

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

            written_image_tm_file_path = write_file(tm_image_data,
                                                    file_path_tm,
                                                    'w',
                                                    gui)

            # FLIR Image data is converted to .csv file
            file_path_csv = file_path_base + '_data.csv'

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

            written_image_data_file_path = write_file(csv_image_data,
                                                      file_path_csv,
                                                      'w',
                                                      gui)

            # FLIR Image data is converted is saved as .bmp file
            file_path = file_path_base + '.bmp'

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

            written_image_file_path = write_file(bmp_data, file_path, 'wb', gui)

            if (written_image_file_path is not None and
                    written_image_tm_file_path is not None and
                    written_image_data_file_path is not None):
                successful_write = True
            if image.is_complete() and successful_write:
                finished_images.append(index)

        # On a successful file write note that there are not more updates
        if successful_write:
            image.update = False

            # Since the file write was successful,
            # remove previous versions of the files
            try:
                if (image.latest_saved_file != written_image_file_path and
                        image.latest_saved_file is not None and
                        os.path.exists(image.latest_saved_file)):
                    os.remove(image.latest_saved_file)
                    logging.info('Removed previous version of file %s',
                                 image.latest_saved_file)

                if (image.latest_saved_file_tm != written_image_tm_file_path and
                        image.latest_saved_file_tm is not None and
                        os.path.exists(image.latest_saved_file_tm)):
                    os.remove(image.latest_saved_file_tm)
                    logging.info('Removed previous version of file %s',
                                 image.latest_saved_file_tm)

                if (image.latest_saved_file_data != written_image_data_file_path and
                        image.latest_saved_file_data is not None and
                        os.path.exists(image.latest_saved_file_data)):
                    os.remove(image.latest_saved_file_data)
                    logging.info('Removed previous version of file %s',
                                 image.latest_saved_file_data)

            except IOError:
                logging.info('Could not remove some of the old file versions')
                pass

            # And note the latest written down file
            image.latest_saved_file = written_image_file_path
            if image.camera_type == "FLIR":
                image.latest_saved_file_tm = written_image_tm_file_path
                image.latest_saved_file_data = written_image_data_file_path

        # Update gui if available
        if gui:
            gui.update_image_data(image)
            gui.update_stats()

        # Update image in database
        image.update = False
        receiver.database.update_image_status(image)
        receiver.database.update_image_filenames(image)

    # Remove fully complete and written down images from the incomplete list
    if len(finished_images) > 0:
        for index in finished_images[::-1]:
            receiver.database.update_image_status(images[index])
            images.pop(index)

    return images
