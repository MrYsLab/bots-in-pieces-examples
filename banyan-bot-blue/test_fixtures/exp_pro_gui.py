#!/usr/bin/env python3

"""
 This is the Python Banyan GUI that communicates with
 the Raspberry Pi Banyan Gateway

 Copyright (c) 2019 Alan Yorinks All right reserved.

 Python Banyan is free software; you can redistribute it and/or
 modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 Version 3 as published by the Free Software Foundation; either
 or (at your option) any later version.
 This library is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 General Public License for more details.

 You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
 along with this library; if not, write to the Free Software
 Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""

import argparse
import signal
import sys
from functools import partial
# noinspection PyCompatibility
from tkinter import Tk, StringVar, Entry, DoubleVar, SUNKEN, Scale
# noinspection PyCompatibility,PyCompatibility
from tkinter import ttk
# noinspection PyCompatibility
# noinspection PyCompatibility
from tkinter.ttk import Notebook, Frame, Label, Combobox, Button

import msgpack
import zmq

from python_banyan.banyan_base import BanyanBase


# noinspection PyCompatibility


class Spinbox(ttk.Entry):
    """
    Some versions of python3 do not include this control
    as part of the standard distro, so here is the control's
    implementation
    """

    def __init__(self, master=None, **kw):
        ttk.Entry.__init__(self, master, "ttk::spinbox", **kw)

    def set(self, value):
        self.tk.call(self._w, "set", value)


# noinspection PyPep8
class ExplorerProGui(BanyanBase):
    """
    The Pimoroni Explorer-Pro For Raspberry Pi Demo Station GUI
    """

    def __init__(self, **kwargs):
        """
        Build the main screen as a notebook.
        """

        # initialize the parent class
        super(ExplorerProGui, self).__init__(
            back_plane_ip_address=kwargs['back_plane_ip_address'],
            subscriber_port=kwargs['subscriber_port'],
            publisher_port=kwargs['publisher_port'],
            process_name=kwargs['process_name'])

        self.set_subscriber_topic('report_from_hardware')

        self.main = Tk()
        self.main.title('Demo Station For Explorer-Pro HAT')

        # gives weight to the cells in the grid
        rows = 0
        while rows < 50:
            self.main.rowconfigure(rows, weight=1)
            self.main.columnconfigure(rows, weight=1)
            rows += 1

        # Defines and places the notebook widget
        self.nb = Notebook(self.main, padding=20, height=300, width=800)
        self.nb.grid(row=1, column=0, columnspan=50, rowspan=49, sticky='NESW')

        # create the analog inputs tab
        self.analog_inputs_tab = Frame(self.nb, padding=[130, 20])
        self.nb.add(self.analog_inputs_tab, text='Analog Inputs')
        # create an instance of the AnalogInputs class
        self.analog_inputs = AnalogInputs(self.analog_inputs_tab, self)

        # create the digital inputs tab
        self.digital_inputs_tab = Frame(self.nb, padding=[130, 20])
        self.nb.add(self.digital_inputs_tab, text='Digital Inputs')
        # create an instance of the DigitalInputs class
        # to populate and control Signal inputs
        self.digital_inputs = DigitalInputs(self.digital_inputs_tab, self)

        # create the touch tab
        self.touch_tab = Frame(self.nb, padding=10)
        self.nb.add(self.touch_tab, text='Touch Inputs')
        self.touch_inputs = TouchInputs(self.touch_tab, self)

        # create the digital outputs tab
        self.digital_outputs_tab = Frame(self.nb, padding=10)
        self.nb.add(self.digital_outputs_tab, text='Digital Outputs')
        # create an instance of the DigitalOutputs class
        # to populate and control digital outputs
        self.digital_outputs = DigitalOutputs(self.digital_outputs_tab, self)

        # create the LED digital outputs tab
        self.led_digital_outputs_tab = Frame(self.nb, padding=10)
        self.nb.add(self.led_digital_outputs_tab, text='LED Digital Outputs')
        # create an instance of the DigitalOutputs class
        # to populate and control digital outputs
        self.led_digital_outputs = LedDigitalOutputs(self.led_digital_outputs_tab, self)

        # create the pwm output tab
        self.pwm_output_tab = Frame(self.nb, padding=10)
        self.nb.add(self.pwm_output_tab, text='PWM Outputs')
        self.pwm_output = PwmOutputs(self.pwm_output_tab, self)

        # create the LED PWM output tab
        self.led_pwm_output_tab = Frame(self.nb, padding=10)
        self.nb.add(self.led_pwm_output_tab, text='LED PWM Outputs')
        self.led_pwm_output = LedPwmOutputs(self.led_pwm_output_tab, self)

        # create the dc motors tab
        self.motors_tab = Frame(self.nb, padding=10)
        self.nb.add(self.motors_tab, text='DC Motors')
        self.dc_motors = DcMotors(self.motors_tab, self)

        l = Label(self.main,
                  text='Copyright (c) 2019 Alan Yorinks All Rights Reserved.')
        l.config(font="Helvetica 8 ")
        l.grid(row=48, column=0, padx=[505, 0])

        self.main.after(5, self.get_message)

        try:
            self.main.mainloop()
        except KeyboardInterrupt:
            self.on_closing()

    def notebook_tab_selection(self):
        print(self.nb.tab(self.nb.select(), "text"))
        print(self.nb.index(self.nb.select()))

    # noinspection DuplicatedCode
    def get_message(self):
        """
        This method is called from the tkevent loop "after" method.
        It will poll for new zeromq messages within the tkinter event loop.
        """
        try:
            data = self.subscriber.recv_multipart(zmq.NOBLOCK)
            self.incoming_message_processing(data[0].decode(),
                                             msgpack.unpackb(data[1],
                                                             raw=False))
            self.main.after(1, self.get_message)

        except zmq.error.Again:
            try:
                self.main.after(1, self.get_message)
            except KeyboardInterrupt:
                self.main.destroy()
                self.publisher.close()
                self.subscriber.close()
                self.context.term()
                sys.exit(0)
        except KeyboardInterrupt:
            self.main.destroy()
            self.publisher.close()
            self.subscriber.close()
            self.context.term()
            sys.exit(0)

    def incoming_message_processing(self, topic, payload):
        """
        This method processes the incoming pin state change
        messages for GPIO pins set as inputs.

        :param topic:
        :param payload:

        Typical report: {'report': 'digital_input', 'pin': pin,
                       'value': level, 'timestamp': time.time()}
        """
        # if the pin currently input active, process the state change
        pin = payload['pin'] - 1
        value = payload['value']
        timestamp = payload['timestamp']
        report_type = payload['report']
        if report_type == 'analog_input':
            if 0 <= pin <= 3:
                self.analog_inputs.set_input_value(pin, value)
                self.analog_inputs.set_time_stamp_value(pin, timestamp)
            else:
                raise RuntimeError('analog pin out of range: ', pin)
        elif report_type == 'digital_input':
            if 0 <= pin <= 3:
                self.digital_inputs.set_input_value(pin, value)
                self.digital_inputs.set_time_stamp_value(pin, timestamp)
            else:
                raise RuntimeError('digital pin out of range')
        elif report_type == 'touch':
            if 0 <= pin <= 8:
                self.touch_inputs.set_input_value(pin, value)
                self.touch_inputs.set_time_stamp_value(pin, timestamp)
            else:
                raise RuntimeError('touch pin out of range')
        else:
            raise RuntimeError('Unknown report type: ', payload['report'])

    def on_closing(self):
        """
        Destroy the window
        """
        self.clean_up()
        self.main.destroy()


# noinspection PyPep8
class AnalogInputs:
    """
    This class creates a Analog Inputs labelframe
    on the parent notebook page, and also
    provides control for its components
    """

    def __init__(self, notebook_page, caller):
        """
        Create the and place the widgets in the frame
        for user input interaction.

        :param notebook_page: Notebook page to contain this frame
        :param caller: class instantiating this class
        """

        self.caller = caller

        # an array of value entry controls that hold the returned values
        self.values = []

        # an array of time stamp entry controls that hold the returned
        # timestamps
        self.time_stamps = []

        # create the frame
        self.analog_inputs_frame = Frame(notebook_page, padding=10,
                                         relief=SUNKEN)

        # create the controls for each of the 4 inputs
        for x in range(1, 5):
            # set the mode label with an associated analog input channel number
            l = Label(self.analog_inputs_frame,
                      text=('Analog Input ' + str(x)))
            l.grid(row=x, column=0)

            # create the next label for the value entry field
            l = Label(self.analog_inputs_frame, text=' Value:')
            l.grid(row=x, column=2, padx=[20, 5])

            # create a read only entry field for each analog input report
            # and set its value to 0
            value = Entry(self.analog_inputs_frame, state='readonly', width=6)
            value.configure({'readonlybackground': 'white'})
            self.values.append(value)
            value.grid(row=x, column=3, pady=3, padx=3)
            self.set_input_value(x - 1, '')

            # create a time stamp label for the timestamp entry field
            # and set its value to empty
            l = Label(self.analog_inputs_frame, text=' Time Stamp:')
            l.grid(row=x, column=4, padx=[20, 5])

            l.focus_set()

            # create a read only entry field for each time stamp
            time_stamp = Entry(self.analog_inputs_frame, state='readonly',
                               width=20)
            time_stamp.configure({'readonlybackground': 'white'})
            self.time_stamps.append(time_stamp)

            time_stamp.grid(row=x, column=5, pady=3, padx=3)
            self.set_time_stamp_value(x - 1, '')

            # grid the label frame and sets its position

        self.analog_inputs_frame.grid(row=0, column=0, sticky='EW',
                                      columnspan=49, padx=25, pady=[10, 0])

    def set_input_value(self, channel, value):
        """
        Set an input value field for the specified analog input channel
        to the value specified
        :param channel: 0-7
        :param value: value to be displayed
        :return:
        """
        # channel -= 1
        self.values[channel].configure({'state': 'normal'})
        self.values[channel].delete('0', 'end')
        self.values[channel].insert(0, value)
        self.values[channel].configure({'state': 'readonly'})

    def set_time_stamp_value(self, channel, value):
        """
        Set a time stamp field to the specified time stamp value
        :param channel: 0-7
        :param value: value to be displayed
        :return:
        """
        self.time_stamps[channel].configure({'state': 'normal'})
        self.time_stamps[channel].delete('0', 'end')
        self.time_stamps[channel].insert(0, value)
        self.time_stamps[channel].configure({'state': 'readonly'})


class DigitalInputs:
    """
    This class creates a Digital Inputs labelframe
    on the parent notebook page, and also
    provides control for its components
    """

    def __init__(self, notebook_page, caller):
        """
        Create the and place the widgets in the frame
        for user input interaction.

        :param notebook_page: Notebook page to contain this frame
        :param caller: class instantiating this class
        """

        self.caller = caller

        # an array of value entry controls that hold the returned values
        self.values = []

        # an array of time stamp entry controls that hold the returned
        # timestamps
        self.time_stamps = []

        # create the frame
        self.digital_inputs_frame = Frame(notebook_page, padding=10,
                                          relief=SUNKEN)

        # create the controls for each of the 4 inputs
        for x in range(1, 5):
            # set the mode label with an associated analog input channel number
            l = Label(self.digital_inputs_frame,
                      text=('Digital Input ' + str(x)))
            l.grid(row=x, column=0)

            # create the next label for the value entry field
            l = Label(self.digital_inputs_frame, text=' Value:')
            l.grid(row=x, column=2, padx=[20, 5])

            # create a read only entry field for each analog input report
            # and set its value to 0
            value = Entry(self.digital_inputs_frame, state='readonly', width=6)
            value.configure({'readonlybackground': 'white'})
            self.values.append(value)
            value.grid(row=x, column=3, pady=3, padx=3)
            self.set_input_value(x - 1, '')

            # create a time stamp label for the timestamp entry field
            # and set its value to empty
            l = Label(self.digital_inputs_frame, text=' Time Stamp:')
            l.grid(row=x, column=4, padx=[20, 5])
            l.focus_set()

            # create a read only entry field for each time stamp
            time_stamp = Entry(self.digital_inputs_frame, state='readonly',
                               width=20)
            time_stamp.configure({'readonlybackground': 'white'})
            self.time_stamps.append(time_stamp)

            time_stamp.grid(row=x, column=5, pady=3, padx=3)
            self.set_time_stamp_value(x - 1, '')

            # grid the label frame and sets its position

        self.digital_inputs_frame.grid(row=0, column=0, sticky='EW',
                                       columnspan=49, padx=25, pady=[10, 0])

    def set_input_value(self, channel, value):
        """
        Set an input value field for the specified analog input channel
        to the value specified
        :param channel: 0-7
        :param value: value to be displayed
        :return:
        """
        # channel -= 1
        self.values[channel].configure({'state': 'normal'})
        self.values[channel].delete('0', 'end')
        self.values[channel].insert(0, value)
        self.values[channel].configure({'state': 'readonly'})

    def set_time_stamp_value(self, channel, value):
        """
        Set a time stamp field to the specified time stamp value
        :param channel: 0-7
        :param value: value to be displayed
        :return:
        """
        self.time_stamps[channel].configure({'state': 'normal'})
        self.time_stamps[channel].delete('0', 'end')
        self.time_stamps[channel].insert(0, value)
        self.time_stamps[channel].configure({'state': 'readonly'})


class TouchInputs:
    """
    This class creates a Digital Inputs labelframe
    on the parent notebook page, and also
    provides control for its components
    """

    def __init__(self, notebook_page, caller):
        """
        Create the and place the widgets in the frame
        for user input interaction.

        :param notebook_page: Notebook page to contain this frame
        :param caller: class instantiating this class
        """

        self.caller = caller

        # an array of value entry controls that hold the returned values
        self.values = []

        # an array of time stamp entry controls that hold the returned
        # timestamps
        self.time_stamps = []

        # create the frame
        self.touch_inputs_frame = Frame(notebook_page, padding=10,
                                        relief=SUNKEN)

        # create the controls for each of the 4 inputs
        for x in range(1, 9):
            # set the mode label with an associated analog input channel number
            l = Label(self.touch_inputs_frame,
                      text=('Touch Input ' + str(x)))
            l.grid(row=x, column=0)
            # create the next label for the value entry field
            l = Label(self.touch_inputs_frame, text=' Value:')
            l.grid(row=x, column=2, padx=[20, 5])
            # create a read only entry field for each analog input report
            # and set its value to 0
            value = Entry(self.touch_inputs_frame, state='readonly', width=6)
            value.configure({'readonlybackground': 'white'})
            self.values.append(value)
            value.grid(row=x, column=3, pady=3, padx=3)
            self.set_input_value(x - 1, '')

            # create a time stamp label for the timestamp entry field
            # and set its value to empty
            l = Label(self.touch_inputs_frame, text=' Time Stamp:')
            l.grid(row=x, column=4, padx=[20, 5])
            l.focus_set()

            # create a read only entry field for each time stamp
            time_stamp = Entry(self.touch_inputs_frame, state='readonly',
                               width=20)
            time_stamp.configure({'readonlybackground': 'white'})
            self.time_stamps.append(time_stamp)

            time_stamp.grid(row=x, column=5, pady=3, padx=3)
            self.set_time_stamp_value(x - 1, '')

        self.touch_inputs_frame.grid(row=0, column=0, sticky='EW',
                                     columnspan=49, padx=135, pady=[10, 0])

    def set_input_value(self, channel, value):
        """
        Set an input value field for the specified analog input channel
        to the value specified
        :param channel: 0-7
        :param value: value to be displayed
        :return:
        """
        # channel -= 1
        self.values[channel].configure({'state': 'normal'})
        self.values[channel].delete('0', 'end')
        self.values[channel].insert(0, value)
        self.values[channel].configure({'state': 'readonly'})

    def set_time_stamp_value(self, channel, value):
        """
        Set a time stamp field to the specified time stamp value
        :param channel: 0-7
        :param value: value to be displayed
        :return:
        """
        self.time_stamps[channel].configure({'state': 'normal'})
        self.time_stamps[channel].delete('0', 'end')
        self.time_stamps[channel].insert(0, value)
        self.time_stamps[channel].configure({'state': 'readonly'})


# noinspection PyPep8
class DigitalOutputs:
    """
    This class creates a Signal Outputs labelframe
    on the parent notebook page, and also
    provides control for its components
    """

    def __init__(self, notebook_page, caller):
        """
        Create the and place the widgets in the frame
        for user Signal input interaction.

        :param notebook_page: Notebook page to contain this frame
        :param caller: class instantiating this class
        """

        self.digital_output_pins = [6, 12, 13, 16]
        self.caller = caller

        # an array of StringVariables, one for each mode control
        self.values = []

        # an array of the 8 mode combobox controls
        self.values_controls = []

        # selections for values combobox
        self.selections = ['Select Output Value', '0', '1']

        # create the frame
        self.digital_outputs_frame = Frame(notebook_page, padding=10,
                                           relief=SUNKEN)

        # create the controls for each of the 8 signals
        for x in range(1, 5):
            # set the mode label with an associated signal channel number
            l = Label(self.digital_outputs_frame,
                      text=('Digital Output ' + str(x)))
            l.grid(row=x, column=0, padx=[20, 3])

            self.values.append(StringVar())

            # Create the modes selection combobox.
            # Need to adjust index by -1
            self.values_box = Combobox(self.digital_outputs_frame,
                                       textvariable=self.values[x - 1],
                                       values=self.selections)
            self.values_box.bind('<<ComboboxSelected>>', self.value_selection)
            if x == 8:
                self.values_box.grid(row=x, column=1, pady=[3, 10], padx=[3,
                                                                          20])
            else:
                self.values_box.grid(row=x, column=1, pady=3, padx=[3, 20])
            self.values_box.current(0)
            self.values_controls.append(self.values_box)

            # add widget to array
            self.values.append(self.values_box)

        self.digital_outputs_frame.grid(row=0, column=0, sticky='EW',
                                        columnspan=49,
                                        padx=200, pady=[20, 0])

    def value_selection(self, event):
        if event.widget in self.values:
            if event.widget.get() in self.selections:
                pin = self.values_controls.index(event.widget)
                pin = self.digital_output_pins[pin]
                # need to decrease by 1
                value = self.selections.index(event.widget.get()) - 1
                topic = 'to_hardware'
                payload = {'command': 'set_mode_digital_output',
                           'pin': pin}
                self.caller.publish_payload(payload, topic)
                payload = {'command': 'digital_write', 'pin': pin, 'value': value}
                self.caller.publish_payload(payload, topic)


# noinspection PyPep8
class LedDigitalOutputs:
    """
    This class creates a Signal Outputs labelframe
    on the parent notebook page, and also
    provides control for its components
    """

    def __init__(self, notebook_page, caller):
        """
        Create the and place the widgets in the frame
        for user Signal input interaction.

        :param notebook_page: Notebook page to contain this frame
        :param caller: class instantiating this class
        """

        self.led_names = ['Blue', 'Yellow', 'Red', 'Green']
        self.led_pins = [4,  # Blue
                         17,  # Yellow
                         27,  # Red
                         5]  # Green
        self.caller = caller

        # an array of StringVariables, one for each mode control
        self.values = []

        # an array of the 8 mode combobox controls
        self.values_controls = []

        # selections for values combobox
        self.selections = ['Select Output Value', '0', '1']

        # create the frame
        self.led_digital_outputs_frame = Frame(notebook_page, padding=10,
                                               relief=SUNKEN)

        # create the controls for each of the 8 signals
        for x in range(0, 4):
            # set the mode label with an associated signal channel number
            l = Label(self.led_digital_outputs_frame,
                      text=(self.led_names[x]))
            l.grid(row=x, column=0, padx=[20, 3])

            self.values.append(StringVar())

            # Create the modes selection combobox.
            # Need to adjust index by -1
            self.values_box = Combobox(self.led_digital_outputs_frame,
                                       textvariable=self.values[x],
                                       values=self.selections)
            self.values_box.bind('<<ComboboxSelected>>', self.value_selection)
            if x == 4:
                self.values_box.grid(row=x, column=1, pady=[3, 10], padx=[3,
                                                                          20])
            else:
                self.values_box.grid(row=x, column=1, pady=3, padx=[3, 20])
            self.values_box.current(0)
            self.values_controls.append(self.values_box)

            # add widget to array
            self.values.append(self.values_box)

        self.led_digital_outputs_frame.grid(row=0, column=0, sticky='EW',
                                            columnspan=49,
                                            padx=200, pady=[20, 0])

    def value_selection(self, event):
        if event.widget in self.values:
            if event.widget.get() in self.selections:
                pin = self.values_controls.index(event.widget)
                # need to decrease by 1
                pin = self.led_pins[pin]
                value = self.selections.index(event.widget.get()) - 1
                topic = 'to_hardware'
                # payload = {'command': 'set_mode_digital_output',
                #            'pin': pin}
                # self.caller.publish_payload(payload, topic)
                if value == 1:
                    value = 100
                payload = {'command': 'digital_write', 'pin': pin, 'value': value}
                self.caller.publish_payload(payload, topic)


class PwmOutputs:
    """
    This class creates a PWM Outputs frame
    on the parent notebook page, and also
    provides control for its components.
    """

    def __init__(self, notebook_page, caller):
        self.pwm_output_frame = Frame(notebook_page, padding=10,
                                      relief=SUNKEN)

        self.caller = caller

        self.digital_output_pins = [6, 12, 13, 16]

        # an array of the execute buttons
        self.execute_buttons = []

        # an array of the scale widgets
        self.drive_scales = []

        # an array of the values for the scale widgets
        self.drive_values = []

        for x in range(0, 4):
            # set the mode label with an associated signal channel number
            # noinspection PyPep8
            l = Label(self.pwm_output_frame,
                      text=('Digital Output ' + str(x + 1)))
            l.grid(row=x, column=0, padx=[20, 5], pady=[22, 0])

            self.drive_values.append(DoubleVar())

            drive_scale = Scale(self.pwm_output_frame,
                                variable=self.drive_values[x],
                                orient='horizontal', troughcolor='white',
                                resolution=0.01, from_=0, to=100)
            self.drive_scales.append(drive_scale)

            drive_scale.grid(row=x, column=1)

            b = Button(self.pwm_output_frame,
                       text='Set Value ' + str(x + 1),
                       command=partial(self.set_drive_value, x))
            self.execute_buttons.append(b)
            b.grid(row=x, column=2, pady=[22, 0], padx=40)

        self.pwm_output_frame.grid(row=0, column=0, sticky='EW',
                                   columnspan=49, padx=[170, 0],
                                   pady=[20, 0])

    def set_drive_value(self, index):
        # normalize pin number for drives
        pin = self.digital_output_pins[index]
        value = self.drive_scales[index].get()
        topic = 'to_hardware'

        # payload = {'command': 'set_mode_pwm', 'pin': pin}
        # self.caller.publish_payload(payload, topic)

        payload = {'command': 'digital_write', 'pin': pin, 'value': value}
        self.caller.publish_payload(payload, topic)


class LedPwmOutputs:
    """
    This class creates a PWM Outputs frame
    on the parent notebook page, and also
    provides control for its components.
    """

    def __init__(self, notebook_page, caller):
        self.led_pwm_output_frame = Frame(notebook_page, padding=10,
                                          relief=SUNKEN)

        self.caller = caller
        self.colors = ['Blue', 'Yellow', 'Red', 'Green']

        self.led_pins = [4,  # Blue
                         17,  # Yellow
                         27,  # Red
                         5]  # Green

        # an array of the execute buttons
        self.execute_buttons = []

        # an array of the scale widgets
        self.drive_scales = []

        # an array of the values for the scale widgets
        self.drive_values = []

        for x in range(0, 4):
            # set the mode label with an associated signal channel number
            # noinspection PyPep8
            l = Label(self.led_pwm_output_frame,
                      text=(self.colors[x]))
            l.grid(row=x, column=0, padx=[20, 5], pady=[22, 0])

            self.drive_values.append(DoubleVar())

            drive_scale = Scale(self.led_pwm_output_frame,
                                variable=self.drive_values[x],
                                orient='horizontal', troughcolor='white',
                                resolution=0.01, from_=0, to=100)
            self.drive_scales.append(drive_scale)

            drive_scale.grid(row=x, column=1)

            b = Button(self.led_pwm_output_frame,
                       text='Set ' + self.colors[x],
                       command=partial(self.set_drive_value, x))
            self.execute_buttons.append(b)
            b.grid(row=x, column=2, pady=[22, 0], padx=40)

        self.led_pwm_output_frame.grid(row=0, column=0, sticky='EW',
                                       columnspan=49, padx=[170, 0],
                                       pady=[20, 0])

    def set_drive_value(self, index):
        # normalize pin number for drives
        pin = self.led_pins[index]
        value = self.drive_scales[index].get()
        topic = 'to_hardware'

        # payload = {'command': 'set_mode_pwm', 'pin': pin}
        # self.caller.publish_payload(payload, topic)

        payload = {'command': 'digital_write', 'pin': pin, 'value': value}
        self.caller.publish_payload(payload, topic)


# noinspection PyPep8
class DcMotors:
    """
    This class creates a DC Motor frame
    on the parent notebook page, and also
    provides control for its components.

    """

    def __init__(self, notebook_page, caller):
        self.motors_frame = Frame(notebook_page, padding=10,
                                  relief=SUNKEN)

        self.caller = caller

        # an array of the execute buttons
        self.forward_buttons = []
        self.reverse_buttons = []

        # an array of the scale widgets
        self.motor_scales = []

        # an array of the values for the scale widgets
        self.motor_values = []

        self.directions = []

        for x in range(0, 2):
            # set the mode label with an associated signal channel number
            l = Label(self.motors_frame,
                      text=('Motor ' + str(x + 1) + ' Speed: '))
            l.grid(row=x, column=0, padx=[20, 5], pady=[22, 0])

            self.motor_values.append(DoubleVar())

            motor_scale = Scale(self.motors_frame,
                                variable=self.motor_values[x],
                                orient='horizontal', troughcolor='white',
                                resolution=0.01, from_=0.00, to=1.00)
            self.motor_scales.append(motor_scale)

            motor_scale.grid(row=x, column=1)

            b = Button(self.motors_frame,
                       text='Move Forward',
                       command=partial(self.move_forward, x))
            self.forward_buttons.append(b)
            b.grid(row=x, column=2, pady=[22, 0], padx=[40, 40])

            b = Button(self.motors_frame,
                       text='Move Reverse',
                       command=partial(self.move_reverse, x))
            self.reverse_buttons.append(b)
            b.grid(row=x, column=3, pady=[22, 0])

        self.motors_frame.grid(row=0, column=0, sticky='EW',
                               columnspan=49, padx=125,
                               pady=[50, 0])

    def move_forward(self, index):
        speed = self.motor_scales[index].get()
        topic = 'to_hardware'

        payload = {'command': 'dc_motor_forward', 'motor': index + 1,
                   'speed': speed}
        self.caller.publish_payload(payload, topic)

    def move_reverse(self, index):
        speed = self.motor_scales[index].get()
        topic = 'to_hardware'

        payload = {'command': 'dc_motor_reverse', 'motor': index + 1,
                   'speed': speed * -1.0}
        self.caller.publish_payload(payload, topic)


def explorer_pro_demo():
    parser = argparse.ArgumentParser()

    parser.add_argument("-b", dest="back_plane_ip_address", default="None",
                        help="None or IP address used by Back Plane")
    # allow the user to specify a name for the component and have it shown on
    # the console banner.
    # modify the default process name to one you wish to see on the banner.
    # change the default in the derived class to set the name

    parser.add_argument("-n", dest="process_name", default="explorer_proGui",
                        help="Set process name in banner")
    parser.add_argument("-p", dest="publisher_port", default='43124',
                        help="Publisher IP port")
    parser.add_argument("-s", dest="subscriber_port", default='43125',
                        help="Subscriber IP port")

    args = parser.parse_args()

    if args.back_plane_ip_address == 'None':
        args.back_plane_ip_address = None
    kw_options = {'back_plane_ip_address': args.back_plane_ip_address,
                  'publisher_port': args.publisher_port,
                  'subscriber_port': args.subscriber_port,
                  'process_name': args.process_name, }

    # replace with the name of your class
    app = ExplorerProGui(**kw_options)

    # signal handler function called when Control-C occurs
    # noinspection PyShadowingNames,PyUnusedLocal
    def signal_handler(signal, frame):
        print("Control-C detected. See you soon.")
        app.clean_up()
        sys.exit(0)

    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == '__main__':
    explorer_pro_demo()
