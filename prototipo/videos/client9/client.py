#!/usr/bin/python3
# Usage: python3 client.py serverIp video
# python3 client.py "10.0.1.2" "input" "55555"
import socket
from sys import argv, exit


if __name__ == '__main__':
    if len(argv) < 3: exit(-1)
    s = socket.socket()

    host = argv[1]
    port = int(argv[3])

    s.connect((host, port))
    f = open(argv[2]+".avi",'rb')
    print('Sending...')
    l = f.read(1024)
    while (l):
        print('Sending...')
        s.send(l)
        l = f.read(1024)
    f.close()
    s.shutdown(socket.SHUT_WR)
    s.close()
    print("sent")
