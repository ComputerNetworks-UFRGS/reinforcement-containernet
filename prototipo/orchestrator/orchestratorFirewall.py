#!/usr/bin/python

from mininet.net import Containernet
from mininet.topo import Topo
from mininet.node import Controller, Node, RemoteController, Docker, OVSSwitch, CPULimitedHost
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.util import waitListening
from mininet.link import TCLink, Link
import socket
from threading import Thread
from subprocess import call
from sys import argv
import cPickle as pickle
from os import remove, path as caminho
from time import sleep
from enum import Enum # sudo pip install enum

net = Containernet(controller=None, link=TCLink)
linkopts_switches = dict(bw=10, delay='1ms', loss=0, max_queue_size=1000, use_htb=True)
linkopts_hosts = dict(bw=4, delay='1ms', loss=0, max_queue_size=1000, use_htb=True)
hosts = []
listenCopy_port = 50007
listenPaths_port = 50008
listenLinkStatus_port = 50009
timestep = 0

class Traffic_Switches(Enum):
    LOW = 0
    MEDIUM = 600000#900000 # 7,2 MBP/2s
    HIGH =   2000000 # 16 MBP/2s

class Profile(Enum):
    ATTACK = 0
    BALANCE = 1
    REPLICATE = 2


def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper


class Agent:
    def __init__(self):
        self.currentProfile = 1 # 0 - attack, 1 - traffic, 2 - replicate
        self.catalog = []
        self.changeRoute_port = 50010
        self.default_route = {} # default_route[('h1', 'h2')] = [path]
        self.states_traffic = [] # Id, path, traffic
        self.q_table_traffic = {}
        self.list_servers = ['h1', 'h5']
        self.paths = {} # paths[('h1', 'h2')] = [ [path1], [path2], [path3] ...], path1 is the shortest between hosts h1 and h2
        self.link_status = {} # link_status[('s1', 's2')] = differenceFromLastTimStep
        self.action = None

    def max_traffic(self, path_sws):
        """
        Returns the status of a given path according to its maximum traffic.
        """
        sws_length = len(path_sws)
        if sws_length == 1:
            return Traffic_Switches.LOW
        maximum = 0
        for i in range(0, sws_length - 1):
            if (path_sws[i], path_sws[i+1]) in self.link_status:
                if self.link_status[(path_sws[i], path_sws[i+1])] > maximum:
                    maximum = self.link_status[(path_sws[i], path_sws[i+1])]
        if maximum > Traffic_Switches.HIGH: # is 80% of capacity in a 20Mbits/2s link
            return Traffic_Switches.HIGH
        elif maximum > Traffic_Switches.MEDIUM:
            return Traffic_Switches.MEDIUM
        else:
            return Traffic_Switches.LOW


    def setDefault(self):
        for k,v in self.paths.items():
             self.default_route[k] = v[0]#paths[k].insert(0, v[0])
    
    
    def changeRoute(self, host_origin, host_dst, paths_v_index):
        """
        This functions orders controller to change the route taken
        between two hosts. paths_v_index is the index of the route
        indicated by paths switch vector. Index must be >= 1
        """
        s = socket.socket()
        try:
            host = "127.0.0.1"
            s.connect((host, self.changeRoute_port))
            output = str(host_origin)+"|"+str(host_dst)+"|"+str(paths_v_index)
            s.send(output.encode())
            s.shutdown(socket.SHUT_WR)
            self.default_route[(str(host_origin), str(host_dst))] = self.paths[(str(host_origin), str(host_dst))][int(paths_v_index)]
        except socket.error as msg:
            print "Socket Error: %s %s" % (msg, filename)
        except TypeError as msg:
            print "Type Error: %s" % msg
        s.close()
            

    def reward_traffic(self, state_id):
        """
        Given the current state, reward is -1 if
        there is any link with high traffic.
        """
        state = self.states_traffic[state_id]
        for link in state:
            for k, v in link.items():
                if Traffic_Switches.HIGH in v:
                    return -1
        return 1


    def update_q_table_traffic(self, reward, state, action):
        if (state, action) not in self.q_table_traffic: 
            self.q_table_traffic[(state, action)] = 0
        self.q_table_traffic[(state, action)] = self.q_table_traffic[(state, action)] + 0.1 * (reward - self.q_table_traffic[(state, action)])


    def pick_action_traffic(self, state_index, epsilon=0.4):
        state = self.states_traffic[state_index]
        from sys import float_info
        from random import randint, random
        best_qvalue = float_info.min
        best_action = None
        for k, v in self.q_table_traffic.items(): # v is an index or None
            if k[0] == state_index: # Find current_state
                if v > best_qvalue:
                    best_qvalue = v
                    best_action = k[1]
        if random() > epsilon: 
                return best_action
        else:
            alternative_routes = [] # [ ((h1, h2), [s1, s2, s1]), (h1, h2, [s1, s2]) ... ]
            for route in state:
                for k, v in route.items():
                    if v[1] == Traffic_Switches.HIGH: # High traffic
                        for alternative in self.paths[k]:
                            if self.default_route[k] != alternative:
                                alternative_routes.append([k, alternative])
            if alternative_routes != []: # Meaning there is high traffic somewhere
                randomic_action = alternative_routes[randint(0, len(alternative_routes)-1)] #([('h2', 'h3'), ['s1', 's5', 's3', 's4', 's2']])
                i = 0
                for p in self.paths[randomic_action[0]]:
                    if p == randomic_action[1]:
                        self.default_route[randomic_action[0]] = randomic_action[1]
                        return (randomic_action[0], i)
                    i+=1
            else: # Keep or return to shortest path, because I am in MEDIUM or LOW status.
                randomic_actions = [None]
                for route in state:
                    for k, v in route.items():
                        if v[0] != self.paths[k][0]: # Not shortest route
                            randomic_actions.append( (k, 0))
                randomic_action = randomic_actions[randint(0, len(randomic_actions)-1)]
                return randomic_action


    def convert_link_status(self):
        links = {}
        for k, v in self.link_status.items():
            links[(k[0], v[0])] = v[2]
        return links


    def build_state_table_traffic(self, servers):
        current_state = []
        for k, v in self.paths.items():
            if k[0] in servers or k[1] in servers:
                current_state.append({k: [ v[0], Traffic_Switches.LOW ]})
        return current_state

    
    def update_state_traffic(self, servers):
        """
        It computes the current state. Then, if such state 
        is new, append it ti states_traffic. The current state 
        index is then returned.
        """
        current_state = []
        for k, v in self.paths.items():
            if k[0] in servers or k[1] in servers:
                m = self.max_traffic(self.default_route[k])
                l = self.default_route[k]
                current_state.append({k: [l, m ]})
        if current_state not in self.states_traffic:
            self.states_traffic.append(current_state)
        return self.states_traffic.index(current_state)


    @threaded
    def listenFiles(self, ip, filename, port):
        '''
        It opens up TCP connections and receives data from the controller. 
        Such data is later used to model agent state, reward and set of actions.
        '''
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            serversocket.bind((ip, port))
        except socket.error as msg:
            print ('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            return
        serversocket.listen(socket.SOMAXCONN)
        while True:
            clientsocket, addr = serversocket.accept()      
            #print("Got a connection from %s to receive %s" % (str(addr), filename))
            data = clientsocket.recv(1024)
            try:
                newfile = open(filename,'wb+')
                while data:
                    newfile.write(data)
                    data = clientsocket.recv(1024)
                newfile.close()
                try:
                    f = open(filename,'r')
                    if filename == "paths": # Receives only one time
                        self.paths = pickle.load(f)
                        print(self.paths)
                        self.states_traffic.append(self.build_state_table_traffic(self.list_servers))
                        self.setDefault()
                    elif filename == "link_status" and self.paths != {}: # Receives every time step
                        global timestep
                        print "Time step = ", timestep
                        timestep+=1
                        self.link_status = pickle.load(f)
                        self.link_status = self.convert_link_status()
                        for k, v in self.link_status.items():
                            print k,v
                        current_state_id = self.update_state_traffic(self.list_servers)
                        r = self.reward_traffic(current_state_id)
                        if self.currentProfile == Profile.BALANCE:
                            print "Reward = ", r
                            self.update_q_table_traffic(reward=r, state=current_state_id, action=self.action)
                            print "Q-table = ", self.q_table_traffic
                            self.action = self.pick_action_traffic(state_index=current_state_id)
                            if self.action is not None: 
                                self.changeRoute(self.action[0][0], self.action[0][1], self.action[1])
                            print "Action = ", self.action
                            print "State = ", current_state_id
                            for s in self.states_traffic[current_state_id]:
                                print s
                            print("===============================")
                    f.close()
                    try:
                        remove(filename)
                    except:
                        pass
                except:
                    print("Error during conversion!", filename)
            except IOError as e:
                print "I/O error({0}): {1}".format(e.errno, e.strerror)
            clientsocket.close()


setLogLevel("info")

info('*** Adding switches...\n')
c0 = net.addController( 'c0', controller=RemoteController, ip='127.0.0.1', port=6633 ) # Controller in host: 192.168.56.1
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')
s3 = net.addSwitch('s3')
h51 = net.addDocker('h51', ip = "10.0.0.51", mac = "00:00:00:00:00:51", dimage="phfaustini/firewall:latest")
h52 = net.addDocker('h52', ip = "10.0.0.52", mac = "00:00:00:00:00:52", dimage="phfaustini/firewall:latest")

net.addLink(s1, h51, **linkopts_switches)
net.addLink(s1, h52, **linkopts_switches)
net.addLink(h52, s3, **linkopts_switches)
net.addLink(h51, s2, **linkopts_switches)
net.addLink(s2, s3, **linkopts_switches)

        
info('*** Adding hosts...\n')
#hosts.append(net.addHost('h1', ip="10.0.1.1", mac="00:00:00:00:00:01" )) # Server1
hosts.append(net.addDocker('h1', ip = "10.0.1.1", mac = "00:00:00:00:00:01", dimage="phfaustini/server:latest"))
hosts.append(net.addHost('h2', ip="10.0.2.2", mac="00:00:00:00:00:02" )) # Client Legit
hosts.append(net.addHost('h3', ip="10.0.2.3", mac="00:00:00:00:00:03" )) # Client Legit
hosts.append(net.addHost('h4', ip="10.0.2.4", mac="00:00:00:00:00:04" )) # Client Malicious
#hosts.append(net.addHost('h5', ip="10.0.1.5", mac="00:00:00:00:00:05" )) # Server2
hosts.append(net.addDocker('h5', ip = "10.0.1.5", mac = "00:00:00:00:00:05", dimage="phfaustini/server:latest"))
net.addLink(hosts[0], s1, **linkopts_hosts)
net.addLink(hosts[1], s2, **linkopts_hosts)
net.addLink(hosts[2], s2, **linkopts_hosts)
net.addLink(hosts[3], s2, **linkopts_hosts)
net.addLink(hosts[4], s1, **linkopts_hosts)
    

h51.cmd('brctl addbr br0')
h51.cmd('ifconfig h51-eth0 0.0.0.0 down')
h51.cmd('ifconfig h51-eth1 0.0.0.0 down')
h51.cmd('brctl addif br0 h51-eth0')
h51.cmd('brctl addif br0 h51-eth1')
h51.cmd('ifconfig h51-eth0 up')
h51.cmd('ifconfig h51-eth1 up')
h51.cmd('ifconfig br0 up')

h52.cmd('brctl addbr br0')
h52.cmd('ifconfig h52-eth0 0.0.0.0 down')
h52.cmd('ifconfig h52-eth1 0.0.0.0 down')
h52.cmd('brctl addif br0 h52-eth0')
h52.cmd('brctl addif br0 h52-eth1')
h52.cmd('ifconfig h52-eth0 up')
h52.cmd('ifconfig h52-eth1 up')
h52.cmd('ifconfig br0 up')

net.start()
t = Thread(target=CLI, args=(net,))
t.start()
agent = Agent()
agent.listenFiles("127.0.0.1", "paths", listenPaths_port)
agent.listenFiles("127.0.0.1", "link_status", listenLinkStatus_port)

################## Begin test ##################
sleep(1)
net.get('h1').cmd('cd home/ && python server.py "10.0.1.1" 60001 "50mb.flv" &')
net.get('h5').cmd('cd home/ && python server.py "10.0.1.5" 60001 "50mb.flv" &')

net.get('h2').cmd('cd ../videos/client2/ && xterm -name "h2" &')
net.get('h3').cmd('cd ../videos/client3/ && xterm -name "h3" &')
net.get('h4').cmd('cd ../videos/client4/ && xterm -name "h4" &')

while timestep < 11: pass
h52.cmd('ebtables -A FORWARD -s 00:00:00:00:00:04 -j DROP')
h52.cmd('ebtables -A FORWARD -d 00:00:00:00:00:04 -j DROP')
h51.cmd('ebtables -A FORWARD -s 00:00:00:00:00:04 -j DROP')
h51.cmd('ebtables -A FORWARD -d 00:00:00:00:00:04 -j DROP')

t.join()
################## End test ##################

net.stop()
info('*** Cleaning environment...\n')
call("cd ~/Documents/containernet/bin/ && sudo sh clear_crash.sh", shell=True) # sudo netstat -tulpn
