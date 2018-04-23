import socket                   # Import socket module
from sys import argv
s = socket.socket()             # Create a socket object
host = argv[1]     # Get local machine name
port = int(argv[2])                    # Reserve a port for your service.

s.connect((host, port))
s.send("Hello server!")

with open('received_file', 'wb') as f:
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