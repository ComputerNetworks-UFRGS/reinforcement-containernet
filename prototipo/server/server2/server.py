#!/usr/bin/python3
# Usage: python3 server.py myIp port

import socket
from sys import argv
import threading
from psutil import cpu_percent
from os import path, remove
from random import randint
from subprocess import Popen

listenCPU_port = 60000
listenConvert_port = int(argv[2])

class CPU(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        port = listenCPU_port
        ip = argv[1]
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            serversocket.bind((ip, port))   
        except socket.error as msg:
            print ('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            exit(-2)  
        serversocket.listen(socket.SOMAXCONN) # 128                                           
        while True:
            client, address = serversocket.accept()
            cpu = str(cpu_percent(interval=2.0)).encode()
            client.sendall(cpu)
            client.close()

class Convert(threading.Thread):
    def __init__(self,client_socket, client_addr):
        threading.Thread.__init__(self)
        self.client = client_socket
        self.clientAdd = client_addr
    def run(self):
        print("Got a connection from %s..." % str(self.clientAdd))    
        data = self.client.recv(1024)
        filename = str(randint(0,100000))
        while path.isfile(filename): filename = str(randint(0,123456789012345678901234567890))
        newfile=open(filename+".avi",'wb')
        while data:
            newfile.write(data)
            data = self.client.recv(1024)
        newfile.close()
        remove(filename+".avi")


if __name__ == '__main__':
    if len(argv) < 2: exit(-1)

    threadCPU = CPU()
    threadCPU.start()

    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip = argv[1]
    port = listenConvert_port

    try:
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind((ip, port))   
    except socket.error as msg:
        print ('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
        exit(-2)                               

    serversocket.listen(socket.SOMAXCONN) # 128                                           
    while True:
        clientsocket, addr = serversocket.accept()
        threadConvert = Convert(clientsocket, addr)
        threadConvert.start()