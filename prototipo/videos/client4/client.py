import socket                   # Import socket module
from sys import argv
from random import randint
from subprocess import call
from datetime import datetime
s = socket.socket()             # Create a socket object
host = argv[1]     # Get local machine name
port = int(argv[2])                    # Reserve a port for your service.

call('echo \"Attempting to connect at '+str(datetime.now())+' \" >> output.txt &', shell=True)
s.connect((host, port))
s.send("Hello server!")

with open(str(randint(0,10000)), 'wb') as f:
    print 'file opened'
    while True:
        print('receiving data...')
        data = s.recv(1024)
        print('receiving')
        if not data:
            break
        f.write(data)

f.close()
print('Successfully get the file')
s.close()
print('connection closed')