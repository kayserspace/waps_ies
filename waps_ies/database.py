"""
Script: database.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: WAPS PD image extraction software for operations at MUSC
         Database access class
Version: 2023-04-18 14:00, version 0.1

Change Log:
2023-04-18 version 0.1
 - initial version
"""

import os
import logging
import sqlite3


class Database:
    """
    TCP Receiver class

    Attributes
    ----------

    Methods
    -------

    """

    def __init__(self, database_filename='waps_pd.db'):

        # Database initialization
        if not os.path.exists(database_filename):
            logging.warning("Database seems to be missing path does not exist. Creating it...")
        self.database = sqlite3.connect(database_filename,
                                        check_same_thread=False)
        self.db_cursor = self.database.cursor()
        logging.info(" # Opened database %s", database_filename)

        # Check database tables
        db_request = self.db_cursor.execute("SELECT name FROM sqlite_master")
        db_tables = db_request.fetchall()

        if not ('packets',) in db_tables:
            logging.debug("Adding packet table to db")
            packet_table_contents = ("CREATE TABLE packets(" +
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

        if not ('images',) in db_tables:
            logging.debug("Adding image table to db")
            image_table_contents = ("CREATE TABLE images(" +
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
                                    "completion_time)")
            self.db_cursor.execute(image_table_contents)

    def add_packet(self, packet):
        """ Add packet to database, if not present already """

        # Avoid adding packet several times
        if self.packet_exists(packet):
            logging.warning(" Packet %s already present in database",
                            packet.packet_name)
            return

        packet_data = [(packet.uuid,
                        packet.acquisition_time,
                        packet.ccsds_time,
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
                        packet.image_uuid),]

        packet_param = "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.db_cursor.executemany("INSERT INTO packets VALUES" + packet_param, packet_data)
        self.database.commit()

    def packet_exists(self, packet):
        """
        Check if packet already exists in the database
        Matching CCSDS_time and packet_name
        """

        res = self.db_cursor.execute("SELECT packet_uuid FROM packets WHERE " +
                                     "CCSDS_time=? AND packet_name=?",
                                     [packet.ccsds_time, packet.packet_name])
        res = res.fetchall()
        if len(res) != 0:
            return True

        return False

    def add_image(self, image):
        """ Add image to database, if not present already """

        # Avoid adding image several times
        uuid = self.image_exists(image)
        if uuid is not None:
            logging.warning(" image %s already present in database",
                            image.image_name)
            return uuid

        image_data = [(image.uuid,
                       image.acquisition_time,
                       image.ccsds_time,
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
                       image.completion_time),]
        image_param = "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        self.db_cursor.executemany("INSERT INTO images VALUES" + image_param, image_data)
        self.database.commit()
        return image.uuid

    def image_exists(self, image):
        """
        Check if image already exists in the database
        Matching CCSDS_time and image_name
        """

        res = self.db_cursor.execute("SELECT image_uuid FROM images WHERE " +
                                     "CCSDS_time=? AND image_name=?",
                                     [image.ccsds_time, image.image_name])
        res = res.fetchall()
        if len(res) == 1:
            return res[0][0]
        if len(res) > 1:
            logging.debug(" Multiple matching images")
            return res[0][0]
        return None

    def update_image_status(self, image):
        """ Update an existing image in the database with status """

        image_data = (len(image.packets),
                      image.overwritten,
                      image.outdated,
                      image.image_transmission_active,
                      image.update,
                      image.completion_time,
                      image.uuid),

        self.db_cursor.executemany("""UPDATE images SET
                                   received_packets=?,
                                   overwritten=?,
                                   outdated=?,
                                   transmission_active=?,
                                   image_update=?,
                                   completion_time=?
                                   WHERE image_uuid=?""",
                                   image_data)
        self.database.commit()

    def update_image_filenames(self, image):
        """ Update an existing image in the database with saved file names """

        image_data = (image.latest_saved_file,
                      image.latest_saved_file_data,
                      image.latest_saved_file_tm,
                      image.uuid),

        self.db_cursor.executemany("""UPDATE images SET
                                   latest_image_file=?,
                                   latest_data_file=?,
                                   latest_tm_file=?
                                   WHERE image_uuid=?""",
                                   image_data)
        self.database.commit()

    def get_image_list(self, ec_address=None):
        """
        Get image list to display in GUI
        If ec_address not provided - all images
        """

        contents = ("SELECT image_name, " +
                    "CCSDS_time, " +
                    "ec_address, " +
                    "ec_position, " +
                    "memory_slot, " +
                    "number_of_packets, " +
                    "received_packets, " +
                    "overwritten, " +
                    "transmission_active, " +
                    "completion_time " +
                    "FROM images")

        if ec_address is None:
            res = self.db_cursor.execute(contents + " ORDER BY CCSDS_time DESC;")
        else:
            res = self.db_cursor.execute(contents + " WHERE " + "ec_address=?"
                                         + " ORDER BY CCSDS_time DESC;",
                                         [ec_address])
        return res.fetchall()
