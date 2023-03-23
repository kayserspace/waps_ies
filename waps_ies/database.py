#!/usr/bin/env python

# Script: database.py
# Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
# Purpose: WAPS PD image extraction software for operations at MUSC
#          Database access class
# Version: 2023-03-23 12:00, version 0.1
#
# Change Log:
#  2023-03-23 version 0.1
#  - initial version, file based
#  - prototype stage

import os
import logging
import sqlite3

class WAPS_Database:
    """
    TCP Receiver class

    Attributes
    ----------

    Methods
    -------

    """
    
    def __init__(self, database_filename='waps_pd.db'):

        # Database initialization
        if (not os.path.exists(database_filename)):
            logging.warning("Database seems to be missing path does not exist. Creating it...")
        self.database = sqlite3.connect(database_filename)
        self.db_cursor = self.database.cursor()
        logging.info(" # Opened database " + database_filename)

        # Check database tables
        db_request = self.db_cursor.execute("SELECT name FROM sqlite_master")
        db_tables = db_request.fetchall()
        
        if (not ('packet',) in db_tables):
            logging.debug("Adding packet table to db")
            packet_table_contents = ("CREATE TABLE packet(" +
                                    "packet_uuid, " +
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
                                    "image_id)")
            self.db_cursor.execute(packet_table_contents)

        if (not ('image',) in db_tables):
            logging.debug("Adding image table to db")
            image_table_contents = ("CREATE TABLE image(" +
                                    "image_uuid, " +
                                    "acquisition_time, " +
                                    "CCSDS_time, " +
                                    "time_tag, " +
                                    "image_name, " +
                                    "camera_type, " +
                                    "ec_address, " +
                                    "ec_position, " +
                                    "memory_slot, " +
                                    "number_of_packets, " +
                                    "received_packets, " +
                                    "overwritten, " +
                                    "outdated, " +
                                    "transmission_active, " +
                                    "image_update, " +
                                    "latest_image_file, " +
                                    "latest_data_file, " +
                                    "latest_tm_file, " +
                                    "finalization_time)")
            self.db_cursor.execute(image_table_contents)


    def add_packet(self, packet):
        """ Add packet to database, if not present already """

        #TODO check for duplicate

        packet_data =   [(packet.uuid,
                        packet.acquisition_time,
                        packet.CCSDS_time,
                        packet.data,
                        packet.time_tag,
                        packet.packet_name,
                        packet.ec_address,
                        packet.generic_tm_id,
                        packet.generic_tm_type,
                        packet.generic_tm_length,
                        packet.image_memory_slot,
                        packet.tm_packet_id,
                        packet.image_number_of_packets,
                        packet.data_packet_id,
                        packet.data_packet_crc,
                        packet.data_packet_size,
                        packet.data_packet_verify_code,
                        packet.is_good_waps_image_packet(),
                        "Unknown"),
                        ]
        packet_param = "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.db_cursor.executemany("INSERT INTO packet VALUES" + packet_param, packet_data)
        self.database.commit()


    def add_image(self, image):
        """ Add image to database, if not present already """

        #TODO check for duplicate

        image_data =    [(image.uuid,
                        image.acquisition_time,
                        image.CCSDS_time,
                        image.time_tag,
                        image.image_name,
                        image.camera_type,
                        image.ec_address,
                        image.ec_position,
                        image.memory_slot,
                        image.number_of_packets,
                        len(image.packets),
                        image.overwritten,
                        image.outdated,
                        image.image_transmission_active,
                        image.update,
                        image.latest_saved_file,
                        image.latest_saved_file_data,
                        image.latest_saved_file_tm,
                        'Unknown'),
                        ]
        image_param = "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.db_cursor.executemany("INSERT INTO image VALUES" + image_param, image_data)
        self.database.commit()

    def update_packet(self, packet, image_uuid):

        print ("update packet's image uuid")