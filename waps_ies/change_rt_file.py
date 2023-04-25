"""
Script: change_rt_file.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: Take rt file(s) and update BIOLAB TM according to arguments
Version: 2023-04-18 14:00, version 0.1

Change Log:
2023-04-18 version 0.1
 - initial version
"""

from argparse import ArgumentParser
import os
import sys
from struct import unpack


def update_rt_file(filepath, ec_address):
    """ Read teh rt file and change its contents """

    contains_waps_image_data = False

    # Read the file
    try:
        with open(filepath, 'rb') as file:
            data = bytearray(file.read())

            ec_address_changes = 0

            # Search the file for packets
            pointer = data.find(b'\x13\x00\x57\x30')  # First packet in the file
            while pointer > -1:

                # Confirm packet by BIOLAB ID
                biolab_id_position = pointer + 28

                # Check BIOLAB ID
                if data[biolab_id_position] == 0x40:  # BIOLAB ID 0x40
                    packet_length = data[biolab_id_position + 1] * 2 + 4

                    # Change EC address in BIOLAB TM packet
                    if ec_address:
                        data[biolab_id_position + 2] = ec_address
                        ec_address_changes = ec_address_changes + 1

                    # Check generic_tm_id
                    generic_tm_id = unpack('>H',
                                           data[biolab_id_position+84:biolab_id_position+86])[0]
                    if generic_tm_id in (0x4100, 0x4200, 0x5100, 0x5200):
                        contains_waps_image_data = True

                    # Find next packet packet
                    pointer = data.find(b'\x13\x00\x57\x30', biolab_id_position + packet_length)

                else:
                    # Find next packet packet
                    pointer = data.find(b'\x13\x00\x57\x30', pointer + 1)

            print(' - EC address changed ', ec_address_changes, "times")

    except IOError:
        print('Could not open file: ' + filepath)

    except IndexError:
        print('Unexpected end of file ', filepath)

    return data, contains_waps_image_data


if __name__ == "__main__":

    # Define command line arguments
    parser = ArgumentParser(description='WAPS Image Extraction Software.' +
                            ' Extra script to take rt file(s) and update' +
                            ' BIOLAB TM according to arguments, making a copy' +
                            ' of this file(s) in a predefined directory')
    parser.add_argument("paths", nargs='+',
                        help="Input path (file(s) or directory(ies))")
    parser.add_argument("-o", "--output", dest="output", default="changed_rt_files/",
                        help="Output directory")
    parser.add_argument("-ea", "--ec_addr", type=int, dest="ec_addr",
                        help="EC address with which to update the file(s)")
    parser.add_argument("-p", "--pattern", dest="pattern", default=".dat",
                        help="File name pattern to use when scanning the directory for RT files")
    parser.add_argument("-wo", "--waps_only", action="store_true",
                        help="Save only files containing WAPS image data")
    args = parser.parse_args()

    # Declare given variables
    print("Number of input files and directories:", len(args.paths))
    if args.ec_addr:
        print("Change to EC address", args.ec_addr)
    print("Output directory:", args.output)
    if args.waps_only:
        print("Save only files containing WAPS image data", args.waps_only)

    # Check that there is something to change actually
    if not args.ec_addr:
        print("Nothing to change")
        sys.exit()

    # Check existence of the output path
    if not os.path.exists(args.output):
        print("Output directory does not exist. Creating...")
        os.makedirs(args.output)

    # Count all changed files
    changed_file_count = 0
    # Iterate through give paths
    for path in args.paths:
        if os.path.isfile(path):
            print("%s is a file", path)
        elif os.path.isdir(path):
            print("%s is a directory", path)

            for root, dirs, files in os.walk(path):
                for filename in files:
                    # Check file name pattern
                    if filename.find(args.pattern.replace('*', '')) == -1:
                        continue

                    # From each file
                    file_path = os.path.join(root, filename)
                    # Get the file contents
                    print(file_path)
                    filedata = update_rt_file(file_path, args.ec_addr)

                    if args.waps_only and not filedata[1]:
                        print("File did not contain any WAPS image data")
                        continue
                    output_file = args.output + "rt_" + str(changed_file_count).zfill(4) + ".dat"
                    with open(output_file, "wb") as outfile:
                        outfile.write(filedata[0])

                    changed_file_count = changed_file_count + 1

        elif not os.path.exists(path):
            print("%s does not exist", path)
        else:
            print("Something went wrong with", path)
