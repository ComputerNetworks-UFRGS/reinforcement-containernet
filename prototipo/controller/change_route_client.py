#!/usr/bin/python

# This client is just an example.
# Its functionality must belong to orchestrator.
# python client.py "h1|h4|2"


import socket
from sys import argv


if __name__ == '__main__':
    if len(argv) < 2: exit(-1)
    s = socket.socket()
    host = "127.0.0.1"
    port = 50010
    s.connect((host, port))
    s.send(argv[1])
    s.shutdown(socket.SHUT_WR)
    s.close()
