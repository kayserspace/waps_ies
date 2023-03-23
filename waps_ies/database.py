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
        self.database = sqlite3.connect("waps_pd.db")
        self.db_cursor = self.database.cursor()
        logging.info(" # Opened database 'waps_pd.db'")

        # Check database tables
        db_request = self.db_cursor.execute("SELECT name FROM sqlite_master")
        db_tables = db_request.fetchall()
        if (not ('packet',) in db_tables):
            logging.debug("Adding packet table to db")
            self.db_cursor.execute("CREATE TABLE packet(packet_name, ec_address, image_memory_slot, tm_packet_id, image_name)")
        if (not ('image',) in db_tables):
            logging.debug("Adding image table to db")
            self.db_cursor.execute("CREATE TABLE image(image_name, ec_address, memory_slot, number_of_packets)")
        db_request = self.db_cursor.execute("SELECT name FROM sqlite_master")
        db_tables = db_request.fetchall()


    def add_packet(self, packet):
        """ Add packet to database, if not present already """

        #TODO check for duplicate

        packet_data =   [(packet.packet_name,
                        packet.ec_address,
                        packet.image_memory_slot,
                        packet.tm_packet_id,
                        "Unknown"),
                        ]
        self.db_cursor.executemany("INSERT INTO packet VALUES(?, ?, ?, ?, ?)", packet_data)
        self.database.commit()

    def add_image(self, image):
        """ Add image to database, if not present already """

        #TODO check for duplicate

        image_data =    [(image.image_name,
                        image.ec_address,
                        image.memory_slot,
                        image.number_of_packets),
                        ]
        self.db_cursor.executemany("INSERT INTO image VALUES(?, ?, ?, ?)", image_data)
        self.database.commit()