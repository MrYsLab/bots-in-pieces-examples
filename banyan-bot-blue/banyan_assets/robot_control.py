"""

 Copyright (c) 2016-2019 Alan Yorinks All right reserved.

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

THIS IS A PLACE HOLDER FOR THE ACTUAL CODE TO FOLLOW


"""
from __future__ import unicode_literals

import argparse
import signal
import sys
from python_banyan.banyan_base import BanyanBase


class RobotControl(BanyanBase):
    """
    This class accepts robot commands and translates them
    to motor control messages.

    It also subscribes to receive robot sensor updates to
    autonomously change course if a bumper is hit
    """

    def __init__(self, back_plane_ip_address=None, subscriber_port='43125',
                 publisher_port='43124', process_name=None, loop_time=0.01,
                 publish_to_ui_topic=None,
                 publish_to_hardware_topic=None, subscribe_from_ui_topic=None,
                 subscribe_from_hardware_topic=None, additional_subscriber_list=None,
                 forward_speed=60, turn_speed=20, speed_scale_factor=100):
        """

        :param back_plane_ip_address:
        :param subscriber_port:
        :param publisher_port:
        :param process_name:
        :param loop_time:
        :param publish_to_ui_topic:
        :param publish_to_hardware_topic:
        :param subscribe_from_ui_topic:
        :param subscribe_from_hardware_topic:
        :param additional_subscriber_list:
        :param forward_speed: motor speed to go forward or reverse
        :param turn_speed: turning motor speed
        :param speed_scale_factor: speed multiplier

        """
        # save input parameters as instance variables
        self.back_plane_ip_address = back_plane_ip_address
        self.subscriber_port = subscriber_port
        self.publisher_port = publisher_port
        self.process_name = process_name
        self.loop_time = loop_time
        self.additional_subscriber_list = additional_subscriber_list
        self.forward_speed = forward_speed
        self.turn_speed = turn_speed
        self.speed_scaling_factor = speed_scale_factor

        super(RobotControl, self).__init__(back_plane_ip_address=self.back_plane_ip_address,
                                           process_name=self.process_name,
                                           subscriber_port=self.subscriber_port,
                                           publisher_port=self.publisher_port,
                                           loop_time=self.loop_time)

        self.subscribe_from_ui_topic = subscribe_from_ui_topic
        self.set_subscriber_topic(self.subscribe_from_ui_topic)

        self.subscribe_from_hardware_topic = subscribe_from_hardware_topic
        self.set_subscriber_topic(self.subscribe_from_hardware_topic)
        self.publish_to_hardware_topic = publish_to_hardware_topic
        self.publish_to_ui_topic = publish_to_ui_topic

        # if caller specified a list of additional subscription topics, subscribe to those
        if self.additional_subscriber_list is not None:
            for topic in self.additional_subscriber_list:
                self.set_subscriber_topic(topic)
        self.receive_loop()

    def incoming_message_processing(self, topic, payload):
        """
        Override this method with a custom Banyan message processor
        for subscribed messages.

        :param topic: Message Topic string.

        :param payload: Message Data.
        """
        if topic == self.subscribe_from_ui_topic:
            self.motion_control(payload)
        elif topic == self.subscribe_from_hardware_topic:
            self.avoidance_control(payload)
        else:
            raise RuntimeError('Unknown topic received: ', topic)

    def motion_control(self, payload):
        print('motion', payload)

    def avoidance_control(self, payload):
        print('avoidance', payload)


def robot_control():
    """
    Launcher for robot control
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("-b", dest="back_plane_ip_address", default="None",
                        help="None or IP address used by Back Plane")
    parser.add_argument("-d", dest="publish_to_hardware_topic", default="to_hardware",
                        help="Publishing topic for hardware commands")
    parser.add_argument("-f", dest="forward_speed", default="60",
                        help="Forward and Reverse Motor Speed")
    parser.add_argument("-g", dest="turn_speed", default="20",
                        help="Turning Motor Speed")
    parser.add_argument("-k", dest="speed_scale_factor", default="100",
                        help="Speed scaling factor")
    parser.add_argument("-l", dest="additional_subscriber_list",
                        default=["None"], nargs="+",
                        help="Banyan topics space delimited: topic1 topic2 "
                             "topic3")
    parser.add_argument("-n", dest="process_name", default="Robot Control",
                        help="Set process name in banner")
    parser.add_argument("-p", dest="publisher_port", default='43124',
                        help="Publisher IP port")
    parser.add_argument("-r", dest="publish_to_ui_topic", default="to_ui",
                        help="Publishing topic for report messages")
    parser.add_argument("-s", dest="subscriber_port", default='43125',
                        help="Subscriber IP port")
    parser.add_argument("-t", dest="loop_time", default=".01",
                        help="Event Loop Timer in seconds")
    parser.add_argument("-u", dest="subscribe_from_ui_topic", default="from_ui",
                        help="Topic From User Interface")
    parser.add_argument("-v", dest="subscribe_from_hardware_topic", default="from_hardware",
                        help="Topic From Hardware")

    args = parser.parse_args()
    if args.back_plane_ip_address == 'None':
        args.back_plane_ip_address = None

    if args.process_name == 'None':
        args.process_name = None

    if args.additional_subscriber_list == ['None']:
        args.additional_subscriber_list = None

    kw_options = {
        'back_plane_ip_address': args.back_plane_ip_address,
        'publisher_port': args.publisher_port,
        'subscriber_port': args.subscriber_port,
        'process_name': args.process_name,
        'loop_time': float(args.loop_time),
        'additional_subscriber_list': args.additional_subscriber_list,
        'publish_to_hardware_topic': args.publish_to_hardware_topic,
        'publish_to_ui_topic': args.publish_to_ui_topic,
        'subscribe_from_ui_topic': args.subscribe_from_ui_topic,
        'subscribe_from_hardware_topic': args.subscribe_from_hardware_topic,
        'forward_speed': int(args.forward_speed),
        'turn_speed': int(args.turn_speed),
        'speed_scale_factor': float(args.speed_scale_factor)
    }

    try:
        app = RobotControl(**kw_options)
    except KeyboardInterrupt:
        sys.exit()

    # noinspection PyUnusedLocal
    def signal_handler(sig, frame):
        print("Control-C detected. See you soon.")
        app.clean_up()
        sys.exit(0)

    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == '__main__':
    robot_control()
