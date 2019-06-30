#!/usr/bin/env python3

"""
blue_tooth_gateway.py

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
import json
import subprocess
import signal
import sys
import subprocess
import threading

from bluetooth import *

from boltons.socketutils import BufferedSocket

from python_banyan.banyan_base import BanyanBase


# noinspection PyMethodMayBeStatic
class BlueToothGateway(BanyanBase, threading.Thread):
    """
    This class implements Bluetooth an RFCOMM server or client,
    configurable from command line options.

    usage: bluetooth_gateway.py [-h] [-a SERVER_BT_ADDRESS]
                            [-b BACK_PLANE_IP_ADDRESS] [-g GATEWAY_TYPE]
                            [-j JSON_DATA] [-l PUBLISH_TOPIC]
                            [-m SUBSCRIBER_LIST [SUBSCRIBER_LIST ...]]
                            [-n PROCESS_NAME] [-p PUBLISHER_PORT]
                            [-s SUBSCRIBER_PORT] [-t LOOP_TIME] [-u UUID]

        optional arguments:
          -h, --help            show this help message and exit
          -a SERVER_BT_ADDRESS  Bluetooth MAC Address of Bluetooth Gateway
          -b BACK_PLANE_IP_ADDRESS
                                None or IP address used by Back Plane
          -g GATEWAY_TYPE       Type of Gateway : server or client
          -j JSON_DATA          Bluetooth packets json encoded True or False
          -l PUBLISH_TOPIC      Banyan publisher topic
          -m SUBSCRIBER_LIST [SUBSCRIBER_LIST ...]
                                Banyan topics space delimited: topic1 topic2 topic3
          -n PROCESS_NAME       Set process name in banner
          -p PUBLISHER_PORT     Publisher IP port
          -s SUBSCRIBER_PORT    Subscriber IP port
          -t LOOP_TIME          Event Loop Timer in seconds
          -u UUID               Bluetooth UUID

    """

    # gateway types
    BTG_SERVER = 0
    BTG_CLIENT = 1

    def __init__(self, back_plane_ip_address=None, subscriber_port='43125',
                 publisher_port='43124', process_name=None, loop_time=.001,
                 gateway_type=BTG_SERVER, publish_topic=None,
                 uuid='e35d6386-1802-414f-b2b9-375c92fa23e0',
                 server_bt_address=None, subscriber_list=None,
                 json_data=False):
        """
        This method initialize the class for operation

        """
        # save input parameters as instance variables
        self.back_plane_ip_address = back_plane_ip_address
        self.subscriber_port = subscriber_port
        self.publisher_port = publisher_port
        self.loop_time = loop_time
        self.gateway_type = gateway_type

        # set the name for the banner depending upon client or server
        if process_name is None:
            if self.gateway_type == self.BTG_CLIENT:
                self.process_name = 'BanyanBluetoothClient'
            else:
                self.process_name = 'BanyanBluetoothServer'
        else:
            self.process_name = process_name

        self.publish_topic = publish_topic

        self.uuid = uuid
        self.server_bt_address = server_bt_address
        self.json_data = json_data

        # initialize the parent

        super(BlueToothGateway, self).__init__(
            back_plane_ip_address=self.back_plane_ip_address,
            subscriber_port=self.subscriber_port,
            publisher_port=self.publisher_port,
            process_name=self.process_name,
            loop_time=self.loop_time)

        self.subscriber_list = subscriber_list

        for topic in self.subscriber_list:
            self.set_subscriber_topic(topic)
            print('Subscribed to: ', topic)

        print('Publish to   : ', self.publish_topic)

        mac = self.find_local_mac_address()
        if mac:
            print('Local Bluetooth MAC Address: ', mac)
        else:
            print('No Bluetooth Interface Found - Exiting')
            sys.exit(0)

        if self.gateway_type == self.BTG_SERVER:
            self.server_sock = BluetoothSocket(RFCOMM)
            self.server_sock.bind(("", PORT_ANY))
            self.server_sock.listen(1)

            port = self.server_sock.getsockname()[1]

            advertise_service(self.server_sock, "BanyanBlueToothServer",
                              service_id=uuid,
                              service_classes=[uuid, SERIAL_PORT_CLASS],
                              profiles=[SERIAL_PORT_PROFILE],
                              )

            print("Waiting for connection on RFCOMM channel %d" % port)

            self.client_sock, self.client_info = self.server_sock.accept()

            print("Accepted connection from ", self.client_info)
        else:
            service_matches = find_service(uuid=self.uuid,
                                           address=self.server_bt_address)

            if len(service_matches) == 0:
                print("Could not find the remote Bluetooth server - exiting")
                sys.exit(0)

            first_match = service_matches[0]
            port = first_match["port"]
            name = first_match["name"]
            host = first_match["host"]

            print("connecting to \"%s\" on %s" % (name, host))

            # Create the client socket
            self.client_sock = BluetoothSocket(RFCOMM)
            self.client_sock.connect((host, port))

        # wrap the socket for both client and server
        self.bsock = BufferedSocket(self.client_sock)

        # create a thread to handle receipt of bluetooth data
        threading.Thread.__init__(self)
        self.daemon = True

        # start the thread
        self.start()

        # this will keep the program running forever
        self.receive_loop()

    def incoming_message_processing(self, topic, payload):
        """
        Process the incoming Banyan message to
        be sent to the Bluetooth network
        :param topic: topic string
        :param payload: payload data
        """

        # if the bluetooth device requires json encoding
        if self.json_data:
            data_out = json.dumps(payload)
            data_out = data_out.encode('utf-8')

            try:
                self.bsock.send(data_out)
            except Exception as e:
                self.clean_up()
                raise RuntimeError('Write Error')
        else:
            # convert the payload to a string
            data_out = str(payload['report'])
            data_out = data_out.encode('utf-8')
            self.client_sock.send(data_out)

    def find_local_mac_address(self):
        """
        Get the local bluetooth mac address
        :return: mac address string or None
        """
        proc = subprocess.Popen(['hcitool', 'dev'],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        data = proc.communicate()

        data = data[0].decode()

        data = data.split('\t')
        if len(data) < 2:
            return None
        else:
            return data[2].strip()

    def run(self):
        """
        This is thread that receives packets from the bluetooth interface
        :return:
        """

        while True:
            # if json encoding look for termination character
            # used for a dictionary
            if self.json_data:
                try:
                    data = self.bsock.recv_until(b'}',
                                                 timeout=0,
                                                 with_delimiter=True)
                except Exception as e:
                    continue

                data = data.decode()
                data = json.loads(data)

                self.publish_payload(data, self.publish_topic)

            # data is not json encoded
            else:
                data = (self.client_sock.recv(1)).decode()
                payload = {'command': data}
                self.publish_payload(payload, self.publish_topic)


def bluetooth_gateway():
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", dest="server_bt_address", default="None",
                        help="Bluetooth MAC Address of Bluetooth Gateway"),
    parser.add_argument("-b", dest="back_plane_ip_address", default="None",
                        help="None or IP address used by Back Plane")
    parser.add_argument("-g", dest="gateway_type", default="server",
                        help="Type of Gateway : server or client"),
    parser.add_argument("-j", dest="json_data", default="False",
                        help="Bluetooth packets json encoded true or false"),
    parser.add_argument("-l", dest="publish_topic", default="from_bt_gateway",
                        help="Banyan publisher topic"),
    parser.add_argument("-m", dest="subscriber_list",
                        default=["None"], nargs="+",
                        help="Banyan topics space delimited: topic1 topic2 "
                             "topic3")
    parser.add_argument("-n", dest="process_name", default="None",
                        help="Set process name in banner")
    parser.add_argument("-p", dest="publisher_port", default='43124',
                        help="Publisher IP port")
    parser.add_argument("-s", dest="subscriber_port", default='43125',
                        help="Subscriber IP port")
    parser.add_argument("-t", dest="loop_time", default=".01",
                        help="Event Loop Timer in seconds")
    parser.add_argument("-u", dest="uuid",
                        default="e35d6386-1802-414f-b2b9-375c92fa23e0",
                        help="Bluetooth UUID")

    args = parser.parse_args()

    if args.back_plane_ip_address == 'None':
        args.back_plane_ip_address = None
    if args.server_bt_address == 'None':
        args.backplane_ip_address = None
    if args.gateway_type == 'server':
        args.gateway_type = BlueToothGateway.BTG_SERVER
    else:
        args.gateway_type = BlueToothGateway.BTG_CLIENT
    if args.server_bt_address == 'None':
        args.server_bt_address = None
    if args.process_name == 'None':
        args.process_name = None
    if args.subscriber_list == ['None']:
        args.subscriber_list = ['to_bt_gateway']
    if args.json_data == 'False' or args.json_data == 'false':
        args.json_data = False
    else:
        args.json_data = True

    kw_options = {
        'back_plane_ip_address': args.back_plane_ip_address,
        'publisher_port': args.publisher_port,
        'subscriber_port': args.subscriber_port,
        'process_name': args.process_name,
        'json_data': args.json_data,
        'loop_time': float(args.loop_time),
        'publish_topic': args.publish_topic,
        'gateway_type': args.gateway_type,
        'uuid': args.uuid,
        'server_bt_address': args.server_bt_address,
        'subscriber_list': args.subscriber_list
    }

    try:
        app = BlueToothGateway(**kw_options)
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
    bluetooth_gateway()
