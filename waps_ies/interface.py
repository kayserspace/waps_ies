"""
Script: interface.py
Author: Georgi Olentsenko, g.olentsenko@kayserspace.co.uk
Purpose: WAPS Image Extraction Software
         Graphical User Interface module
Version: 2023-05-31, version 1.0

Change Log:
2023-04-18 version 0.1
 - initial version, file based
 - prototype stage
2023-05-31 v 1.0
 - release
"""

import logging
import threading
from datetime import datetime, timedelta
import PySimpleGUI as sg


class WapsIesGui:
    """WAPS Graphical User Interface Class

    Attributes
    ----------
    window (window type): GUI main window instance
    window_open (bool): Main GUI loop condition
    thread (Threading type): GUI thread instance
    list_window (window type): GUI image list window instance
    receiver (Receiver type): current waps_ies.Receiver instance

    db_data (list): full database image table readout
    db_shown (list): db_data entries list that is show in the image list window (filtered)
    db_fresh (bool): Whether database table is fresh, for filtering
    db_filtered_by (str): Latest filter value of teh image list table

    For reducing GUI update rate:
    last_ccsds_count_update (Tiem type): Time of the last CCSDS count update
    last_biolab_tm_count_update (Time type): Time of the last TM count update
    server_active (bool): Whether server status is already set to "Active"

    Following are IES session statistics mirror variables from the Receiver:
    prev_total_packets_received
    prev_total_biolab_packets
    prev_total_waps_image_packets
    prev_total_initialized_images
    prev_total_completed_images
    prev_total_lost_packets
    prev_total_corrupted_packets

    Methods
    -------
    __init__(self, receiver, start_thread=True):
        GUI initialization with Receiver reference. Start thread a new thread by default
    run(self):
        Main GUI loop with events
    close(self):
        Trigger a close event for the GUI
    update_server_connected(self):
        Change TCP server connection status to "Connected"
    update_server_active(self):
        Change TCP server connection status to "Active"
    update_server_disconnected(self):
        Change TCP server connection status to "Disconnected"

    update_ccsds_count(self):
        Update CCSDS packet count
    update_stats(self):
        Update all counts in the GUI
    update_latets_file(self, latest_file):
        Update latest saved file name
    update_column_occupation(self, ec_column, ec_address, ec_position):
        Update EC column with EC heading
    clear_column(self, ec_column):
        Clear an occupied column of EC header and data
    update_image_data(self, image):
        Update image data of one of the image cells

    format_image_list_data(self, db_data):
        format database data into the table format of teh image list window
    show_image_list(self, ec_address=None):
        Open the image list window
    refresh_image_list(self):
        Referesh the image list table in the image list window
    filter_image_list(self, val):
        Filter the image list table by a string
    save_image_list(self):
        Save the image list table to output directory
    show_selected_image(self, rows):
        Show selected image at the bottom of the image list window
    show_selected_image_details(self, rows):
        Show selected image details as a popup
    recover_images(self, rows):
        Request to recover and save images from database
    new_image(self):
        New image cerating based on user input
    """

    # Window with list of received images
    list_window = None
    db_data = []
    db_data_packet_numbers = []
    db_fresh = False
    db_shown = []
    db_filtered_by = ''

    last_ccsds_count_update = datetime.now()
    last_biolab_tm_count_update = datetime.now()
    server_active = False

    # Mirror of receiver values to check for update
    prev_total_packets_received = 0
    prev_total_biolab_packets = 0
    prev_total_waps_image_packets = 0
    prev_total_initialized_images = 0
    prev_total_completed_images = 0
    prev_total_lost_packets = 0
    prev_total_corrupted_packets = 0

    size_adjusted = False

    def __init__(self, receiver, instance_name='', start_thread=True):
        """Initialize the GUI referencing the Receiver
        Starting a new threa by default
        """

        self.window_open = False
        self.receiver = receiver

        sg.theme('GreenMono')
        sg.SetOptions(font=("Helvetica", 11), element_padding=(5, 2), margins=(5, 0))

        kayserspacelogo = b'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'
        icon = b'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'
        sg.set_options(icon=icon)

        column_number = 4
        slot_number = 8

        output_path_justivfication = 'l'
        if len(receiver.output_path) > 35:
            output_path_justivfication = 'r'

        layout_h = [[sg.Text('Instance:', size=(6, 1)),
                     sg.Text(instance_name, background_color='lightgrey',
                             justification='c', size=(18, 1)),
                     sg.Text('Server:'),
                     sg.Text(receiver.server_address[0] + ' : ' +
                             str(receiver.server_address[1]),
                             background_color='lightgrey',
                             justification='c', k='server', size=(20, 1),
                             tooltip="TCP server IP address and port"),
                     sg.Text('Disconnected', k='server_status',
                             size=(11, 1),
                             justification='c',
                             background_color='red'),
                     sg.Push(),
                     sg.Text('WAPS IES ' + str(receiver.conf["version"])),],
                    [sg.Text('CCSDS:', size=(6, 1)),
                     sg.Input('0', k='CCSDS_pkts', size=(12, 1),
                              background_color='white', readonly=True,
                              tooltip="Number of received CCSDS packets"),
                     sg.Text('BIOLAB telemetry:'),
                     sg.Input('0', k='BIOLAB_pkts', size=(12, 1),
                              background_color='white', readonly=True,
                              tooltip="Number of received BIOLAB telemetry packets"),
                     sg.Text('WAPS image data:'),
                     sg.Input('0', k='WAPS_pkts', size=(10, 1),
                              background_color='white', readonly=True,
                              tooltip="Number of received WAPS image packets"),
                     sg.Text('packets counts')],
                    [sg.Text('Output:  ', size=(6, 1)),
                     sg.Input(receiver.output_path, k='output_path',
                              size=(24, 1), justification=output_path_justivfication,
                              tooltip="Full path: " + receiver.output_path, readonly=True,
                              background_color='lightgrey'),
                     sg.Text('Latest saved image:', size=(15, 1)),
                     sg.Input('None', k='latest_file', size=(62, 1),
                              background_color='white', readonly=True)]]

        layout = [[sg.Col(layout_h),
                   sg.Col([[sg.Image(kayserspacelogo,
                                     size=(72, 72),
                                     expand_x=True, expand_y=True)]])]]

        column_slot = []
        column_slot.append([sg.Text(' ')])
        column_slot.append([sg.HSep()])
        for i in range(slot_number):
            column_slot.append([sg.Text('Memory')])
            column_slot.append([sg.Text('slot ' + str(i), justification='c')])
            if i < slot_number - 1:
                column_slot.append([sg.HSep()])

        columns = []
        frames = []
        for col in range(column_number):
            columns.append([])
            frames.append([])
            columns[col].append([sg.HSep()])
            columns[col].append([sg.Text("EC addr"),
                                sg.Text("", k='ec_address_' + str(col),
                                        background_color='lightgrey',
                                        size=(3, 1), justification='c',
                                        tooltip="EC address"),
                                sg.Text("pos"),
                                sg.Text("", k='ec_position_' + str(col),
                                        background_color='white',
                                        size=(6, 1), justification='c',
                                        tooltip="EC position"),
                                sg.Button('clr', k='clr_' + str(col),
                                          visible=False, font='Helvetica 7',
                                          tooltip="Clear this GUI column")])
            for i in range(slot_number):
                cell_id = '_' + str(col) + '_' + str(i)
                frames[col].append([sg.Text(str(i),
                                            background_color='lightgrey',
                                            tooltip="Memory slot number"),
                                   sg.Text('Unknown', k='status' + cell_id,
                                           size=(9, 1), justification='c',
                                           tooltip="Memory slot status"),
                                   sg.ProgressBar(100, orientation='h', s=(3, 16),
                                                  k='progressbar' + cell_id),
                                   sg.Text('', k='packet_number' + cell_id,
                                           size=(6, 1), tooltip="Received/Expected packets")])
                frames[col].append([sg.Text('', k='image_type' + cell_id,
                                            tooltip="Image type (uCAM or FLIR)"),
                                   sg.Text('', k="miss" + cell_id),
                                   sg.Text('', k='missing_packets' + cell_id,
                                           tooltip="Missing packet list")])
                if i < slot_number - 1:
                    frames[col].append([sg.HSep()])
            columns[col].append([sg.Frame('Memory slots', frames[col])])

        combined_columns = [sg.Col(columns[0]),
                            sg.Col(columns[1]),
                            sg.Col(columns[2]),
                            sg.Col(columns[3])]
        layout.append(combined_columns)

        status_bar = [sg.Button('List all received images',
                                k='list_all_button'),
                      sg.Text('Initialized images:'),
                      sg.Input('0', k='initialized_images', size=(5, 1),
                               background_color='white', readonly=True),
                      sg.Text('Completed images:'),
                      sg.Input('0', k='completed_images', size=(5, 1),
                               background_color='white', readonly=True),
                      sg.Text('Lost packets:'),
                      sg.Input('0', k='lost_packets', size=(5, 1),
                               background_color='white', readonly=True),
                      sg.Text('Corrupted packets:'),
                      sg.Input('0', k='corrupted_packets', size=(5, 1),
                               background_color='white', readonly=True)]
        layout.append(status_bar)

        # Create the Window
        self.window = sg.Window(instance_name + ' WAPS Image Extraction Software ' +
                                str(receiver.conf["version"]),
                                layout,
                                resizable=True)

        # New thread start
        if start_thread:
            self.thread = threading.Thread(target=self.run,
                                           args=(),
                                           daemon=True)
            self.thread.start()

    def run(self):
        """Interface main loop
        All GUI events are received and processed here
        """

        timeout = 100
        # Event Loop to process "events" and get the "values" of the inputs
        while self.receiver.continue_running:
            try:
                if self.list_window is None:
                    win = self.window
                    event, values = self.window.read(timeout=timeout)
                else:
                    win, event, values = sg.read_all_windows(timeout=timeout)
                self.window_open = True
                if event in (sg.WIN_CLOSED, 'Exit'):
                    if win == self.list_window:
                        self.list_window.close()
                        del self.list_window
                        self.list_window = None
                        del self.db_data
                        self.db_data = []
                    else:
                        self.receiver.continue_running = False
                elif str(event) == 'list_all_button':
                    self.show_image_list()
                elif str(event) in ('clr_0', 'clr_1', 'clr_2', 'clr_3'):
                    self.clear_column(str(event)[4])
                elif str(event) == 'refresh_button':
                    # Make the refresh in the main loop to avoid recursive database calls
                    self.receiver.refresh_gui_list_window = True
                elif str(event) == 'save_button':
                    self.save_image_list()
                elif str(event) == 'filter_input_Enter':
                    self.filter_image_list(self.list_window['filter_input'].get())
                elif str(event) == 'filter_button':
                    self.filter_image_list(self.list_window['filter_input'].get())
                elif str(event) == 'image_table':
                    self.show_selected_image(values['image_table'])
                elif str(event) == 'image_details':
                    self.show_selected_image_details(values['image_table'])
                elif str(event) == 'image_retrieve':
                    self.recover_images(values['image_table'])
                elif str(event) == 'clone_database':
                    self.receiver.clone_database = True
                elif str(event) == 'new_image':
                    self.new_image()
                elif str(event) != '__TIMEOUT__':
                    logging.info(' Unexpected interface event: %s %s %s',
                                 str(event),
                                 str(values),
                                 str(win))
                if not self.size_adjusted:
                    self.size_adjusted = True
                    # Adjusting kayser logo placement in case of differnt font pixel size
                    font_pixel_size = sg.tkinter.font.Font().measure('A')
                    if font_pixel_size != 13:  # test window machine font size
                        # Fancy calculation based on font/pixel size of row with this field...
                        diff = int(62 - (1331 - 107 * font_pixel_size)/font_pixel_size*62/107)
                        self.window['latest_file'].Widget.config(width=diff)
                timeout = 10000  # ms
            finally:
                pass

        self.window_open = False
        self.window.close()
        logging.info(' # Closed interface')
        self.receiver.continue_running = False

    def close(self):
        """ Triggers close button interface action. Used externally """

        if self.window_open:
            self.receiver.gui = None
            self.window.write_event_value(None, 'Exit')

    def update_server_connected(self):
        """ Update server status as "Connected" in the window """

        self.window['server_status'].update(background_color='yellow')
        self.window['server_status'].update("Connected")
        self.server_active = False

    def update_server_active(self):
        """ Update server status as "Active" in the window """

        if self.server_active:
            return
        self.window['server_status'].update(background_color='springgreen4')
        self.window['server_status'].update("Active")
        self.server_active = True

    def update_server_disconnected(self):
        """ Update server status as "Disconnected" in the window """

        self.window['server_status'].update(background_color='red')
        self.window['server_status'].update("Disconnected")
        self.server_active = False

    def update_ccsds_count(self):
        """ Update CCSDS count in GUI (limited per second) """

        current_time = datetime.now()
        if (current_time > self.last_ccsds_count_update +
                timedelta(milliseconds=50)):                        # 20 Hz
            self.last_ccsds_count_update = current_time
            self.window['CCSDS_pkts'].update(self.receiver.total_packets_received)

    def update_stats(self):
        """ Update statistics in the window """

        # To minimaize GUI processing time, for each check if value is identical first
        # Top
        if self.prev_total_packets_received != self.receiver.total_packets_received:
            self.prev_total_packets_received = self.receiver.total_packets_received
            self.window['CCSDS_pkts'].update(self.receiver.total_packets_received)

        if self.prev_total_biolab_packets != self.receiver.total_biolab_packets:
            self.prev_total_biolab_packets = self.receiver.total_biolab_packets
            self.window['BIOLAB_pkts'].update(self.receiver.total_biolab_packets)

        if self.prev_total_waps_image_packets != self.receiver.total_waps_image_packets:
            self.prev_total_waps_image_packets = self.receiver.total_waps_image_packets
            self.window['WAPS_pkts'].update(self.receiver.total_waps_image_packets)

        # Bottom
        if self.prev_total_initialized_images != self.receiver.total_initialized_images:
            self.prev_total_initialized_images = self.receiver.total_initialized_images
            self.window['initialized_images'].update(self.receiver.total_initialized_images)

        if self.prev_total_completed_images != self.receiver.total_completed_images:
            self.prev_total_completed_images = self.receiver.total_completed_images
            self.window['completed_images'].update(self.receiver.total_completed_images)

        if self.prev_total_lost_packets != self.receiver.total_lost_packets:
            self.prev_total_lost_packets = self.receiver.total_lost_packets
            self.window['lost_packets'].update(self.receiver.total_lost_packets)

        if self.prev_total_corrupted_packets != self.receiver.total_corrupted_packets:
            self.prev_total_corrupted_packets = self.receiver.total_corrupted_packets
            self.window['corrupted_packets'].update(self.receiver.total_corrupted_packets)

    def update_latets_file(self, latest_file):
        """ Update saved file name in the window """

        self.window['latest_file'].update(latest_file)

    def update_column_occupation(self, ec_column, ec_address, ec_position):
        """ Update GUI EC column occupation """

        # EC address / position update
        self.window['ec_address_' + str(ec_column)].update(str(ec_address))
        self.window['ec_position_' + str(ec_column)].update(ec_position)
        self.window['clr_' + str(ec_column)].update(visible=True)

    def clear_column(self, ec_column):
        """ Update GUI EC column occupation """

        res = sg.popup_yes_no('Clear column ' + ec_column + '?' +
                              '\nDatabase is unaffected')
        if res != 'Yes':
            return

        self.receiver.clear_gui_column(ec_column)

        # Update column top
        self.window['ec_address_' + ec_column].update('')
        self.window['ec_position_' + ec_column].update('')
        self.window['clr_' + ec_column].update(visible=False)

        # Update cells
        for i in range(8):
            cell_id = '_' + ec_column + '_' + str(i)
            self.window['status' +
                        cell_id].update('Unknown', background_color=sg.theme_background_color())
            self.window['progressbar' + cell_id].update(0)
            self.window['packet_number' + cell_id].update('')
            self.window['image_type' +
                        cell_id].update('', background_color=sg.theme_background_color())
            self.window['miss' + cell_id].update('')
            self.window['missing_packets' +
                        cell_id].update('', background_color=sg.theme_background_color())

        logging.info("\nCleared GUI column " + ec_column)

    def update_image_data(self, image):
        """ Update GUI image cell contents """

        # Identify GUI column of the image
        ec_index = self.receiver.get_ec_states_index(image.ec_address)
        ec_column = self.receiver.ec_states[ec_index]["gui_column"]
        if ec_column is None:
            self.receiver.assign_ec_column(image.ec_address)
            ec_column = self.receiver.ec_states[ec_index]["gui_column"]
            if ec_column is None:
                logging.warning("\nGUI does not have space for this EC: %i",
                                image.ec_address)
                return

        # Image packets status
        missing_packets = image.get_missing_packets()
        self.window['progressbar_' + str(ec_column) + '_' +
                    str(image.memory_slot)].update(
                    int(100.0*(image.number_of_packets -
                        len(missing_packets))/image.number_of_packets))
        self.window['packet_number_' + str(ec_column) + '_' +
                    str(image.memory_slot)].update(
            str(image.number_of_packets - len(missing_packets)) +
            '/' +
            str(image.number_of_packets))

        curr_tag = 'status_' + str(ec_column) + '_' + str(image.memory_slot)

        if len(missing_packets) == 0:
            self.window[curr_tag].update("Complete")
            self.window[curr_tag].update(background_color='springgreen1')
            # Change colours of all other finished images
            for i in range(8):  # 8 memory slots
                if (self.window['status_' + str(ec_column) +
                                '_' + str(i)].get() == 'Complete' and
                        i != image.memory_slot):
                    self.window['status_' + str(ec_column) +
                                '_' + str(i)].update(
                        background_color='springgreen4')
        elif image.image_transmission_active:
            self.window[curr_tag].update("In progress")
            self.window[curr_tag].update(background_color='lightblue')
        elif image.overwritten:
            self.window[curr_tag].update("Overwritten")
            self.window[curr_tag].update(background_color='yellow')
        elif image.outdated:
            self.window[curr_tag].update("Outdated")
            self.window[curr_tag].update(background_color='yellow')
        else:
            self.window[curr_tag].update("Incomplete")
            self.window[curr_tag].update(background_color='red')

        # Image type
        self.window['image_type_' + str(ec_column) + '_' +
                    str(image.memory_slot)].update(image.camera_type,
                                                   background_color='lightgrey')

        # Missing packets with colour change
        missing_packets_str = image.missing_packets_string()
        packets_sequential = image.packets_are_sequential()
        if len(missing_packets_str) > 18:
            missing_packets_str = missing_packets_str[:missing_packets_str[:17].rfind(',')] + '...'
        self.window['missing_packets_' + str(ec_column) + '_' +
                    str(image.memory_slot)].update(missing_packets_str)
        if len(missing_packets) == 0:
            self.window['miss_' + str(ec_column) + '_' + str(image.memory_slot)].update("")
        if len(missing_packets) == 0 or image.image_transmission_active and packets_sequential:
            self.window['missing_packets_' + str(ec_column) + '_' +
                        str(image.memory_slot)].update(background_color=sg.theme_background_color())
        else:
            self.window['miss_' + str(ec_column) + '_' + str(image.memory_slot)].update("Miss:")
            sg.Text('', k="miss" + str(ec_column) +
                    '_' + str(image.memory_slot))
            if image.overwritten or image.outdated or image.image_transmission_active:
                self.window['missing_packets_' + str(ec_column) + '_' +
                            str(image.memory_slot)].update(background_color='yellow')
            else:
                self.window['missing_packets_' + str(ec_column) + '_' +
                            str(image.memory_slot)].update(background_color='red')

        # Too many packets received for this image
        if len(missing_packets) == 0 and image.total_packets > image.number_of_packets*1.1:
            logging.warning("\n More than expected number of packets." +
                            " Has the initialization packet been missed?")
            self.window['missing_packets_' + str(ec_column) + '_' +
                        str(image.memory_slot)].update("Total packets: " + str(image.total_packets))

            self.window['missing_packets_' + str(ec_column) + '_' +
                        str(image.memory_slot)].update(background_color='yellow')

    def format_image_list_data(self, db_data):
        """ Format the data according to the list window table """

        data = []
        for index, image_data in enumerate(db_data):
            image_row = []
            image_row.append(len(db_data) - index)
            image_row.append(image_data[6])           # EC address
            image_row.append(image_data[7])           # EC Position
            image_row.append('m'+str(image_data[8]))  # Memory slot
            image_row.append(image_data[5])           # Camera type
            image_row.append(image_data[2][5:19])      # Creation time
            image_row.append(image_data[18][5:19])     # Last update time

            image_row.append(str(image_data[10]) +    # Received / Expected packets
                             '/' + str(image_data[9]))
            perc = int(100.0*image_data[10]/image_data[9])
            image_row.append(str(perc) + '%')         # Image percentage received
            image_row.append(self.db_data_packet_numbers[index])  # All assigned packets

            status = "Incomplete"
            if image_data[9] == image_data[10]:
                status = "Done"
            elif image_data[13] == 1:
                status = "In progress"
            image_row.append(status)                  # Image status
            image_row.append(image_data[19])          # Missing packets

            data.append(image_row)

        return data

    def show_image_list(self, ec_address=None):
        """ Open a new window with the list of received images """

        # Only allow one list window at a time
        if self.list_window is not None:
            self.list_window.close()

        self.db_data = self.receiver.database.get_image_list()
        self.db_data_packet_numbers = []
        self.db_shown = []
        for i in range(len(self.db_data)):
            self.db_shown.append(True)
            # Get number of assigned packets in database
            self.db_data_packet_numbers.append(self.receiver.database.get_image_packet_number(self.db_data[i][0]))
        data = self.format_image_list_data(self.db_data)

        table_headings = ['#  ', 'Addr', 'Pos', 'Mem', 'Type',
                          'Created', 'Last update',
                          'Compl', '%', 'Recv', 'Status', 'Missing packets']

        layout = [[sg.Button('Refresh', k='refresh_button',
                             tooltip="Read database and get fresh list of images"),
                   sg.Text("Total of"),
                   sg.Input(len(self.db_data), k='image_list_count', size=(4, 1),
                            background_color='white', readonly=True,
                            tooltip="Count includes filtered out"),
                   sg.Text("images starting with the latest"),
                   sg.Button('Save table', k='save_button',
                             tooltip="Save table contents as a .CSV file to output directory"),
                   sg.Text("", k='save_result', size=(6, 1),
                           justification='c'),
                   sg.Button('Filter', k='filter_button',
                             tooltip="Filter contents by following string"),
                   sg.Input('', k='filter_input')],
                  [sg.Table(data,
                            table_headings,
                            k="image_table",
                            num_rows=20,
                            select_mode=sg.TABLE_SELECT_MODE_EXTENDED,
                            alternating_row_color='lightgrey',
                            justification='l',
                            enable_events=True,
                            auto_size_columns=False,
                            col_widths=[3, 3, 6, 3, 5, 11, 11, 7, 4, 4, 8, 15],
                            expand_x=True, expand_y=True),],
                  [sg.Button('Clone database', k='clone_database'),
                   sg.Button('New image', k='new_image'),
                   sg.Text("Selected image:"),
                   sg.Input("None", k='selected_image_file_path', size=(40, 1), readonly=True),
                   sg.Button('Details', k='image_details', visible=False),
                   sg.Button('Retrieve and save selected', k='image_retrieve', visible=False)]]

        # Create a new window
        list_window_title = 'WAPS list of received images'
        if ec_address is not None:
            list_window_title = (list_window_title +
                                 ' from EC ' + str(ec_address))

        self.list_window = sg.Window(list_window_title,
                                     layout,
                                     resizable=True,
                                     finalize=True)

        self.list_window['filter_input'].bind("<Return>", "_Enter")

        logging.info("\nOpened image list table")

    def refresh_image_list(self):
        """ Refresh the image list table """

        self.db_data = self.receiver.database.get_image_list()
        self.db_data_packet_numbers = []
        self.db_shown = []
        for i in range(len(self.db_data)):
            self.db_shown.append(True)
            # Get number of assigned packets in database
            self.db_data_packet_numbers.append(self.receiver.database.get_image_packet_number(self.db_data[i][0]))
        data = self.format_image_list_data(self.db_data)
        if self.list_window is not None:
            self.list_window["image_table"].update(data)
            self.list_window['image_list_count'].update(len(data))
            self.list_window['save_result'].update('', background_color=sg.theme_background_color())
            logging.info("\nImage list table refreshed")

    def filter_image_list(self, val):
        """ Filter image list table by given value """

        data = self.format_image_list_data(self.db_data)

        filtered_data = []
        for index, row in enumerate(data):
            if not self.db_shown[index]:
                continue
            match_found = False
            for col_val in row:
                if val in str(col_val):
                    filtered_data.append(data[index])
                    match_found = True
                    break
            if not match_found:
                self.db_shown[index] = False

        self.db_filtered_by = val

        self.list_window['image_list_count'].update(len(filtered_data))
        self.list_window["image_table"].update(filtered_data)
        self.list_window['save_result'].update('', background_color=sg.theme_background_color())
        logging.info("\nImage list filtered by '%s'", val)

    def save_image_list(self):
        """ Save image list table to excel """

        # Get the current table contents
        data = self.format_image_list_data(self.db_data)

        csv_data = ('Database image list generated ' + datetime.now().strftime("%Y/%m/%d %H:%M:%S") +
                    ' by WAPS Image Extraction Software\n')
        csv_data = csv_data + f"Total number of images: {len(data)}\n"
        if self.db_filtered_by != '':
            csv_data = csv_data + f"Image list is filtered by '{self.db_filtered_by}'\n"
        else:
            csv_data = csv_data + "No filter\n"

        csv_data = csv_data + ('#  , Addr, Pos, Mem, Type, Created, Last update,' +
                               'Compl, %, Recv, Status, Missing packets, , ,')
        csv_data = csv_data + self.receiver.database.database_image_table + '\n'

        for index, row in enumerate(data):
            if self.db_shown[index]:
                # Save actual image list table data
                for item in row:
                    csv_data = csv_data + str(item).replace(',', ';') + ', '

                csv_data = csv_data + ', , '  # a couple of empty columns
                # Also save all the addition database data of that items
                for item in self.db_data[index]:
                    csv_data = csv_data + str(item).replace(',', ';') + ', '

                csv_data = csv_data + '\n'

        # Write the file
        filename = "waps_image_list_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".csv"
        file_path = self.receiver.output_path + '/' + filename
        try:
            with open(file_path, 'w') as file:
                file.write(csv_data)
                logging.info("\nSaved image list as %s", str(file_path))

        except IOError:
            logging.error('\nCould not open file for writing: %s', file_path)

        self.list_window['save_result'].update("Saved!",
                                               background_color='springgreen1')

    def show_selected_image(self, rows):
        """ Show selected image name in the list window """

        if len(rows) != 0:
            # Get only the first value
            row_data = self.list_window["image_table"].get()[rows[0]]
            db_data_length = len(self.db_data)
            table_index = db_data_length - row_data[0]  # minus selected number

            image_data = self.db_data[table_index]
            self.list_window['selected_image_file_path'].update(image_data[4])
            self.list_window['image_details'].update(visible=True)
            self.list_window['image_retrieve'].update(visible=True)
        else:
            self.list_window['selected_image_file_path'].update('None')
            self.list_window['image_details'].update(visible=False)
            self.list_window['image_retrieve'].update(visible=False)

    def show_selected_image_details(self, rows):
        """ Show selected image details in a popup window """

        if len(rows) != 0:

            # Get only the first value
            row_data = self.list_window["image_table"].get()[rows[0]]
            db_data_length = len(self.db_data)
            table_index = db_data_length - row_data[0]  # minus selected number

            image_data = self.db_data[table_index]
            completion = 100.0*int(image_data[10])/int(image_data[9])

            popup_str = (f'Image name:\t{image_data[4]}\n' +
                         f'Image UUID:\t{image_data[0]}\n' +
                         f'Acquisition time:\t\t{image_data[1]}\n' +
                         f'Initialization CCSDS time:\t{image_data[2]}\n' +
                         f'EC internal time tag:\t\t{image_data[3]}\n' +
                         f'Last update CCSDS time:\t\t{image_data[18]}\n' +
                         f'EC address / position:\t\t{image_data[6]} / {image_data[7]}\n' +
                         f'Memory slot / Camera type:\t{image_data[8]}   / {image_data[5]}\n' +
                         f'\tIn progress:\t{image_data[13] == 1}\n' +
                         f'\tOverwritten:\t{image_data[11] == 1}\n' +
                         f'\tOutdated:\t{image_data[12] == 1}\n\n' +
                         'Completion (assigned packets):\t' +
                         f'{image_data[10]}/{image_data[9]}  {completion:.1f}%' +
                         f'  ({self.db_data_packet_numbers[table_index]})\n')
            if image_data[19] != '':
                popup_str = (popup_str +
                             f'Missing packets numbers:\t{image_data[19]}\n')

            popup_str = (popup_str + '\n' +
                         f'Last saved image file:\t\t{str(image_data[15])}')

            if image_data[5] == 'FLIR':
                popup_str = (popup_str + '\n' +
                             f'Last saved data file:\t\t{image_data[16]}\n' +
                             f'Last saved telemetry file:\t{image_data[17]}')

            self.popup_window = sg.popup_no_buttons(popup_str, font=("Courier New", 10),
                                                    title=f"Image {image_data[4]} details")

            logging.info("\nImage %s details are shown in a popup window", image_data[4])

    def recover_images(self, rows):
        """ Recover images from database and saved them to harddrive """

        for index, row in enumerate(rows):
            # Get only the first value
            row_data = self.list_window["image_table"].get()[rows[index]]
            db_data_length = len(self.db_data)
            table_index = db_data_length - row_data[0]  # minus selected number

            image_uuid = self.db_data[table_index][0]
            image_name = self.db_data[table_index][4]

            logging.info(f'\n### Retrieving and saving {image_name}')
            self.receiver.recover_image_uuids.append(image_uuid)

    def new_image(self):
        """New image cerating based on user input"""

        image_uuid = sg.popup_get_text("Type in the packet UUID to base the image on",
                                       title="New image")
        self.receiver.create_new_image_packet_uuid = image_uuid
