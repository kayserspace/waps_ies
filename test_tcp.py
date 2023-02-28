# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from waps_ies import tcpreceiver, interface

"""
Directly process the telemetry file
"""
if __name__ == "__main__":

    log_path = r'C:\Workspace_local\WAPS\waps_ies_testing\logs/'

    # Set up logging
    log_filename = log_path + 'WAPS_test_tcp' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.log'
    logging.basicConfig(filename = log_filename, format='%(asctime)s:%(levelname)s:%(message)s', level=0)
    logging.getLogger().addHandler(logging.StreamHandler())

    logging.info("TCP test")
    
    ies = tcpreceiver.TCP_receiver()
    
    logging.info(" # Running graphical interface")
    ies_interface = interface.WAPS_interface(ies)
    ies.add_interface(ies_interface)
    
    ies.start()




