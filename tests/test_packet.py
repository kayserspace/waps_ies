

import unittest
from waps_ies import waps_packet
import datetime

class TestPacket(unittest.TestCase):

    def test_uCAM_init_packet(self):
        """ Create and test a uCAM init packet"""

        packet_data = b'@}\xab\x01\x00qa\xa4\xf1\xe2\x03\xbe\x02o\t\x7f\x03y\x08\x00\x05\xc4\x05\xc9\r\x16\x00\t\x03L\x0c\x9e\x08g\x00\x01\x00\x01\x00\x02\x00\x03\x02\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Q\x00`\x00\x00\x02\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        packet = waps_packet.BIOLAB_Packet(datetime.datetime(2023, 3, 29, 14, 11, 54, 100000),
                                            datetime.datetime(2023, 3, 29, 14, 11, 54, 200000),
                                            packet_data)

        # Check contents
        self.assertEqual(str(packet.acquisition_time), '2023-03-29 14:11:54.200000')
        self.assertEqual(str(packet.CCSDS_time), '2023-03-29 14:11:54.100000')
        self.assertEqual(packet.data, packet_data)

        self.assertEqual(packet.ec_address, 171)
        self.assertEqual(packet.time_tag, 7430564)
        self.assertEqual(packet.generic_tm_id, 0x5100)
        self.assertEqual(packet.generic_tm_type, 0x6000)
        self.assertEqual(packet.generic_tm_length, 2)
        self.assertEqual(packet.image_memory_slot, 6)
        self.assertEqual(packet.tm_packet_id, 0)
        self.assertEqual(packet.packet_name, "pkt_ec_171_m6_20230329_141154_7430564")

        self.assertTrue(packet.is_waps_image_packet)

        # Init packet
        self.assertEqual(packet.image_number_of_packets, 33)
        # FLIR or uCAM data packet
        self.assertEqual(packet.data_packet_id, -1)
        # FLIR data packet
        self.assertEqual(packet.data_packet_crc, -1)
        # uCAM data packet
        self.assertEqual(packet.data_packet_size, -1)
        self.assertEqual(packet.data_packet_verify_code, -1)

        # All BIOLAB telemetry
        self.assertEqual(packet.biolab_current_image_memory_slot, 0)

        self.assertTrue(packet.in_spec())
        self.assertTrue(packet.is_good_waps_image_packet())

    def test_uCAM_data_packet(self):
        """ Create and test a uCAM data packet"""

        packet_data = b'@}\xab\x01\x00q\x88\xb4\xf1\xf5\x03\xbc\x02m\tx\x03\x80\x07\xfe\x04\xd7\x05\xc0\r\x17\x00\x0b\x03N\x0c\x9c\x08f\x00\x02\x00\x02\x00\x02\x00\x02\x03\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00R\x00`\x00\x00\xa4\x00\x01\x00\x9e\xff\xd8\xff\xdb\x00\x84\x00\r\t\t\x0b\n\x08\r\x0b\n\x0b\x0e\x0e\r\x0f\x13 \x15\x13\x12\x12\x13\'\x1c\x1e\x17 .)10.)-,3:J>36F7,-@WAFLNRSR2>ZaZP`JQRO\x01\x0e\x0e\x0e\x13\x11\x13&\x15\x15&O5-5OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO\xff\xc4\x01\xa2\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\xf9\x00'
        packet = waps_packet.BIOLAB_Packet(datetime.datetime(2023, 3, 29, 14, 11, 54, 300000),
                                            datetime.datetime(2023, 3, 29, 14, 11, 54, 400000),
                                            packet_data)

        # Check contents
        self.assertEqual(str(packet.acquisition_time), '2023-03-29 14:11:54.400000')
        self.assertEqual(str(packet.CCSDS_time), '2023-03-29 14:11:54.300000')
        self.assertEqual(packet.data, packet_data)

        self.assertEqual(packet.ec_address, 171)
        self.assertEqual(packet.time_tag, 7440564)
        self.assertEqual(packet.generic_tm_id, 0x5200)
        self.assertEqual(packet.generic_tm_type, 0x6000)
        self.assertEqual(packet.generic_tm_length, 164)
        self.assertEqual(packet.image_memory_slot, 6)
        self.assertEqual(packet.tm_packet_id, 0)
        self.assertEqual(packet.packet_name, "pkt_ec_171_m6_20230329_141154_7440564")

        self.assertTrue(packet.is_waps_image_packet)

        # Init packet
        self.assertEqual(packet.image_number_of_packets, -1)
        # FLIR or uCAM data packet
        self.assertEqual(packet.data_packet_id, 1)
        # FLIR data packet
        self.assertEqual(packet.data_packet_crc, -1)
        # uCAM data packet
        self.assertEqual(packet.data_packet_size, 158)
        self.assertEqual(packet.data_packet_verify_code, 63744)

        # All BIOLAB telemetry
        self.assertEqual(packet.biolab_current_image_memory_slot, 0)

        self.assertTrue(packet.in_spec())
        self.assertTrue(packet.is_good_waps_image_packet())

    def test_FLIR_init_packet(self):
        """ Create and test a FLIR init packet"""

        packet_data = b'@}\xab\x01\x00\xd5\xe7\xa9@\x00\x03\xba\x02n\ts\x03t\x07\xfe\x04J\x05\xb1\r\x16\x00\n\x03M\x0c\xdf\x08\x10\x00\x00\x00\x03\x00\x01\x00\x01\x03\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00A\x00\x00\x00\x00\x02\x00?\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        packet = waps_packet.BIOLAB_Packet(datetime.datetime(2023, 3, 29, 14, 11, 54, 500000),
                                            datetime.datetime(2023, 3, 29, 14, 11, 54, 600000),
                                            packet_data)

        # Check contents
        self.assertEqual(str(packet.acquisition_time), '2023-03-29 14:11:54.600000')
        self.assertEqual(str(packet.CCSDS_time), '2023-03-29 14:11:54.500000')
        self.assertEqual(packet.data, packet_data)

        self.assertEqual(packet.ec_address, 171)
        self.assertEqual(packet.time_tag, 14018473)
        self.assertEqual(packet.generic_tm_id, 0x4100)
        self.assertEqual(packet.generic_tm_type, 0x0)
        self.assertEqual(packet.generic_tm_length, 2)
        self.assertEqual(packet.image_memory_slot, 0)
        self.assertEqual(packet.tm_packet_id, 0)
        self.assertEqual(packet.packet_name, "pkt_ec_171_m0_20230329_141154_14018473")

        self.assertTrue(packet.is_waps_image_packet)

        # Init packet
        self.assertEqual(packet.image_number_of_packets, 63)
        # FLIR or uCAM data packet
        self.assertEqual(packet.data_packet_id, -1)
        # FLIR data packet
        self.assertEqual(packet.data_packet_crc, -1)
        # uCAM data packet
        self.assertEqual(packet.data_packet_size, -1)
        self.assertEqual(packet.data_packet_verify_code, -1)

        # All BIOLAB telemetry
        self.assertEqual(packet.biolab_current_image_memory_slot, 0)

        self.assertTrue(packet.in_spec())
        self.assertTrue(packet.is_good_waps_image_packet())

    def test_FLIR_data_packet(self):
        """ Create and test a FLIR data packet"""

        packet_data = b'@}\xab\x01\x00\xd5\xeb\x90\xf1\xf5\x03\xb9\x02l\ts\x03t\x07\xfd\x04H\x05\xb8\r\x15\x00\x0b\x03N\x0c\xd1\x08\x0f\x00\x00\x00\x03\x00\x02\x00\x03\x03\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00B\x00\x00\x00\x00\xa4\x00\x00\xdd\xa0\x00\x0e\r/\x00\xd6\x080\x00\x00a\x10\x82\x08j\xa6\xb0\x9a\n\x89\x06\xfc$\x00\x00\x00\x00 \x00\x01\x00 \x00\x01\x04M\x00\x00\x00\x00\x8c\x99\x00\x05w~\x17\xcav|#\x9ev1\x00\x00u0vn:\xd6\x00\xd5v)\x00\x00\x00\x00\x00\x00\x00O\x00;\x12\xc0\x02\x00\x00\x01\x00\x80\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x80\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1e\x00\x00\x00\x01\x00\x01\x00N\x00:\x00\x07\x006\x00\x12\x00\xd2\x006\x00\x1b\x00\x0c\x00\x0c\x00\x00\x00\x00\x00\x07\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        packet = waps_packet.BIOLAB_Packet(datetime.datetime(2023, 3, 29, 14, 11, 54, 700000),
                                            datetime.datetime(2023, 3, 29, 14, 11, 54, 800000),
                                            packet_data)

        # Check contents
        self.assertEqual(str(packet.acquisition_time), '2023-03-29 14:11:54.800000')
        self.assertEqual(str(packet.CCSDS_time), '2023-03-29 14:11:54.700000')
        self.assertEqual(packet.data, packet_data)

        self.assertEqual(packet.ec_address, 171)
        self.assertEqual(packet.time_tag, 14019472)
        self.assertEqual(packet.generic_tm_id, 0x4200)
        self.assertEqual(packet.generic_tm_type, 0x0)
        self.assertEqual(packet.generic_tm_length, 164)
        self.assertEqual(packet.image_memory_slot, 0)
        self.assertEqual(packet.tm_packet_id, 0)
        self.assertEqual(packet.packet_name, "pkt_ec_171_m0_20230329_141154_14019472")

        self.assertTrue(packet.is_waps_image_packet)

        # Init packet
        self.assertEqual(packet.image_number_of_packets, -1)
        # FLIR or uCAM data packet
        self.assertEqual(packet.data_packet_id, 0)
        # FLIR data packet
        self.assertEqual(packet.data_packet_crc, 56736)
        # uCAM data packet
        self.assertEqual(packet.data_packet_size, -1)
        self.assertEqual(packet.data_packet_verify_code, -1)

        # All BIOLAB telemetry
        self.assertEqual(packet.biolab_current_image_memory_slot, 0)

        self.assertTrue(packet.in_spec())
        self.assertTrue(packet.is_good_waps_image_packet())

    def test_other_BIOLAB_TM_packet(self):
        """ Create and test generic BIOLAB telemetry packet"""

        packet_data = b'@}\xab\x01\x00qa\xa4\xf1\xe2\x03\xbe\x02o\t\x7f\x03y\x08\x00\x05\xc4\x05\xc9\r\x16\x00\t\x03L\x0c\x9e\x08g\x00\x01\x00\x01\x00\x02\x00\x03\x02\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF\x00`\x00\x00\x02\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        packet = waps_packet.BIOLAB_Packet(datetime.datetime(2023, 3, 29, 14, 11, 54, 900000),
                                            datetime.datetime(2023, 3, 29, 14, 11, 54, 990000),
                                            packet_data)

        # Check contents
        self.assertEqual(str(packet.acquisition_time), '2023-03-29 14:11:54.990000')
        self.assertEqual(str(packet.CCSDS_time), '2023-03-29 14:11:54.900000')
        self.assertEqual(packet.data, packet_data)

        self.assertEqual(packet.ec_address, 171)
        self.assertEqual(packet.time_tag, 7430564)
        self.assertEqual(packet.generic_tm_id, 0xFF00)
        self.assertEqual(packet.generic_tm_type, 0x6000)
        self.assertEqual(packet.generic_tm_length, 2)
        self.assertEqual(packet.image_memory_slot, 6)
        self.assertEqual(packet.tm_packet_id, 0)
        self.assertEqual(packet.packet_name, "pkt_ec_171_m6_20230329_141154_7430564")

        self.assertFalse(packet.is_waps_image_packet)

        # Init packet
        self.assertEqual(packet.image_number_of_packets, -1)
        # FLIR or uCAM data packet
        self.assertEqual(packet.data_packet_id, -1)
        # FLIR data packet
        self.assertEqual(packet.data_packet_crc, -1)
        # uCAM data packet
        self.assertEqual(packet.data_packet_size, -1)
        self.assertEqual(packet.data_packet_verify_code, -1)

        # All BIOLAB telemetry
        self.assertEqual(packet.biolab_current_image_memory_slot, 0)

        self.assertTrue(packet.in_spec())
        self.assertFalse(packet.is_good_waps_image_packet())

    def test_wrong_packet_length(self):
        """ Create and test packet with wrong length of data"""

        packet_data = b'@}\xab\x01\x00qa\xa4\xf1\xe2\x03\xbe\x02o\t\x7f\x03y\x08\x00\x05\xc4\x05\xc9\r\x16\x00\t\x03L\x0c\x9e\x08g\x00\x01\x00\x01\x00\x02\x00\x03\x02\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Q\x00'
        packet = waps_packet.BIOLAB_Packet(datetime.datetime(2023, 3, 29, 14, 11, 54, 110000),
                                            datetime.datetime(2023, 3, 29, 14, 11, 54, 120000),
                                            packet_data)

        # Check contents
        self.assertEqual(str(packet.acquisition_time), '2023-03-29 14:11:54.120000')
        self.assertEqual(str(packet.CCSDS_time), '2023-03-29 14:11:54.110000')
        self.assertEqual(packet.data, packet_data)

        with self.assertRaises(AttributeError):
            packet.ec_address

        self.assertFalse(packet.in_spec())
        self.assertFalse(packet.is_good_waps_image_packet())

    def test_FLIR_bad_packet(self):
        """ Create and test a wrong FLIR packet"""

        class Receiver:
            total_corrupted_packets = 0


        packet_data = b'@}\xab\x01\x00\xd5\xeb\x90\xf1\xf5\x03\xb9\x02l\ts\x03t\x07\xfd\x04H\x05\xb8\r\x15\x00\x0b\x03N\x0c\xd1\x08\x0f\x00\x00\x00\x03\x00\x02\x00\x03\x03\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00B\x00\x00\x00\x00\xa4\x00\x00\xdd\xa0\x00\x0e\r/\x00\xd6\x080\x00\x00a\x10\x82\x08j\xa6\xb0\x9a\n\x89\x06\xfc$\x00\x00\x00\x00 \x00\x01\x00 \x00\x01\x04M\x00\x00\x00\x00\x8c\x99\x00\x05w~\x17\xcav|#\x9ev1\x00\x00u0vn:\xd6\x00\xd5v)\x00\x00\x00\x00\x00\x00\x00O\x00;\x12\xc0\x02\x00\x00\x01\x00\x80\x00@\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x80\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1e\x00\x00\x00\x01\x00\x01\x00N\x00:\x00\x07\x006\x00\x12\x00\xd2\x006\x00\x1b\x00\x0c\x00\x0c\x00\x00\x00\x00\x00\x07\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        packet = waps_packet.BIOLAB_Packet(datetime.datetime(2023, 3, 29, 14, 11, 54, 700000),
                                            datetime.datetime(2023, 3, 29, 14, 11, 54, 800000),
                                            packet_data,
                                            Receiver())

        packet.data_packet_crc = 56735
        self.assertFalse(packet.is_good_waps_image_packet())
        packet.data_packet_crc = 56736
        self.assertTrue(packet.is_good_waps_image_packet())

        packet.tm_packet_id = -1
        self.assertFalse(packet.is_good_waps_image_packet())
        packet.tm_packet_id = 0
        self.assertTrue(packet.is_good_waps_image_packet())

        packet.image_memory_slot = -1
        self.assertFalse(packet.is_good_waps_image_packet())
        packet.image_memory_slot = 8
        self.assertFalse(packet.is_good_waps_image_packet())
        packet.image_memory_slot = 0
        self.assertTrue(packet.is_good_waps_image_packet())

        packet.data = packet.data[:200]
        self.assertFalse(packet.is_good_waps_image_packet())


    def test_uCAM_bad_packet(self):
        """ Create and test a wrong uCAM packet"""

        class Receiver:
            total_corrupted_packets = 0

        packet_data = b'@}\xab\x01\x00q\x88\xb4\xf1\xf5\x03\xbc\x02m\tx\x03\x80\x07\xfe\x04\xd7\x05\xc0\r\x17\x00\x0b\x03N\x0c\x9c\x08f\x00\x02\x00\x02\x00\x02\x00\x02\x03\x02`\x00\x00 \x00 \xff"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00R\x00`\x00\x00\xa4\x00\x01\x00\x9e\xff\xd8\xff\xdb\x00\x84\x00\r\t\t\x0b\n\x08\r\x0b\n\x0b\x0e\x0e\r\x0f\x13 \x15\x13\x12\x12\x13\'\x1c\x1e\x17 .)10.)-,3:J>36F7,-@WAFLNRSR2>ZaZP`JQRO\x01\x0e\x0e\x0e\x13\x11\x13&\x15\x15&O5-5OOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOO\xff\xc4\x01\xa2\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\xf9\x00'
        packet = waps_packet.BIOLAB_Packet(datetime.datetime(2023, 3, 29, 14, 11, 54, 300000),
                                            datetime.datetime(2023, 3, 29, 14, 11, 54, 400000),
                                            packet_data,
                                            Receiver())


        packet.data_packet_verify_code = 63743
        self.assertFalse(packet.is_good_waps_image_packet())
        packet.data_packet_verify_code = 63744
        self.assertTrue(packet.is_good_waps_image_packet())

        packet.tm_packet_id = -1
        self.assertFalse(packet.is_good_waps_image_packet())
        packet.tm_packet_id = 0
        self.assertTrue(packet.is_good_waps_image_packet())

        packet.image_memory_slot = -1
        self.assertFalse(packet.is_good_waps_image_packet())
        packet.image_memory_slot = 8
        self.assertFalse(packet.is_good_waps_image_packet())
        packet.image_memory_slot = 0
        self.assertTrue(packet.is_good_waps_image_packet())

        packet.data = packet.data[:200]
        self.assertFalse(packet.is_good_waps_image_packet())

if __name__ == '__main__':
    unittest.main()