import socket                   # Import socket module
import threading
from sys import argv
from subprocess import call
from datetime import datetime
#python server myip port file
port = int(argv[2])                    # Reserve a port for your service.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)             # Create a socket object
host = argv[1]     # Get local machine name
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((host, port))            # Bind to the port
s.listen(socket.SOMAXCONN)                     # Now wait for client connection.

class Convert(threading.Thread):
    def __init__(self,client_socket, client_addr):
        threading.Thread.__init__(self)
        self.client = client_socket
        self.clientAdd = client_addr
    def run(self):
        #print "Got a connection from %s..." % str(self.clientAdd)
        call('echo \"Got a connection from'+str(self.clientAdd)+' at '+str(datetime.now())+' \" >> output.txt &', shell=True)
        data = self.client.recv(1024)
        filename=argv[3]
        f = open(filename,'rb')
        l = f.read(1024)
        while (l):
            self.client.send(l)
            l = f.read(1024)
        f.close()
        self.client.close()

while True:
    conn, addr = s.accept()     # Establish connection with client.
    threadConvert = Convert(conn, addr)
    threadConvert.start()

    
