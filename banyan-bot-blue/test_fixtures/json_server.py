
# desc: simple demonstration of a server application that uses RFCOMM sockets

#

# $Id: rfcomm-server.py 518 2007-08-10 07:20:07Z albert $



from bluetooth import *



import json



server_sock=BluetoothSocket( RFCOMM )

server_sock.bind(("",PORT_ANY))

server_sock.listen(1)



port = server_sock.getsockname()[1]



# uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"

uuid = "e35d6386-1802-414f-b2b9-375c92fa23e0"



advertise_service( server_sock, "SampleServer",

                   service_id = uuid,

                   service_classes = [ uuid, SERIAL_PORT_CLASS ],

                   profiles = [ SERIAL_PORT_PROFILE ],

#                   protocols = [ OBEX_UUID ]

                    )



print("Waiting for connection on RFCOMM channel %d" % port)



client_sock, client_info = server_sock.accept()

print("Accepted connection from ", client_info)



try:

    while True:

        data = client_sock.recv(1024)
        data = data.decode()

        if len(data) == 0: break

        # print("received [%s]" % data)

        datax = json.loads(data)

        print(datax)

except IOError:

    pass



print("disconnected")



client_sock.close()

server_sock.close()

print("all done")



A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A
A

