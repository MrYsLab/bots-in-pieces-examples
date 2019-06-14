"""
#!/usr/bin/env python3

 Copyright (c) 2017-2019 Alan Yorinks All right reserved.

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

import bluetooth


"""
This file is used to validate an Android Bluetooth enabled APK.

It will send a single message to the android upon connection.

It also will also continuously receive data from the Bluetooth
socket and print that data to the console.
"""


print('Waiting for client to connect...')
server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

port = 1
server_sock.bind(("", port))
server_sock.listen(1)

client_sock, address = server_sock.accept()

print("Accepted connection from ", address)
data = 'Hello Banyan Bot'
data = data.encode()
client_sock.send(data)

while True:
    data = (client_sock.recv(1024)).decode()
    print("received [%s]" % data)
