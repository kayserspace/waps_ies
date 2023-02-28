# -*- coding: utf-8 -*-

import logging
from datetime import datetime
#import easygui
from waps_ies import tracker, processor

def crc16_ccitt(crc, data):
    msb = crc >> 8
    lsb = crc & 255
    for c in data:
        x = int(c) ^ msb
        x ^= (x >> 4)
        msb = (lsb ^ (x >> 3) ^ (x << 4)) & 255
        lsb = (x ^ (x << 5)) & 255
    return (msb << 8) + lsb

"""
Directly process the telemetry file
"""
if __name__ == "__main__":

    output_path = r'C:\Users\olg\Documents\Local_workspace\waps_ies_testing/output/'
    log_path = r'C:\Users\olg\Documents\Local_workspace\waps_ies_testing/logs/'

    # Set up logging
    log_filename = log_path + 'WAPS_test_bench' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.log'
    logging.basicConfig(filename = log_filename, format='%(asctime)s:%(levelname)s:%(message)s', level=0)
    logging.getLogger().addHandler(logging.StreamHandler())

    #print ('Select the file to process')
    #filepath = easygui.fileopenbox()
    filepath = r'C:\Users\olg\Kayser Space\WAPS - Documents\Incoming Documents\CIRIS\Test bed output files\EC RAW Data.txt'
    # Extract the packets
    packet_list = tracker.process_test_bench(filepath)

    count = 0
    crc = 0
    for packet in packet_list:
        if (packet.data_packet_crc != -1 or packet.data_packet_verify_code != -1):
            crc = crc16_ccitt(0, packet.data[94:])
            print(hex(crc), hex(packet.data_packet_crc), hex(packet.data_packet_verify_code), packet.data_packet_id)
            count = count + 1
        if (count > 5):
            break

    incomplete_images = []
    # Reconstruct the packets into images
    incomplete_images = processor.sort_biolab_packets(packet_list, incomplete_images)

    print("Number of incomplete images:" + str(len(incomplete_images)))

    processor.save_images(incomplete_images, output_path)




