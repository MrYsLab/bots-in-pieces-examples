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
from tkinter import Tk, StringVar, Entry, DoubleVar, SUNKEN, Scale, IntVar
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
class CrickitGui(BanyanBase):
    """
    The Crickit For Raspberry Pi Demo Station GUI
    """

    def __init__(self, **kwargs):
        """
        Build the main screen as a notebook.
        """

        # initialize the parent class
        super(CrickitGui, self).__init__(
            back_plane_ip_address=kwargs['back_plane_ip_address'],
            subscriber_port=kwargs['subscriber_port'],
            publisher_port=kwargs['publisher_port'],
            process_name=kwargs['process_name'])

        self.set_subscriber_topic('report_from_hardware')

        self.main = Tk()
        self.main.title('Demo Station For Raspberry Pi Crickit')

        # gives weight to the cells in the grid
        rows = 0
        while rows < 50:
            self.main.rowconfigure(rows, weight=1)
            self.main.columnconfigure(rows, weight=1)
            rows += 1

        # Defines and places the notebook widget
        self.nb = Notebook(self.main, padding=20, height=300, width=800)
        self.nb.grid(row=1, column=0, columnspan=50, rowspan=49, sticky='NESW')

        # create the signal inputs tab
        self.signal_inputs_tab = Frame(self.nb, padding=10)
        self.nb.add(self.signal_inputs_tab, text='Signal Inputs')
        # create an instance of the SignalInputs class
        # to populate and control Signal inputs
        self.signal_inputs = SignalInputs(self.signal_inputs_tab, self)

        # create the signal outputs tab
        self.signal_outputs_tab = Frame(self.nb, padding=10)
        self.nb.add(self.signal_outputs_tab, text='Signal Outputs')
        # create an instance of the SignalOutputs class
        # to populate and control Signal outputs
        self.signal_outputs = SignalOutputs(self.signal_outputs_tab, self)

        # create the signals tab
        self.touch_tab = Frame(self.nb, padding=10)
        self.nb.add(self.touch_tab, text='Touch Inputs')
        self.touch_inputs = TouchInputs(self.touch_tab, self)

        # create the drives tab
        self.drives_tab = Frame(self.nb, padding=10)
        self.nb.add(self.drives_tab, text='Drive Outputs')
        self.drive_outputs = DriveOutputs(self.drives_tab, self)

        # create the dc motors tab
        self.motors_tab = Frame(self.nb, padding=10)
        self.nb.add(self.motors_tab, text='DC Motors')
        self.dc_motors = DcMotors(self.motors_tab, self)

        # create the servo motors tab
        self.servos_tab = Frame(self.nb, padding=10)
        self.nb.add(self.servos_tab, text='Servo Motors')
        self.servos = Servos(self.servos_tab, self)

        # create the stepper motors tab
        self.steppers_tab = Frame(self.nb, padding=10)
        self.nb.add(self.steppers_tab, text='Stepper Motors')
        self.stepper_motors = Steppers(self.steppers_tab, self)

        # create the stepper motors tab
        self.neopixels_tab = Frame(self.nb, padding=10)
        self.nb.add(self.neopixels_tab, text='NeoPixels')
        self.stepper_motors = NeoPixels(self.neopixels_tab, self)

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
        pin = payload['pin']
        value = payload['value']
        timestamp = payload['timestamp']
        if 0 <= pin < 8:
            self.signal_inputs.set_input_value(pin, value)
            self.signal_inputs.set_time_stamp_value(pin, timestamp)
        if 8 <= pin < 12:
            # we subtract eight to normalize the pin number
            self.touch_inputs.set_input_value(pin - 8, value)
            self.touch_inputs.set_time_stamp_value(pin - 8, timestamp)

    def on_closing(self):
        """
        Destroy the window
        """
        self.clean_up()
        self.main.destroy()


