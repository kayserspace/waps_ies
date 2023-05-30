
import os
import shutil
import unittest
import waps_ies.receiver
import time

class TestReceiver(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        waps = {"ip_address": "192.168.1.1",
                "port": "12345",
                "tcp_timeout": '2.1',           # seconds
                "output_path": 'tests/output/',       # directory
                "database_file": 'tests/output/waps_pd.db',  # directory
                "silent_db_creation": '1',      # Silent database creation
                "comm_path": 'tests/output/comms/',           # directory
                "log_path": 'tests/output/log3/',             # directory
                "log_level": 'INFO',            # INFO / DEBUG / WARNING / ERROR
                "gui_enabled": '0',             # Graphical User Interface
                "image_timeout": '0',         # minutes (10h by default)
                "detect_mem_slot": '1',         # False
                "skip_verify_code": '0',
                "version": 'test_processor' }                # Check clour image CRC

        self.receiver = waps_ies.receiver.Receiver(waps)

    @classmethod
    def tearDownClass(self):
        self.receiver.database.database.close()
        del self.receiver

    def test_gui_column_assignment(self):
        """ A receiver and test GUI column assignment """

        receiver=self.receiver

        ec_addr1 = 172
        ec_addr2 = 173
        ec_addr3 = 174
        ec_addr4 = 175
        ec_addr5 = 176

        receiver.get_ec_states_index(ec_addr1)
        receiver.get_ec_states_index(ec_addr2)

        receiver.assign_ec_column(ec_addr1)
        self.assertEqual(receiver.ec_states[receiver.get_ec_states_index(ec_addr1)]["gui_column"], 0)
        receiver.assign_ec_column(ec_addr5)
        self.assertEqual(receiver.ec_states[receiver.get_ec_states_index(ec_addr5)]["gui_column"], 1)
        receiver.assign_ec_column(ec_addr2)
        self.assertEqual(receiver.ec_states[receiver.get_ec_states_index(ec_addr2)]["gui_column"], 2)
        receiver.assign_ec_column(ec_addr3)
        self.assertEqual(receiver.ec_states[receiver.get_ec_states_index(ec_addr3)]["gui_column"], 3)
        receiver.assign_ec_column(ec_addr4)
        self.assertEqual(receiver.ec_states[receiver.get_ec_states_index(ec_addr4)]["gui_column"], None)
        receiver.assign_ec_column(ec_addr1)
        self.assertEqual(receiver.ec_states[receiver.get_ec_states_index(ec_addr1)]["gui_column"], 0)
        receiver.assign_ec_column(ec_addr5)
        self.assertEqual(receiver.ec_states[receiver.get_ec_states_index(ec_addr5)]["gui_column"], 1)
        receiver.assign_ec_column(ec_addr2)
        self.assertEqual(receiver.ec_states[receiver.get_ec_states_index(ec_addr2)]["gui_column"], 2)
        receiver.assign_ec_column(ec_addr3)
        self.assertEqual(receiver.ec_states[receiver.get_ec_states_index(ec_addr3)]["gui_column"], 3)
        receiver.assign_ec_column(ec_addr4)
        self.assertEqual(receiver.ec_states[receiver.get_ec_states_index(ec_addr4)]["gui_column"], None)

if __name__ == '__main__':
    unittest.main()