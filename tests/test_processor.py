#!/usr/bin/env python

# Script: test_processor.py
# Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
# Purpose: Unit test for waps_ies.processor module
# Version: 2023-04-05 17:00, version 0.1

import unittest
from waps_ies import processor, tcpreceiver, file_reader
import datetime
import os

class TestPacket(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        self.receiver = tcpreceiver.TCP_Receiver("192.168.0.1", 12345, "tests/output/")
        if (not os.path.exists("tests/output/") or
            not os.path.isdir("tests/output/")):
            os.mkdir("tests/output/")

    def test_bed_packet_sorting(self):
        """ Get packet list from the test bed output file and test sorting """

        packet_list = file_reader.read_test_bed_file("tests/test_bed_files/EC RAW Data.txt")

        self.assertEqual(len(packet_list), 309)

        incomplete_images = []
        self.receiver.incomplete_images = processor.sort_biolab_packets(packet_list, incomplete_images, self.receiver)

        self.assertEqual(len(self.receiver.incomplete_images), 2)


    def test_image_saving(self):


        processor.save_images(self.receiver.incomplete_images, 'tests/output/', self.receiver)
        self.assertEqual(len(self.receiver.incomplete_images), 0)



if __name__ == '__main__':
    unittest.main()