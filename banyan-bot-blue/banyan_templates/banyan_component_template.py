"""

 Copyright (C) 2019 Alan Yorinks All right reserved.

 This is free software; you can redistribute it and/or
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
from __future__ import unicode_literals

import argparse
import signal
import sys
from python_banyan.banyan_base import BanyanBase


class MyBanyanComponent(BanyanBase):
    """
    This class is a template that you can use to create your
    own Banyan components
    """

    def __init__(self, process_name='None'):
        """

        :param process_name: Name of the component to be
        displayed on the console.
        """

        # Call to super allows this class to be used in multiple inheritance scenarios when needed
        super(MyBanyanComponent, self).__init__(process_name=process_name)

        # add any initialization code you need for your specific component

        # You may wish to subscribe to messages here.
        # Subscribe to as many topic as you wish.
        # Uncomment out the following line and enter your topic.

        # self.set_subscriber_topic('the_topic')

        # You may also publish a message in init or anywhere else.
        # You will need to create a payload, that is in the form
        # of a Python dictionary. When you publish, you will also
        # need to specify

        # The next three lines are a sample of this. Uncomment and
        # modify to your needs, or copy the pattern to any other
        # portion of your component.

        # payload = {'command': 'turn_led_on"}
        # topic = 'gpio_control'
        # self.publish_payload(payload, topic)

        # Start the receive event loop to receive messages for
        # subscribed topics.

        # This will also keep the component alive, even if you have not
        # subscribed to any topics.

        # This should be the last statement in init, since the receive_loop
        # runs in an infinite loop.

        self.receive_loop()

    def incoming_message_processing(self, topic, payload):
        """
        Override this method with a custom Banyan message processor
        for subscribed messages.

        :param topic: Message Topic string.

        :param payload: Message Data.
        """


def my_banyan_component():
    parser = argparse.ArgumentParser()

    parser.add_argument("-n", dest="process_name", default="My Component",
                        help="Set process name in banner")
    args = parser.parse_args()
    kw_options = {
        'process_name': args.process_name,
    }

    try:
        app = MyBanyanComponent(**kw_options)
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
    my_banyan_component()
