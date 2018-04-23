#!/usr/bin/python3
# Usage: python3 addServer.py orchestratorIP serverName serverIP serverSwitch
# python3 client.py "127.0.0.1" "d2" "10.245" "s3"

import socket
from sys import argv


if __name__ == '__main__':
    if len(argv) < 2: exit(-1)
    s = socket.socket()

    orchestrator = argv[1]
    port = 50007

    s.connect((orchestrator, port))
    data = argv[2]+"|"+argv[3]+"|"+argv[4]
    s.send(data.encode())
    s.shutdown(socket.SHUT_WR)
    s.close()
