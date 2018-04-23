#!/usr/bin/python3
# Usage: python3 cpu_info.py serverIp video
# python3 client.py "10.0.0.2"
import socket
from sys import argv


def get_cpu():
    if len(argv) < 2: exit(-1)
    s = socket.socket()

    host = argv[1]
    port = 60000

    s.connect((host, port))
    s.send("CPU".encode())
    s.shutdown(socket.SHUT_WR)
    
    data = s.recv(1024)
    print(data.decode('utf-8'))
    s.close()

if __name__ == '__main__':
    get_cpu()