#!/usr/bin/env python

# Script: test_processor.py
# Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
# Purpose: Unit test for waps_ies.processor module
# Version: 2023-04-05 17:00, version 0.1

import unittest
import waps_ies.receiver
import waps_ies.file_reader
import waps_ies.processor
import waps_ies.waps_packet
import datetime
import os

class TestProcessor(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        self.receiver = waps_ies.receiver.Receiver("192.168.0.1",
                                                   12345,
                                                   "tests/output/",
                                                    database_filename='tests/waps_pd.db')
        if (not os.path.exists("tests/output/") or
            not os.path.isdir("tests/output/")):
            os.mkdir("tests/output/")
        self.receiver.database

    def test_different_ec_addresses(self):
        """ Test adding packets with different EC addresses """

        packet_list = []
        # Image initialization packets
        packet_data = b'@}\xab\x01\x00qa\xa4\xf1\xe2\x03\xbe\x02o\t\x7f\x03y\x08\x00\x05\xc4\x05\xc9\r\x16\x00\t\x03L\x0c\x9e\x08g\x00\x01\x00\x01\x00\x02\x00\x03\x02\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Q\x00`\x00\x00\x02\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        packet_list.append(waps_ies.waps_packet.WapsPacket(datetime.datetime(2022, 3, 29, 14, 11, 54, 0),
                                                     datetime.datetime(2022, 3, 29, 14, 11, 54, 1),
                                                     packet_data))
        packet_data = b'@}\xac\x01\x00qa\xa4\xf1\xe2\x03\xbe\x02o\t\x7f\x03y\x08\x00\x05\xc4\x05\xc9\r\x16\x00\t\x03L\x0c\x9e\x08g\x00\x01\x00\x01\x00\x02\x00\x03\x02\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Q\x00`\x00\x00\x02\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        packet_list.append(waps_ies.waps_packet.WapsPacket(datetime.datetime(2022, 3, 29, 14, 11, 54, 2),
                                                     datetime.datetime(2022, 3, 29, 14, 11, 54, 3),
                                                     packet_data))
        packet_data = b'@}\xad\x01\x00qa\xa4\xf1\xe2\x03\xbe\x02o\t\x7f\x03y\x08\x00\x05\xc4\x05\xc9\r\x16\x00\t\x03L\x0c\x9e\x08g\x00\x01\x00\x01\x00\x02\x00\x03\x02\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Q\x00`\x00\x00\x02\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        packet_list.append(waps_ies.waps_packet.WapsPacket(datetime.datetime(2022, 3, 29, 14, 11, 54, 4),
                                                     datetime.datetime(2022, 3, 29, 14, 11, 54, 5),
                                                     packet_data))
        packet_data = b'@}\xae\x01\x00qa\xa4\xf1\xe2\x03\xbe\x02o\t\x7f\x03y\x08\x00\x05\xc4\x05\xc9\r\x16\x00\t\x03L\x0c\x9e\x08g\x00\x01\x00\x01\x00\x02\x00\x03\x02\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Q\x00`\x00\x00\x02\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        packet_list.append(waps_ies.waps_packet.WapsPacket(datetime.datetime(2022, 3, 29, 14, 11, 54, 6),
                                                     datetime.datetime(2022, 3, 29, 14, 11, 54, 7),
                                                     packet_data))
        packet_data = b'@}\xaf\x01\x00qa\xa4\xf1\xe2\x03\xbe\x02o\t\x7f\x03y\x08\x00\x05\xc4\x05\xc9\r\x16\x00\t\x03L\x0c\x9e\x08g\x00\x01\x00\x01\x00\x02\x00\x03\x02\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Q\x00`\x00\x00\x02\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        packet_list.append(waps_ies.waps_packet.WapsPacket(datetime.datetime(2022, 3, 29, 14, 11, 54, 8),
                                                     datetime.datetime(2022, 3, 29, 14, 11, 54, 9),
                                                     packet_data))

        # Image data packets
        packet_data = b'@}\xab\x01\x00q\x88\xb4\xf1\xf5\x03\xbc\x02m\tx\x03\x80\x07\xfe\x04\xd7\x05\xc0\r\x17\x00\x0b\x03N\x0c\x9c\x08f\x00\x02\x00\x02\x00\x02\x00\x02\x03\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00R\x00`\x00\x00\xa4\x00\x01\x00\x9e\xff\xd8\xff\xdb\x00\x84\x00\r\t\t\x0b\n\x08\r\x0b\n\x0b\x0e\x0e\r\x0f\x13 \x15\x13\x12\x12\x13\'\x1c\x1e\x17 .)10.)-,3:J>36F7,-@WAFLNRSR2>ZaZP`JQRO\x01\x0e\x0e\x0e\x13\x11\x13&\x15\x15&O5-5OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO\xff\xc4\x01\xa2\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\xf9\x00'
        packet_list.append(waps_ies.waps_packet.WapsPacket(datetime.datetime(2022, 3, 29, 14, 11, 55, 0),
                                                     datetime.datetime(2022, 3, 29, 14, 11, 55, 1),
                                                     packet_data))
        packet_data = b'@}\xac\x01\x00q\x88\xb4\xf1\xf5\x03\xbc\x02m\tx\x03\x80\x07\xfe\x04\xd7\x05\xc0\r\x17\x00\x0b\x03N\x0c\x9c\x08f\x00\x02\x00\x02\x00\x02\x00\x02\x03\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00R\x00`\x00\x00\xa4\x00\x01\x00\x9e\xff\xd8\xff\xdb\x00\x84\x00\r\t\t\x0b\n\x08\r\x0b\n\x0b\x0e\x0e\r\x0f\x13 \x15\x13\x12\x12\x13\'\x1c\x1e\x17 .)10.)-,3:J>36F7,-@WAFLNRSR2>ZaZP`JQRO\x01\x0e\x0e\x0e\x13\x11\x13&\x15\x15&O5-5OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO\xff\xc4\x01\xa2\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\xf9\x00'
        packet_list.append(waps_ies.waps_packet.WapsPacket(datetime.datetime(2022, 3, 29, 14, 11, 55, 2),
                                                     datetime.datetime(2022, 3, 29, 14, 11, 55, 3),
                                                     packet_data))
        packet_data = b'@}\xad\x01\x00q\x88\xb4\xf1\xf5\x03\xbc\x02m\tx\x03\x80\x07\xfe\x04\xd7\x05\xc0\r\x17\x00\x0b\x03N\x0c\x9c\x08f\x00\x02\x00\x02\x00\x02\x00\x02\x03\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00R\x00`\x00\x00\xa4\x00\x01\x00\x9e\xff\xd8\xff\xdb\x00\x84\x00\r\t\t\x0b\n\x08\r\x0b\n\x0b\x0e\x0e\r\x0f\x13 \x15\x13\x12\x12\x13\'\x1c\x1e\x17 .)10.)-,3:J>36F7,-@WAFLNRSR2>ZaZP`JQRO\x01\x0e\x0e\x0e\x13\x11\x13&\x15\x15&O5-5OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO\xff\xc4\x01\xa2\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\xf9\x00'
        packet_list.append(waps_ies.waps_packet.WapsPacket(datetime.datetime(2022, 3, 29, 14, 11, 55, 4),
                                                     datetime.datetime(2022, 3, 29, 14, 11, 55, 5),
                                                     packet_data))
        packet_data = b'@}\xae\x01\x00q\x88\xb4\xf1\xf5\x03\xbc\x02m\tx\x03\x80\x07\xfe\x04\xd7\x05\xc0\r\x17\x00\x0b\x03N\x0c\x9c\x08f\x00\x02\x00\x02\x00\x02\x00\x02\x03\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00R\x00`\x00\x00\xa4\x00\x01\x00\x9e\xff\xd8\xff\xdb\x00\x84\x00\r\t\t\x0b\n\x08\r\x0b\n\x0b\x0e\x0e\r\x0f\x13 \x15\x13\x12\x12\x13\'\x1c\x1e\x17 .)10.)-,3:J>36F7,-@WAFLNRSR2>ZaZP`JQRO\x01\x0e\x0e\x0e\x13\x11\x13&\x15\x15&O5-5OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO\xff\xc4\x01\xa2\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\xf9\x00'
        packet_list.append(waps_ies.waps_packet.WapsPacket(datetime.datetime(2022, 3, 29, 14, 11, 55, 6),
                                                     datetime.datetime(2022, 3, 29, 14, 11, 55, 7),
                                                     packet_data))
        packet_data = b'@}\xaf\x01\x00q\x88\xb4\xf1\xf5\x03\xbc\x02m\tx\x03\x80\x07\xfe\x04\xd7\x05\xc0\r\x17\x00\x0b\x03N\x0c\x9c\x08f\x00\x02\x00\x02\x00\x02\x00\x02\x03\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00R\x00`\x00\x00\xa4\x00\x01\x00\x9e\xff\xd8\xff\xdb\x00\x84\x00\r\t\t\x0b\n\x08\r\x0b\n\x0b\x0e\x0e\r\x0f\x13 \x15\x13\x12\x12\x13\'\x1c\x1e\x17 .)10.)-,3:J>36F7,-@WAFLNRSR2>ZaZP`JQRO\x01\x0e\x0e\x0e\x13\x11\x13&\x15\x15&O5-5OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO\xff\xc4\x01\xa2\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\xf9\x00'
        packet_list.append(waps_ies.waps_packet.WapsPacket(datetime.datetime(2022, 3, 29, 14, 11, 55, 8),
                                                     datetime.datetime(2022, 3, 29, 14, 11, 55, 9),
                                                     packet_data))

        incomplete_images = []
        self.receiver.incomplete_images = waps_ies.processor.sort_biolab_packets(packet_list, incomplete_images, self.receiver)

        self.assertEqual(len(self.receiver.incomplete_images), 5)
        for image in incomplete_images:
            self.assertEqual(len(image.packets), 1)
            self.assertFalse(image.overwritten)


    def test_bed_data(self):
        """ Get packet list from the test bed output file and test sorting """

        packet_list = waps_ies.file_reader.read_test_bed_file("tests/test_bed_files/EC RAW Data.txt")

        self.assertEqual(len(packet_list), 309)

        incomplete_images = []
        self.receiver.incomplete_images = waps_ies.processor.sort_biolab_packets(packet_list, incomplete_images, self.receiver)

        self.assertEqual(len(self.receiver.incomplete_images), 2)
        flir_image_name = self.receiver.incomplete_images[0].image_name
        ucam_image_name = self.receiver.incomplete_images[1].image_name
        waps_ies.processor.save_images(self.receiver.incomplete_images, 'tests/output/', self.receiver)
        self.assertEqual(len(self.receiver.incomplete_images), 0)

        output_dir = "tests/output/" + datetime.datetime.now().strftime("%Y%m%d") + '/'

        # Compare original to the new JPEG files
        original_file_data = None
        new_file_data = None
        with open("tests/test_bed_files/color_20221024_1052.jpeg", 'rb') as file:
            original_file_data = file.read()
            file.close()
        with open(output_dir+ucam_image_name+"_100.jpg", 'rb') as file:
            new_file_data = file.read()
            file.close()

        # JPEGs are equal except for last packet is not cut as it should be
        # according to specification (12 bytes extra)
        self.assertEqual(new_file_data, original_file_data[:len(new_file_data)])
        self.assertEqual(len(original_file_data) - len(new_file_data), 12)

        # Compare original to the new raw FLIR files
        with open("tests/test_bed_files/ir_20221024_1049_pic.csv", 'rb') as file:
            original_file_data = file.read()
            file.close()
        with open(output_dir+flir_image_name+"_100_data.csv", 'rb') as file:
            new_file_data = file.read()
            file.close()

        self.assertEqual(new_file_data, original_file_data[:len(new_file_data)])

        # Compare original to the new meta FLIR files
        with open("tests/test_bed_files/ir_20221024_1049_tm.txt", 'rb') as file:
            original_file_data = file.read()
            file.close()
        with open(output_dir+flir_image_name+"_100_tm.txt", 'rb') as file:
            new_file_data = file.read()
            file.close()

        self.assertEqual(new_file_data, original_file_data[:len(new_file_data)])

        # Compare original to the new meta FLIR files
        with open("tests/test_bed_files/ir_20221024_1049.bmp", 'rb') as file:
            original_file_data = file.read()
            file.close()
        with open(output_dir+flir_image_name+"_100.bmp", 'rb') as file:
            new_file_data = file.read()
            file.close()

        self.assertEqual(new_file_data, original_file_data[:len(new_file_data)])


if __name__ == '__main__':
    unittest.main()