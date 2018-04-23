import socket                   # Import socket module
import threading
from sys import argv
#python server myip port
port = int(argv[2])                    # Reserve a port for your service.
s = socket.socket()             # Create a socket object
host = argv[1]     # Get local machine name
s.bind((host, port))            # Bind to the port
s.listen(5)                     # Now wait for client connection.

print 'Server listening....'

class Convert(threading.Thread):
    def __init__(self,client_socket, client_addr):
        threading.Thread.__init__(self)
        self.client = client_socket
        self.clientAdd = client_addr
    def run(self):
        print("Got a connection from %s..." % str(self.clientAdd))
        data = self.client.recv(1024)
        print('Server received', repr(data))
        filename=argv[3]
        f = open(filename,'rb')
        l = f.read(1024)
        while (l):
            self.client.send(l)
            print('Sending ')
            l = f.read(1024)
        f.close()

        print('Done sending')
        self.client.close()

while True:
    conn, addr = s.accept()     # Establish connection with client.
    threadConvert = Convert(conn, addr)
    threadConvert.start()

    
