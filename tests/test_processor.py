#!/usr/bin/env python

# Script: test_processor.py
# Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
# Purpose: Unit test for waps_ies.processor module
# Version: 2023-04-05 17:00, version 0.1

import unittest
import waps_ies.receiver
import waps_ies.file_reader
import waps_ies.processor
import datetime
import os

class TestProcessor(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        self.receiver = waps_ies.receiver.TCP_Receiver("192.168.0.1",
                                                       12345,
                                                       "tests/output/")
        if (not os.path.exists("tests/output/") or
            not os.path.isdir("tests/output/")):
            os.mkdir("tests/output/")

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