# noinspection PyPep8
class SignalInputs:
    """
    This class creates a Signal Inputs labelframe
    on the parent notebook page, and also
    provides control for its components
    """

    # modes
    DIGITAL_INPUT = 0
    DIGITAL_PULL_UP = 1
    ANALOG = 2

    def __init__(self, notebook_page, caller):
        """
        Create the and place the widgets in the frame
        for user Signal input interaction.

        :param notebook_page: Notebook page to contain this frame
        :param caller: class instantiating this class
        """

        self.caller = caller

        # A set of arrays to manage the user selected modes,
        # and reported values and timestamps for each of the
        # 8 signals

        # an array of StringVariables, one for each mode control
        self.modes = []

        # an array of the 8 mode combobox controls
        self.modes_controls = []

        # an array of value entry controls that hold the returned values
        self.values = []

        # an array of time stamp entry controls that hold the returned
        # timestamps
        self.time_stamps = []

        # the set of mode choices in the mode selection combobox
        self.selections = ['Select Mode', 'Digital',
                           'Digital Pull-Up', 'Analog']

        # create the frame
        self.signal_inputs_frame = Frame(notebook_page, padding=10,
                                         relief=SUNKEN)

        # create the controls for each of the 8 signals
        for x in range(1, 9):
            # set the mode label with an associated signal channel number
            l = Label(self.signal_inputs_frame,
                      text=('Signal ' + str(x) + ' Mode: '))
            l.grid(row=x, column=0)

            # append a StringVar to provide access to the users
            # selection in the modes combo box that follows.
            self.modes.append(StringVar())

            # Create the modes selection combobox.
            # Need to adjust index by -1
            self.modes_box = Combobox(self.signal_inputs_frame,
                                      textvariable=self.modes[x - 1],
                                      values=self.selections)
            self.modes_box.bind('<<ComboboxSelected>>', self.mode_selection)
            self.modes_box.grid(row=x, column=1, pady=3, padx=3)
            self.modes_box.current(0)
            self.modes_controls.append(self.modes_box)

            # add widget to array
            self.modes.append(self.modes_box)

            # create the next label for the value entry field
            l = Label(self.signal_inputs_frame, text=' Value:')
            l.grid(row=x, column=2, padx=[20, 5])

            # create a read only entry field for each signal report
            # and set its value to 0
            value = Entry(self.signal_inputs_frame, state='readonly', width=6)
            value.configure({'readonlybackground': 'white'})
            self.values.append(value)
            value.grid(row=x, column=3, pady=3, padx=3)
            self.set_input_value(x - 1, '')

            # create a time stamp label for the timestamp entry field
            # and set its value to empty
            l = Label(self.signal_inputs_frame, text=' Time Stamp:')
            l.grid(row=x, column=4, padx=[20, 5])

            # create a read only entry field for each time stamp
            time_stamp = Entry(self.signal_inputs_frame, state='readonly',
                               width=20)
            time_stamp.configure({'readonlybackground': 'white'})
            self.time_stamps.append(time_stamp)

            time_stamp.grid(row=x, column=5, pady=3, padx=3)
            self.set_time_stamp_value(x - 1, '')

            # grid the label frame and sets its position

            self.signal_inputs_frame.grid(row=0, column=0, sticky='EW',
                                          columnspan=49, padx=25, pady=[10, 0])

    def mode_selection(self, event):
        payload = {}
        # control_index = selection_index = None
        if event.widget in self.modes_controls:
            if event.widget.get() in self.selections:
                pin = self.modes_controls.index(event.widget)
                # need to decrease by 1 = first selection in combobox is
                # 'Select Mode'
                selection_index = self.selections.index(event.widget.get()) - 1
                if selection_index == self.DIGITAL_INPUT:
                    payload = {'command': 'set_mode_digital_input', 'pin': pin}
                elif selection_index == self.DIGITAL_PULL_UP:
                    payload = {'command': 'set_mode_digital_input_pullup',
                               'pin': pin}
                else:
                    payload = {'command': 'set_mode_analog_input', 'pin': pin}

            topic = 'to_hardware'
            self.caller.publish_payload(payload, topic)

    def set_input_value(self, channel, value):
        """
        Set an input value field for the specified signal channel
        to the value specified
        :param channel: 0-7
        :param value: value to be displayed
        :return:
        """
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
class SignalOutputs:
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

        self.caller = caller

        # an array of StringVariables, one for each mode control
        self.values = []

        # an array of the 8 mode combobox controls
        self.values_controls = []

        # selections for values combobox
        self.selections = ['Select Output Value', '0', '1']

        # create the frame
        self.signal_outputs_frame = Frame(notebook_page, padding=10,
                                          relief=SUNKEN)

        # create the controls for each of the 8 signals
        for x in range(1, 9):
            # set the mode label with an associated signal channel number
            l = Label(self.signal_outputs_frame,
                      text=('Signal ' + str(x) + ' Output Value: '))
            l.grid(row=x, column=0, padx=[20, 3])

            self.values.append(StringVar())

            # Create the modes selection combobox.
            # Need to adjust index by -1
            self.values_box = Combobox(self.signal_outputs_frame,
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

            self.signal_outputs_frame.grid(row=0, column=0, sticky='EW',
                                           columnspan=49,
                                           padx=200, pady=[20, 0])

    def value_selection(self, event):
        if event.widget in self.values:
            if event.widget.get() in self.selections:
                pin = self.values_controls.index(event.widget)
                # need to decrease by 1
                value = self.selections.index(event.widget.get()) - 1
                topic = 'to_hardware'
                payload = {'command': 'set_mode_digital_output',
                           'pin': pin}
                self.caller.publish_payload(payload, topic)
                payload = {'command': 'digital_write', 'pin': pin, 'value': value}
                self.caller.publish_payload(payload, topic)


# noinspection PyPep8,PyPep8
class TouchInputs:
    """
    This class creates a Touch Inputs labelframe
    on the parent notebook page, and also
    provides control for its components.

    We will map the touch pin numbers as follows:
    1 - 8
    2 - 9
    3 - 10
    4 - 11

    The reason for this is that for messaging purposes, we will
    treat the touch pins as digital input pins and adjust the mapping
    accordingly in the gateway.
    """

    def __init__(self, notebook_page, caller):
        """
        Create the and place the widgets in the frame
        for user Signal input interaction.

        :param notebook_page: Notebook page to contain this frame
        :param caller: class instantiating this class
        """

        self.caller = caller

        # A set of arrays to manage the user selected modes,
        # and reported values and timestamps for each of the
        # 8 signals

        # an array of value entry controls that hold the returned values
        self.values = []

        # an array of time stamp entry controls that hold the returned
        # timestamps
        self.time_stamps = []

        # create the frame
        self.touch_inputs_frame = Frame(notebook_page, padding=10,
                                        relief=SUNKEN)

        # create the controls for each of the 8 signals
        for x in range(1, 5):
            # set the mode label with an associated signal channel number
            l = Label(self.touch_inputs_frame,
                      text=('Touch ' + str(x) + ' Value'))
            l.grid(row=x, column=2, padx=[20, 5])

            # create a read only entry field for each signal report
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

            # create a read only entry field for each time stamp
            time_stamp = Entry(self.touch_inputs_frame, state='readonly',
                               width=20)
            time_stamp.configure({'readonlybackground': 'white'})
            self.time_stamps.append(time_stamp)

            time_stamp.grid(row=x, column=5, pady=3, padx=3)
            self.set_time_stamp_value(x - 1, '')

            # add an enable touch button
            b = Button(self.touch_inputs_frame, text='Enable Touch',
                       command=self.enable_touch)
            b.focus_set()
            b.grid(row=55, column=45, pady=[30, 5], padx=[0, 30])

            # grid the label frame and sets its position

            self.touch_inputs_frame.grid(row=0, column=0, sticky='EW',
                                         columnspan=49, padx=[95, 10],
                                         pady=30)

    def set_input_value(self, channel, value):
        """
        Set an input value field for the specified signal channel
        to the value specified
        :param channel: 0-7
        :param value: value to be displayed
        :return:
        """
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

    def enable_touch(self):
        """
        Enable digital input for virtual pins 8 through 11
        :return:
        """
        topic = 'to_hardware'
        for pin in range(8, 12):
            payload = {'command': 'set_mode_digital_input', 'pin': pin}
            self.caller.publish_payload(payload, topic)


class DriveOutputs:
    """
    This class creates a Drive Outputs frame
    on the parent notebook page, and also
    provides control for its components.


    We will map the drive pin numbers as follows:
    1 - 12
    2 - 13
    3 - 14
    4 - 15
    """

    def __init__(self, notebook_page, caller):
        self.drive_outputs_frame = Frame(notebook_page, padding=10,
                                         relief=SUNKEN)

        self.caller = caller

        # an array of the execute buttons
        self.execute_buttons = []

        # an array of the scale widgets
        self.drive_scales = []

        # an array of the values for the scale widgets
        self.drive_values = []

        for x in range(0, 4):
            # set the mode label with an associated signal channel number
            # noinspection PyPep8
            l = Label(self.drive_outputs_frame,
                      text=('Drive ' + str(x + 1) + ' Value:'))
            l.grid(row=x, column=0, padx=[20, 5], pady=[22, 0])

            self.drive_values.append(DoubleVar())

            drive_scale = Scale(self.drive_outputs_frame,
                                variable=self.drive_values[x],
                                orient='horizontal', troughcolor='white',
                                resolution=0.01, from_=0.00, to=1.00)
            self.drive_scales.append(drive_scale)

            drive_scale.grid(row=x, column=1)

            b = Button(self.drive_outputs_frame,
                       text='Set Drive ' + str(x + 1) + ' Value',
                       command=partial(self.set_drive_value, x))
            self.execute_buttons.append(b)
            b.grid(row=x, column=2, pady=[22, 0], padx=40)

        self.drive_outputs_frame.grid(row=0, column=0, sticky='EW',
                                      columnspan=49, padx=[170, 0],
                                      pady=[20, 0])

    def set_drive_value(self, index):
        # normalize pin number for drives
        pin = index
        value = self.drive_scales[index].get()
        topic = 'to_hardware'

        payload = {'command': 'set_mode_pwm', 'pin': pin}
        self.caller.publish_payload(payload, topic)

        payload = {'command': 'pwm_write', 'pin': pin, 'value': value}
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


# noinspection PyPep8
class Servos:
    """
    This class creates a Servos frame
    on the parent notebook page, and also
    provides control for its components.
    """

    def __init__(self, notebook_page, caller):
        self.servos_frame = Frame(notebook_page, padding=10,
                                  relief=SUNKEN)

        self.caller = caller

        # an array of the execute buttons
        self.execute_buttons = []

        # an array of the scale widgets
        self.servo_scales = []

        # an array of the values for the scale widgets
        self.servo_values = []

        for x in range(0, 4):
            # set the mode label with an associated signal channel number
            l = Label(self.servos_frame,
                      text=('Servo ' + str(x + 1) + ' Angle:'))
            l.grid(row=x, column=0, padx=[20, 5], pady=[22, 0])

            self.servo_values.append(DoubleVar())

            servo_scale = Scale(self.servos_frame,
                                variable=self.servo_values[x],
                                orient='horizontal', troughcolor='white',
                                from_=0, to=180)
            self.servo_scales.append(servo_scale)

            servo_scale.grid(row=x, column=1)

            b = Button(self.servos_frame,
                       text='Move Servo ' + str(x + 1),
                       command=partial(self.set_servo_value, x))
            self.execute_buttons.append(b)
            b.grid(row=x, column=2, pady=[22, 0], padx=40)

        self.servos_frame.grid(row=0, column=0, sticky='EW',
                               columnspan=49, padx=[170, 0],
                               pady=[20, 0])

    def set_servo_value(self, index):
        # normalize pin number for drives

        value = self.servo_scales[index].get()
        topic = 'to_hardware'
        payload = {'command': 'set_mode_servo', 'pin': index}
        self.caller.publish_payload(payload, topic)

        payload = {'command': 'servo_position', "pin": index, 'position': value}
        self.caller.publish_payload(payload, topic)


class Steppers:
    """
    This class creates a Stepper Motor frame
    on the parent notebook page, and also
    provides control for its components.

    """

    def __init__(self, notebook_page, caller):
        self.steppers_frame = Frame(notebook_page, padding=10,
                                    relief=SUNKEN)

        self.caller = caller

        # the set of mode choices in the mode selection combobox
        self.style_selections = ['Single', 'Double', 'Interleave']

        # an array of the execute buttons
        self.forward_buttons = []
        self.reverse_buttons = []

        # an array of the scale widgets
        self.stepper_scales = []

        # an array of the values for the scale widgets
        self.stepper_values = []

        # an array of spinbox style widgets
        self.stepper_styles = []

        # an array of style values
        self.stepper_style_values = []

        # an array of the number of steps widgets
        self.stepper_steps = []

        # an array of the values for the # of steps
        self.number_of_steps = []

        self.directions = []

        for x in range(0, 2):
            # set the mode label with an associated signal channel number
            if x == 0:
                l = Label(self.steppers_frame,
                          text='Inter Step Delay(Drive):')
                l.grid(row=x, column=0, padx=[5, 5], pady=[22, 0])
            else:
                l = Label(self.steppers_frame,
                          text='Inter Step Delay:')
                l.grid(row=x, column=0, padx=[45, 0], pady=[22, 0], sticky='W')

            self.stepper_values.append(DoubleVar())

            servo_scale = Scale(self.steppers_frame,
                                variable=self.stepper_values[x],
                                orient='horizontal', troughcolor='white',
                                resolution=0.0001, from_=0.00, to=0.10)
            self.stepper_scales.append(servo_scale)

            servo_scale.grid(row=x, column=1)

            l = Label(self.steppers_frame, text='Style: ')
            l.grid(row=x, column=2, padx=[10, 0], pady=[22, 0], sticky='W')

            self.stepper_style_values.append(StringVar())

            # Create the modes selection combobox.
            # Need to adjust index by -1
            self.styles_box = Combobox(self.steppers_frame,
                                       textvariable=self.stepper_style_values[
                                           x],
                                       values=self.style_selections, width=8)
            self.styles_box.grid(row=x, column=3, pady=[22, 0], padx=3)
            self.styles_box.current(0)
            self.stepper_styles.append(self.styles_box)

            l = Label(self.steppers_frame, text='# of steps: ')
            l.grid(row=x, column=4, padx=[10, 0], pady=[22, 0], sticky='W')

            self.number_of_steps.append(IntVar())
            self.number_of_steps[x].set(100)
            self.steps_spinner = Spinbox(self.steppers_frame, from_=0, to=1000,
                                         width=5,
                                         textvariable=self.number_of_steps[x])

            self.steps_spinner.grid(row=x, column=5, pady=[22, 0])
            # add widget to array
            self.stepper_steps.append(self.steps_spinner)

            b = Button(self.steppers_frame,
                       text='Forward',
                       command=partial(self.move_forward, x))
            self.forward_buttons.append(b)
            b.grid(row=x, column=6, pady=[22, 0], padx=[20, 10])

            b = Button(self.steppers_frame,
                       text='Reverse',
                       command=partial(self.move_reverse, x))
            self.reverse_buttons.append(b)
            b.grid(row=x, column=7, pady=[22, 0], padx=[10, 5])

        self.steppers_frame.grid(row=0, column=0, sticky='EW',
                                 columnspan=49,
                                 pady=[50, 0])

    def move_forward(self, index):
        speed = self.stepper_scales[index].get()
        style = self.stepper_styles[index].get()
        steps = self.stepper_steps[index].get()
        topic = 'to_hardware'

        if index == 0:
            payload = {'command': 'stepper_drive_forward',
                       'style': style,
                       'steps': steps,
                       'speed': speed
                       }
        else:
            payload = {'command': 'stepper_forward',
                       'style': style,
                       'steps': steps,
                       'speed': speed
                       }

        self.caller.publish_payload(payload, topic)

    def move_reverse(self, index):
        speed = self.stepper_scales[index].get()
        style = self.stepper_styles[index].get()
        steps = self.stepper_steps[index].get()
        topic = 'to_hardware'

        if index == 0:
            payload = {'command': 'stepper_drive_reverse',
                       'style': style,
                       'steps': steps,
                       'speed': speed
                       }
        else:
            payload = {'command': 'stepper_reverse',
                       'style': style,
                       'steps': steps,
                       'speed': speed
                       }

        self.caller.publish_payload(payload, topic)


class NeoPixels:
    def __init__(self, notebook_page, caller):
        self.neopixels_frame = Frame(notebook_page, padding=10,
                                     relief=SUNKEN)

        self.caller = caller

        self.max_pixels = 8

        # number of pixels
        l = Label(self.neopixels_frame, text='Number Of Pixels:')
        l.grid(row=0, column=0, pady=[22, 22])

        self.number_of_pixels_var = IntVar()
        self.number_of_pixels_var.set(8)

        self.num_pixels_spinner = Spinbox(self.neopixels_frame, from_=0,
                                          to=1000,
                                          width=4,
                                          textvariable=self.number_of_pixels_var,
                                          command=self.limit_pixel_position)
        self.num_pixels_spinner.grid(row=0, column=1, )

        # pixel position

        l = Label(self.neopixels_frame, text='Pixel Position:')
        l.grid(row=1, column=0, padx=[5, 0], sticky='E')

        self.pixel_position_var = IntVar()
        self.pixel_position_var.set(0)

        self.pixel_position_spinner = Spinbox(self.neopixels_frame, from_=0,
                                              to=self.max_pixels,
                                              width=4,
                                              textvariable=self.pixel_position_var)

        self.pixel_position_spinner.grid(row=1, column=1, pady=[10, 10])

        # red value
        l = Label(self.neopixels_frame, text='   R:')
        l.grid(row=1, column=2, padx=[10, 5])

        self.r_var = IntVar()
        self.r_var.set(128)

        self.r_spinner = Spinbox(self.neopixels_frame, from_=0,
                                 to=255,
                                 width=4,
                                 textvariable=self.r_var)

        self.r_spinner.grid(row=1, column=3, pady=[10, 10], sticky='W')

        # green value
        l = Label(self.neopixels_frame, text='   G:')
        l.grid(row=1, column=4, padx=[10, 5])

        self.g_var = IntVar()
        self.g_var.set(128)

        self.g_spinner = Spinbox(self.neopixels_frame, from_=0,
                                 to=255,
                                 width=5,
                                 textvariable=self.g_var)

        self.g_spinner.grid(row=1, column=5, pady=[10, 10], sticky='W')

        l = Label(self.neopixels_frame, text='   B:')
        l.grid(row=1, column=6, padx=[10, 5])

        self.b_var = IntVar()
        self.b_var.set(128)

        self.b_spinner = Spinbox(self.neopixels_frame, from_=0,
                                 to=255,
                                 width=4,
                                 textvariable=self.b_var)

        self.b_spinner.grid(row=1, column=7, pady=[10, 10], sticky='W')

        # execute button

        b = Button(self.neopixels_frame,
                   text='Set Pixel',
                   command=self.set_pixel)
        b.grid(row=1, column=8, padx=[80, 10], sticky='W', )

        self.neopixels_frame.grid(row=0, column=0, sticky='EW',
                                  columnspan=49,
                                  pady=[50, 0], padx=[50, 0])

    def limit_pixel_position(self):
        self.pixel_position_spinner.config(to=(self.number_of_pixels_var.get()) - 1)

    def set_pixel(self):
        """

        :return:
        """
        num_pixels = self.number_of_pixels_var.get()
        pixel_position = self.pixel_position_var.get()
        r = self.r_var.get()
        g = self.g_var.get()
        b = self.b_var.get()

        topic = 'to_hardware'
        payload = {'command': 'set_pixel', 'number_of_pixels': num_pixels,
                   'pixel_position': pixel_position, 'red': r, 'green': g,
                   'blue': b}

        self.caller.publish_payload(payload, topic)


def crickit_demo():
    parser = argparse.ArgumentParser()

    parser.add_argument("-b", dest="back_plane_ip_address", default="None",
                        help="None or IP address used by Back Plane")
    # allow the user to specify a name for the component and have it shown on
    # the console banner.
    # modify the default process name to one you wish to see on the banner.
    # change the default in the derived class to set the name

    parser.add_argument("-n", dest="process_name", default="CrickitGui",
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
    app = CrickitGui(**kw_options)

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
    crickit_demo()
