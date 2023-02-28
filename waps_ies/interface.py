import logging
import PySimpleGUI as sg
import threading
from waps_ies import processor

class WAPS_interface:
    """
    WAPS Graphical User Interface Class

    Attributes
    ----------
    source_file : str
        Source file path where the packet was extracted from
    extraction_time : str
        Time of packet extraction
    data : list
        Packet data stored as list of numbers. Each number represents one byte

    Methods
    -------
    info(additional=""):
        Prints the person's name and age.
    """

    def __init__(self, monitor):

        self.window_open = False
        self.monitor = monitor
        self.image_folder = self.monitor.output_folder

        sg.theme('GreenMono')

        icon = b'iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAOCklEQVR42u1aCZAddZn//n2+fse8N2dmJpMDCNlsROTQJZhAFINBsFQU2KUUS0uRsiirLLEodRdc3a0VFTxYgytqSRUCSqGwlHisSDCEI3JNKAwgEXJnkpnMu9/r8//f379fd2jGSTKToE2V86W+6n79+r3+fr/vfhlGf+fC0jYgbZkjIG0D0pY5AtI2IG2ZIyBtA9KWOQLSNiBtmSMgbQPSFvbOB7oNHL/i2cHl3OOkGNRUdaWu6MqkqrO9uqnu1HRtKzNoSyZjPnHb4u2VtI1+TQmITz7wzPyfck9cMrmnRkwhUvSO6hmNrFyGCrkuyufyPJ8pPE+quL9N9fsslnvgq/mNftogXhMCzttUOlMw8Ug2n6Hq3jYFTU4MBKiSiAwjFarnoJZCfV3zaEHmRCroxQlHtG4tB/u+e5318ItpgzkmAtZuKuqc87LglNOzjOwyJx/BzjQQYDDSTIDPShIU0qCGqZJiKjSUXUDHa28KfOHdtdv98799Lb9xa9qgjooAKWs2Fh4Qnng7IiEEHrSJ3Al4X4eCAFUDAUWQkVXIBAlM4Nir4LpCXVoPLVX/yS37+75e9Q/8xzdKjzlpg5s1Aeesz39ZuOIaEb+pEvk2kTfO4G0AV+H1jCCj2IkEFcVCL+F6RgkJYiqjQXUx9Skjm3fZL168rn/0dZ8WryJg9a9y7ySPfsNxLlDaFAWgdEF+i5FX7oAOmkSZeSiOlqwLKr5AkNmHtMhQSBJYIV3otCT7pvJYe8f7vjf47Ia0Qc6YgFV35woioEnyhSa9yV3c4Kmk9wmyJwTxNghxEAV9HOCJTKQCBznmMJFmUVgo0UbDL0XbpEXWsla1feA9P1zwwu/SBjojAqS89fb849wRb1Y0FqaAlKCskDWsUGOPT6ypE7d80vIdwJIQY16HEEkCw5Gx6BzH4exx9Vq7cvaPl2wbTRvsjAg480eF64O2uIrJoidbIIohYS4I0BEMhHr9zwEFAc6L0su4x0dEdAekZilMA0kEyiOpBdH5LJ4wmFu4rdIsn3rXSXted0PUXxCw4uau8/023aciBVQZ1rK46fJO3vkAyKi+GIT5LgcljWvEM52IUDIdEpiQ3UKEaSBJUBFKRbP/x7e9YetlaQM+IgFnrCvmibMJxpgpQ5w4egIAqXIW6BY4DchvMqpv88L5QMc/T3VJz3fyX5KgcIWUEtLC7EyThFTKKlk0TfXce1bsfV3Vg2mXoTNv6v0dBqJzdEtFLssWiAIIIrxJHrZApRhQc7ugdtknE252mUOK1YkIRYL20RV6MEnKc5Ai5wcecCrmSk/ds3L36WmDPiIBq9YNfIYH4ga9oJGRx9SHVBCaoID71J7wSTQVKp6g09hoi6itkqc4IfB4alQ9DZ3C70REmAYdAqycjnQwLvjVmv2/TBv4YQk4a93g8SxgW/W8ysxuncw8+r3JQYBHnuuR2/aovYdT98I8bft9mRDdnY4BVaXHPZ2UHr9TA8IIwPzAg3CXyBiZX/7mvIkLZmPkynusEeL0LvB/it+gEW5TQXhUR5Tuw/EFXN8E0zY9+0UY9loQIGX1jSNPGoZ2mtWnU6bXIB1VHdlPruOQ03ZAhI/ywEmv5WnXHw+E3yTbnop9gVroDD1BpwZIEhQVZUUWSkaGrgVIp5EHL6yOHcm4d2y0TkJL+S97P53vjJPqoocEmEyFHLLDaY3CDiXJR7Ft4Pm/xpXbMcnfu/nadnBMBJzz7cVXKUy9PgfwVq9ORo9cfiQFDtkgod1ok2f7ZBgG1bYQTe6thZ+zSjq1xnB9ngg7RdgWA5VE1u90DqSJrmpXPHhR5eZDPnujpRhd9GVnkq5ubicd4MMJVA5mckJlQlA2B7JVEU6engf1AQXXQ0cotB26DhX7+5u/2Dps6z0kAWu+uWSQfLYj223quQGT8kMGaSiALm9TY7IJbSECPAp0n/Kw9uX1ZUSGS/lurNN7bDIHWBgB4XSIWYF1BWE7lXVC05S7H7q09v5pn7s+Z2r9/CetXfS+1g7sIlUAh8d1tFmzGxEEb8sfblxPITyeAqgC3BrIQIMi12Xy2i7O6ZPg4z4QIOgwctifxM69ftmduqFd3DVgUWE+dBGaXjeRLZpUm6jS/q01au50w9ZX6inSc/+3l7JWhhqIDpkK4biMIipH6LAr6FG4Gmzikcvq/dM9812juVvrO/mH7F0dr+dxV98JIpxHXGyndoNRu87CTVWqjArkPwmZEr6QEbIZqNY+fU1r3zGlQGjMDSedheTdUOjPUnEYutCi7DDy2XSoZlepvG+SquMtqu+0SdiYCcDEjoflyMhJQWjKNphHDWmPo10OdfYDJSIBsuixjzV2yJNrP7zmoupAfcf4qftX7yyOfU16XjiCukqCcv1YxhDPXHR2E+RgePTgaRfzSBClhawJwhfPwesrR69tlWcC/ogESHn39adsMCzjrNJwjorzs1RYiFTIYznSalSpVWhyT5Vq5SY5dUSCilF5i6DJl9udLwfYfClDtu2E4atYnTlBwEpsmuduuqJxv7zvPz++9lu+T5/c9O4n9H37sV0BVGkZwh1dAzUuDPNwLW/RQc9jXA9BSwIowE4aiAl87ZsBfvtMwc+IgAtvfMtKFJOHCr1Z1jUoUyFDFnaCwHKoIRAFBypU2VulZtUmp+mRZih04GmX6rv9cGzO5yxymI0uwsKhSrU6M4EilCv/8On6TfIZ111+/v2Tpeo7HnzDU+SjoQwsQxBht/DgddeRIFlY/WUt8CV4HGX+S5WTKjpsgC323M3/3lo/G/AzIkDKxd898w5d0/4lj1ogq7zZi6KWD6gtGlQpV6g+0SAHXvblnOB4CH1B44+jQDZRmGyVAtMLR2VV/qaYUToEOOo1A/t6vrLcXnjyiFF6/KmBrepo/iXsDHgPa7avgzBZMJEuuB0FliEK2Cs57ydCPxCf3/yl1nWzBT9jAi794aoBPOhZ3dT78/0mmSUNRQ1v5DAZ8jo1qjWa2FWj6s42ubVA5iJpfXJc5lR7GeCLFP6YqoIEtEDimk/2bvrm+N38X69+79t/bpbM835dGqVxYwLFk4edQkaP7POyuHEXRRDnvtuJBh4Bl4qJ9WfPfKl10dGAnzEBUi679ey13Be/MCxdM7vUEIxS4OQbNrlBi2q1BrUqLWrUHXIbLnnNINwm6y/hnjq8Kj2KzqBheeKYCdrb+S3m/cVbPnLRGeuf6Kqxbe7zPOhuKKTzznATtXURejjydiDDnR0EL7j4LW55Lwho/9UJkPLh28/+qO8EP9AMVdHQ3hQL0yFW4YCQ/16bWi0Q0MJ5zUXLwqRoB+F47EygkjcEZYrYGypIhVJAjZf4HafvWjrZv7r7yqeb22jH6Nh3+s5SL0SqzA8JoFcIoJiE+BzdLnDEOr/BP/v8f9tO3wqNVbcE5NXETGC86qZZ/9fYJd9fcSna2A+YwrIqCKAMJ6575CM+bZRq24O2MCoDPHc76cCFJABpQAZVd7VJ72NUHfV/csXg21Y/yctDoy9u3bD90fJViBhl8Bzjg72naf+MaJkXpkCkkcc9EHlve4x/FfoklKDMLYuQoCl44vMkYJF4HZ7PmoBVn/oHTKJ8aWHQ/E5unrFGbokMIzJnHgjojMl2W6YBCmIrCPOXBYgWxLRjywVJhOlg7u8avfiEVac8tPFP9PtH/3Rts2I/ja+XodxA/tezC5TF+UXqUuwS+cyg0g5s8UevIh5zK6LhTIagmd8UDEVRicAmdTqPx9sDT+jsCRh6Y1FplV0dnswNn1pcs3Bl9+U9yzMrhcqtQEHuo0S74daIcwcE+Dx8FJOjqnwa9gIfoTqsL6ouHT6x+MItz9m/feKFqxHerYgADL8kB5kD0XkLw5OPmUJI89EOMQPLxAqBx8ekTvV+DDqI1E8eZ00Awl8aYMJg1HYahC7QMsqC7iWZkwvHGSdYQ8oAakMBUYF2IUysfqgFwg8c7iJ8a+6kqHKH9Z62+qSlXUo3e/bmLaPPvLTnTnyPmyBgAjoeEdGKjKUIsFQtofG1mIAYU+zlGLgXqRtp+Hq2BLDoIZjnCFsBLYQugg5AC1AjYcShQpGsLr1/5ALrEyO9A7TltrE795Ubz0UGtSICxiOV50702Ri4ntCYhKT3k+D9BGhnGp01ATSFgOOgi6FyscklPBKTNa10D+bfMnJ6z9rTc8Pizv998saW41UiIyUBlSgCJqPXMXg9IjgJPvb8VK9PB9yeCv5oCWCRAdLjI9DjoX0RAcYUo6bmZChLlg5csnxo3vKRYlflpnsf/hZ1QlQaWI+Ay9BvREaqEeEx+JkA96aAdRPHaKU6yhpAr06DLurUgaEoIjI0fWgmw5Pe89bl1/QV84Va03nmrg2bb48IaETej7URXY89byTAJ4tcnOdJ8LH3k68PgqZj6QIJEuKwlKCxupAVRUEuOs8kCIkLFZvfV1x6wYp//ELG0OnRLdvvePz5HX+IjJH5vhc6Rq/kPo/ISxa8qf19arFLVvok2IOgk58/1r8Rir0bF6hDHeNw1c9Ytuhjp504/NnuQo7+5xePXDdZa+3EdbnC7o6ANyLw8cQfF9SpxVUcRvmU10nCknLUETBdREwdRJI5Gl/XsqY+smL54s+98bihk7/98w1XUqfgNanTAuOwDQ5hcNJpU98/1MR3RMP/VsJyGYMpCtNt1zeCgGuMsUAOsZyLZG7OxPhDtthZG/U3JOCgSCKwHzD501Db9Y/a+NdC5v5OMG0D0pY5AtI2IG2ZIyBtA9KWOQLSNiBtmSMgbQPSljkC0jYgbfm7J+D/AdBcNsVGbLFzAAAAAElFTkSuQmCC'
        sg.set_options(icon=icon)

        ec_number = 4
        slot_number = 8
        layout = [[sg.Text('Input path:', size=(9,1)), sg.Text(monitor.input_folder, background_color='lightgrey', k='input_path')],
                  [sg.Text('Output path:', size=(9,1)), sg.Text(monitor.output_folder, background_color='lightgrey', k='input_path')],
                  [sg.Text('Scan not enabled', background_color='lightgrey', key='scan_status', size=(13,1), justification='c'),
                       sg.Text('Tracker not started', background_color='yellow',  key='tracker_status', size=(15,1), justification='c'),
                       sg.Text('Manually select a file to process:'),
                       sg.Input(key='selected_file', visible=False, enable_events=True), sg.FileBrowse()],
                  [sg.Text('Last processed telemetry archive from the input path:')],
                  [sg.Text('None', background_color='white', size=(63,1), k='last_processed_file')],
                  [sg.HSep()]]
                  
        column_slot = []
        column_slot.append([sg.Text(' ')])
        column_slot.append([sg.HSep()])
        for i in range(slot_number):
            column_slot.append([sg.Text('Memory')])
            column_slot.append([sg.Text('slot ' + str(i), justification='c')])
            if (i < slot_number - 1):
                column_slot.append([sg.HSep()])
        
        columns = []
        for ec in range(ec_number):
            columns.append([])
            if (ec==0):
                columns[ec].append([sg.Text("EC address 171")])
            else:
                columns[ec].append([sg.Text("EC address NUMBER")])
            columns[ec].append([sg.HSep()])
            for i in range(slot_number):
                cell_id = '_' + str(ec) + '_' + str(i)
                columns[ec].append([sg.Text('Unknown', k='status' + cell_id, size=(9,1), justification='c'),
                                 sg.ProgressBar(100, orientation='h', s=(3,16), k='progressbar' + cell_id),
                                 sg.Text('0/0', k='packet_number' + cell_id, size=(5,1))])
                #sg.Text('Image name', background_color='white', k='image_name' + cell_id, size=(30,1))
                columns[ec].append([sg.Text('Missing:'),sg.Text('[]', k='missing_packets' + cell_id)])
                if (i < slot_number - 1):
                    columns[ec].append([sg.HSep()])

        combined_columns = [sg.Col(column_slot), sg.VSep(),
                            sg.Col(columns[0]),sg.VSep(),
                            sg.Col(columns[1]),sg.VSep(),
                            sg.Col(columns[2]),sg.VSep(),
                            sg.Col(columns[3])]
        layout.append(combined_columns)
        layout.append([sg.Text('Statisctics: Total number of packets: X Missing packets: X Corrupt packets: X Images: X')])

        # Create the Window
        self.window = sg.Window('WAPS Image Extractor Software', layout)

        self.thread = threading.Thread(target=self.run, args=())
        self.thread.start()

    def run(self):
        """ Interface main loop """
        
        try:
            # Event Loop to process "events" and get the "values" of the inputs
            first_run = True
            timeout_value = 1
            while self.monitor.continue_running:
                event, values = self.window.read(timeout = timeout_value) # 1 s timeout
                self.window_open = True
                if event == sg.WIN_CLOSED or event == 'Exit': # if user closes window or clicks cancel
                    break
                elif (str(event) == 'selected_file'):
                    self.monitor.add_file_for_processing(values['selected_file'])
                    logging.info(' Manually added file: ' + values['selected_file'])
                elif (str(event) != '__TIMEOUT__'):
                    logging.info(' Interface event: ' + str(event) + ' ' + str(values))
                if (first_run):
                    first_run = False
                    timeout_value = 1000

        finally:
            self.window.close()
            self.window_open = False
            logging.info(' Closed interface')
            self.monitor.continue_running = False

    def close(self):
        """ Triggers close button interface action """
        
        if (self.window_open):
            self.window.write_event_value(None, 'Exit')

    def update_latest_file_processed(self, file_processed):
        """ Update the latest processed telemetry archive name """

        self.window['last_processed_file'].update(file_processed)

    def update_scan_enabled(self):
        """ Update scan status as "In progress" in the window """

        self.window['scan_status'].update(background_color='blue')
        self.window['scan_status'].update("Scan in progress")

    def update_scan_complete(self):
        """ Update scan status as "Complete" in the window """

        self.window['scan_status'].update(background_color='springgreen4')
        self.window['scan_status'].update("Scan complete")

    def update_tracker_not_enabled(self):
        """ Update tracker status as "Not enabled" in the window """

        self.window['tracker_status'].update(background_color='lightgrey')
        self.window['tracker_status'].update("Tracker not enabled")

    def update_tracker_active(self):
        """ Update tracker status as "Active" in the window """

        self.window['tracker_status'].update(background_color='blue')
        self.window['tracker_status'].update("Tracker active")

    def update_image_data(self, image):


        #logging.info(str(image))
        #self.window['image_name_0_' + str(image.memory_slot)].update(image.image_name)

        # Image packets status
        missing_packets = image.get_missing_packets()
        self.window['progressbar_0_' + str(image.memory_slot)].update(
            int(100.0*(image.number_of_packets - len(missing_packets))/image.number_of_packets))
        self.window['packet_number_0_' + str(image.memory_slot)].update(
            str(image.number_of_packets - len(missing_packets)) +
            '/' +
            str(image.number_of_packets))

        
        if (image.overwritten):
            self.window['status_0_' + str(image.memory_slot)].update("Overwritten")
            self.window['status_0_' + str(image.memory_slot)].update(background_color='yellow')
        elif (image.outdated):
            self.window['status_0_' + str(image.memory_slot)].update("Outdated")
            self.window['status_0_' + str(image.memory_slot)].update(background_color='yellow')
        elif (image.image_transmission_active):
            self.window['status_0_' + str(image.memory_slot)].update("In progress")
            self.window['status_0_' + str(image.memory_slot)].update(background_color='blue')
        elif (len(missing_packets)):
            self.window['status_0_' + str(image.memory_slot)].update("Incomplete")
            self.window['status_0_' + str(image.memory_slot)].update(background_color='red')
        else:
            self.window['status_0_' + str(image.memory_slot)].update("Finished")
            self.window['status_0_' + str(image.memory_slot)].update(background_color='springgreen1')
            # Change colours of all other finished images
            for i in range(8): # 8 memory slots
                if (self.window['status_0_' + str(i)].get() == 'Finished' and
                    i != image.memory_slot):
                    self.window['status_0_' + str(i)].update(
                        background_color='springgreen4')

        # Missing packets with colour change
        missing_packets_str = processor.WAPS_Image.number_sequence_printout(missing_packets)
        if (len(missing_packets_str) > 15):
            missing_packets_str = missing_packets_str[:16] + '..'
        self.window['missing_packets_0_' + str(image.memory_slot)].update(missing_packets_str)
        if (len(missing_packets)):
            if (image.overwritten or image.outdated or image.image_transmission_active):
                self.window['missing_packets_0_' + str(image.memory_slot)].update(
                    background_color='yellow')
            else:
                self.window['missing_packets_0_' + str(image.memory_slot)].update(
                    background_color='red')
        else:
            self.window['missing_packets_0_' + str(image.memory_slot)].update(
                background_color=sg.theme_background_color())
