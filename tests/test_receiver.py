

import unittest
import waps_ies.receiver
import time

class TestReceiver(unittest.TestCase):

    @classmethod
    def setUpClass(self):

        self.receiver = waps_ies.receiver.Receiver("192.168.0.1",
                                                   12345,
                                                   "output/",
                                                   database_filename='tests/waps_pd.db')

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