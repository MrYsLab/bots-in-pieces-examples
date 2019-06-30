#!/usr/bin/env python3

"""
traffic_generator.py

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
import time

import msgpack
import msgpack_numpy as m
import zmq
from python_banyan.banyan_base import BanyanBase


class MessageInjector(BanyanBase):
    """
    This class will generate Banyan test messages and subscribe
    to receive test messages. If set to continuous mode, a message
    will be sent at a rate of 1 per second.

    usage: message_injector.py [-h]
                           [-a SUBSCRIPTION_TOPICS [SUBSCRIPTION_TOPICS ...]]
                           [-b BACK_PLANE_IP_ADDRESS] [-c PUBLISH_TOPIC]
                           [-f MESSAGE_FREQUENCY] [-m MSG_TYPE]
                           [-n PROCESS_NAME] [-p PUBLISHER_PORT]
                           [-s SUBSCRIBER_PORT] [-t LOOP_TIME]

        optional arguments:
          -h, --help            show this help message and exit
          -a SUBSCRIPTION_TOPICS [SUBSCRIPTION_TOPICS ...]
                                Banyan topics space delimited: topic1 topic2 topic3
          -b BACK_PLANE_IP_ADDRESS
                                None or IP address used by Back Plane
          -c PUBLISH_TOPIC      Publishing Topic
          -f MESSAGE_FREQUENCY  Message Output Frequency: c=continuous s=single shot
          -m MSG_TYPE           Message Injection Type: s=string d=dictionary
          -n PROCESS_NAME       Set process name in banner
          -p PUBLISHER_PORT     Publisher IP port
          -s SUBSCRIBER_PORT    Subscriber IP port
          -t LOOP_TIME          Event Loop Timer in seconds


    """

    def __init__(self, **kwargs):

        """
        kwargs is a dictionary that will contain the following keys:

        :param back_plane_ip_address: banyan_base back_planeIP Address -
                                    if not specified, it will be set to the
                                    local computer
        :param subscriber_port: banyan_base back plane subscriber port.
               This must match that of the banyan_base backplane
        :param publisher_port: banyan_base back plane publisher port.
                               This must match that of the
                               banyan_base backplane.
        :param number_of_messages: number of message to transmit
        :param process_name: Component identifier
        :param loop_time: receive loop sleep time
        :param msg_type: single character or python dictionary
        :param message_frequency: single message or continuous transmission
        """

        # initialize the parent
        super(MessageInjector, self).__init__(
            back_plane_ip_address=kwargs['back_plane_ip_address'],
            subscriber_port=kwargs['subscriber_port'],
            publisher_port=kwargs['publisher_port'],
            process_name=kwargs['process_name'],
            loop_time=kwargs['loop_time'],
        )

        # set the process name for the banner
        self.process_name = kwargs['process_name'],

        # subscribe to the topics in the subscription topics list
        if kwargs['subscription_topics'] is not None:
            for topic in kwargs['subscription_topics']:
                self.set_subscriber_topic(topic)
                print('Subscribed to: ', topic)

        # get the publishing topic
        self.publisher_topic = kwargs['publish_topic']
        print('Publishing to: ', self.publisher_topic)

        self.loop_time = kwargs['loop_time']

        # save the message type - default is dictionary
        self.msg_type = kwargs['msg_type']

        # save how often to publish - default is continuous
        self.message_frequency = kwargs['message_frequency']

        # a count used as in the message payload as data
        self.count = 0

        # start the receive loop
        try:
            self.receive_loop()
        except KeyboardInterrupt:
            self.clean_up()
            sys.exit(0)

    def receive_loop(self):
        """
        This is the receive loop for Banyan messages.

        Messages will be published when there are no
        messages available to process, so we need
        to overwrite the base class method to do this.
        """
        while True:
            try:
                data = self.subscriber.recv_multipart(zmq.NOBLOCK)
                if self.numpy:
                    payload2 = {}
                    payload = msgpack.unpackb(data[1], object_hook=m.decode)
                    # convert keys to strings
                    # this compensates for the breaking change in
                    # msgpack-numpy 0.4.1 to 0.4.2
                    for key, value in payload.items():
                        if not type(key) == str:
                            key = key.decode('utf-8')
                            payload2[key] = value

                    if payload2:
                        payload = payload2
                    self.incoming_message_processing(data[0].decode(), payload)
                else:
                    self.incoming_message_processing(data[0].decode(),
                                                     msgpack.unpackb(data[1],
                                                                     raw=False))
            # if no messages are available, zmq throws this exception
            except zmq.error.Again:
                # single shot
                if self.message_frequency == 's':
                    # just send a single message
                    if self.count > 0:
                        pass
                try:
                    # if message type is dictionary
                    if self.msg_type == 'd':
                        payload = {'report': self.count}
                    # else send as a string
                    else:
                        payload = str(self.count)

                    # bump the count for the next potential message
                    self.count += 1

                    # publish the message
                    self.publish_payload(payload, self.publisher_topic)

                    # sleep for a second
                    time.sleep(1)
                except KeyboardInterrupt:
                    self.clean_up()
                    raise KeyboardInterrupt

    def incoming_message_processing(self, topic, payload):
        """
        Messages are sent here from the receive_loop
        :param topic: Message Topic string
        :param payload: Message Data
        """
        # just print the message
        print(topic, payload)


def message_injector():
    parser = argparse.ArgumentParser()
    # allow user to bypass the IP address auto-discovery.
    # This is necessary if the component resides on a computer
    # other than the computing running the backplane.

    parser.add_argument("-a", dest="subscription_topics",
                        default=["from_bt_gateway"], nargs="+",
                        help="Banyan topics space delimited: topic1 topic2 "
                             "topic3"),
    parser.add_argument("-b", dest="back_plane_ip_address", default="None",
                        help="None or IP address used by Back Plane"),
    parser.add_argument("-c", dest="publish_topic",
                        default="to_bt_gateway",
                        help="Publishing Topic"),
    parser.add_argument("-f", dest="message_frequency", default="c",
                        help="Message Output Frequency: c=continuous  s=single shot")
    parser.add_argument("-m", dest="msg_type", default="d",
                        help="Message Injection Type: s=string  d=dictionary")
    parser.add_argument("-n", dest="process_name",
                        default="MessageInjector",
                        help="Set process name in banner")
    parser.add_argument("-p", dest="publisher_port", default='43124',
                        help="Publisher IP port")
    parser.add_argument("-s", dest="subscriber_port", default='43125',
                        help="Subscriber IP port")
    parser.add_argument("-t", dest="loop_time", default=".1",
                        help="Event Loop Timer in seconds")

    args = parser.parse_args()

    if args.back_plane_ip_address == 'None':
        args.back_plane_ip_address = None
    kw_options = {'back_plane_ip_address': args.back_plane_ip_address,
                  'publisher_port': args.publisher_port,
                  'subscriber_port': args.subscriber_port,
                  'process_name': args.process_name,
                  'loop_time': float(args.loop_time),
                  'subscription_topics': args.subscription_topics,
                  'publish_topic': args.publish_topic,
                  'msg_type': args.msg_type,
                  'message_frequency': args.message_frequency}

    app = MessageInjector(**kw_options)

    # signal handler function called when Control-C occurs
    def signal_handler(sig, frame):
        print("Control-C detected. See you soon.")
        app.clean_up()
        sys.exit(0)

    # listen for SIGINT
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


if __name__ == '__main__':
    message_injector()
