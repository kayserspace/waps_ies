"""
Script: read_database.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: WAPS Image Extraction Software
         List the packets of the database
Version: 2023-05-25 15:00, version 1.0

Change Log:
2023-05-25 v 1.0
 - release
"""

from argparse import ArgumentParser
import sqlite3
from datetime import datetime

database_image_table = ("image_uuid, " +
                        "acquisition_time, " +
                        "CCSDS_time, " +
                        "time_tag, " +
                        "image_name, " +
                        "camera_type, " +
                        "ec_address, " +
                        "ec_position, " +
                        "memory_slot, " +
                        "number_of_packets, " +
                        "good_packets, " +
                        "overwritten, " +
                        "outdated, " +
                        "transmission_active, " +
                        "image_update, " +
                        "latest_image_file, " +
                        "latest_data_file, " +
                        "latest_tm_file, " +
                        "last_update, " +
                        "missing_packets")

database_packet_table = ("packet_uuid, " +
                         "acquisition_time, " +
                         "CCSDS_time, " +
                         "data, " +
                         "time_tag, " +
                         "packet_name, " +
                         "ec_address, " +
                         "generic_tm_id, " +
                         "generic_tm_type, " +
                         "generic_tm_length, " +
                         "image_memory_slot, " +
                         "tm_packet_id, " +
                         "image_number_of_packets, " +
                         "data_packet_id, " +
                         "data_packet_crc, " +
                         "data_packet_size, " +
                         "data_packet_verify_code, " +
                         "good_packet, " +
                         "image_id")

# Define command line arguments
parser = ArgumentParser(description='This script lists the packets contained in the database')

parser.add_argument("-db", "--database", dest="database_file", default="waps_pd.db",
                    help="Specifies the database file. Default: waps_pd.db")
parser.add_argument("-ea", "--ec_address", dest="ec_address", default=None,
                    help="Specifies the EC address (0-255)")
parser.add_argument("-ms", "--memory_slot", dest="memory_slot", default=None,
                    help="Specifies the memory slot (0-7)")
parser.add_argument("-lp", "--list_packets", action="store_true",
                    help="Show the list of packets")
parser.add_argument("-csv", "--csv_export", action="store_true",
                    help="Export the packet list to .CSV file with the same name as the database file")
args = parser.parse_args()

# Open database
db = sqlite3.connect(args.database_file)
cur = db.cursor()

# Additional parameters
parameters = ""
if args.ec_address is not None and args.memory_slot is not None:
    parameters = f"WHERE ec_address={args.ec_address} AND memory_slot={args.memory_slot}"
elif args.ec_address is not None:
    parameters = f"WHERE ec_address={args.ec_address}"
elif args.memory_slot is not None:
    parameters = f"WHERE memory_slot={args.memory_slot}"

res = cur.execute("SELECT packet_uuid FROM packets")
packet_number = len(res.fetchall())
res = cur.execute("SELECT image_uuid FROM images")
image_number = len(res.fetchall())
total_packet_count = 0

# Get images from the database
res = cur.execute("SELECT * FROM images " + parameters + " ORDER BY CCSDS_time ASC")
images = res.fetchall()

print('Database contains:')
data = ''
for image in images:
    res = cur.execute("SELECT * FROM packets WHERE image_id=? ORDER BY CCSDS_time ASC",
                      [image[0]])
    packets = res.fetchall()
    total_packet_count = total_packet_count + len(packets)
    print(f'Image {image[4]} with UUID: {image[0]}')
    print(f'\t\t Completion: {image[10]}/{image[9]}')
    print(f'\t\t Total packets in database {len(packets)}')
    if args.csv_export:
        data = data + f'Image, {len(packets)}, '
        for item in image:
            data = data + str(item).replace(',', ';') + ', '
        data = data + '\n'
    if args.list_packets:
        for packet in packets:
            print(f"Packet CCSDS time {packet[2]} with UUID: {packet[0]}")
            if args.csv_export:
                data = data + 'Packet, '
                for item in packet:
                    data = data + str(item).replace(',', ';') + ', '
                data = data + '\n'

# Get the unassigned packets too
if args.ec_address is None and args.memory_slot is None:
    res = cur.execute("SELECT * FROM packets WHERE image_id=? ORDER BY CCSDS_time ASC", [-1])
    unassigned_packets = res.fetchall()
    total_packet_count = total_packet_count + len(unassigned_packets)
    print('Packets with no image assigned:', len(unassigned_packets))
    data = data + f'No image, {len(unassigned_packets)},\n'
    if args.list_packets:
        for unassigned_packet in unassigned_packets:
            print(f"Packet CCSDS time {unassigned_packet[2]} with UUID: {unassigned_packet[0]}")
            data = data + f'No image, {len(unassigned_packets)}, '
            for item in unassigned_packet:
                data = data + str(item).replace(',', ';') + ', '
            data = data + '\n'
db.close()

print('Total image count:', len(images), '/', image_number)
print('Total packet count:', total_packet_count, '/', packet_number)

if args.csv_export:
    # CSV file data initialization
    csv_file_name = (args.database_file[:-3] + " " +
                     datetime.now().strftime('%Y%m%d_%H%M%S') + "_export.csv")
    csv_data = ('Database exported ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S") +
                ' from args.database_file\n')
    if args.ec_address is not None:
        csv_data = csv_data + f"EC address: {args.ec_address}\n"
    if args.memory_slot is not None:
        csv_data = csv_data + f"Memory slot: {args.memory_slot}\n"
    csv_data = csv_data + f'Total number of of images: {len(images)}/{image_number}\n'
    csv_data = csv_data + f'Total number of packets: {total_packet_count}/{packet_number}\n'
    csv_data = csv_data + "Image header,," + database_image_table + '\n'
    csv_data = csv_data + "Packet header,," + database_packet_table + '\n'

    csv_data = csv_data + data
    try:
        with open(csv_file_name, 'w') as file:
            file.write(csv_data)
            print("\nExport database to", csv_file_name)

    except IOError:
        print('\nCould not open file for writing:', csv_file_name)
