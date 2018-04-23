from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.addresses import IPAddr
from pox.lib.packet.ethernet import ethernet
from pox.lib.addresses import EthAddr
from pox.openflow.discovery import Discovery
from pox.lib.revent import *  
from pox.lib.recoco import Timer
from pox.openflow.of_json import *
import thread
import socket
import cPickle as pickle
from subprocess import call

import networkx as nx
G = nx.Graph()

log = core.getLogger()

ip_to_mac = {}
ip_to_mac["10.0.1.1"] = "00:00:00:00:00:01"
ip_to_mac["10.0.1.5"] = "00:00:00:00:00:05"
ip_to_mac["10.0.2.2"] = "00:00:00:00:00:02"
ip_to_mac["10.0.2.3"] = "00:00:00:00:00:03"
ip_to_mac["10.0.2.4"] = "00:00:00:00:00:04"
ip_to_mac["10.0.0.51"] = "00:00:00:00:00:51"
ip_to_mac["10.0.0.52"] = "00:00:00:00:00:52"

waiting = []
number_switches = 0
number_links = 0
paths = {} # paths[('h1', 'h2')] = [ [path1], [path2], [path3] ...], path1 is the shortest between hosts h1 and h2 
default_route = {} # default_route = [pathdefault]
switch_ports = {} # switch_ports['s1'] = ['s2','s3','s5','h1','nat0'']
                  #                       eth1 eth2 eth3  eth4 eth5
link_status = {} # link_status[(s1, 1)] = [s2, cumulative, differenceFromLastTimStep], link_status[(s1, 2)] = [s3, cumulative, 43242],  # link s1-eth2, going to s3, had 43242 bytes of traffic in the last last step


def initialise(filename="ext/switch_portsF.csv"):
    """
    First it initialises a hash (switch_ports) mapping what is
    in each output port for each switch.
    Afterwards it initialises the waiting array, 
    used to know when to send information to orchestrator
    Finally it initialises the link info data structure
    
    """
    global number_switches
    global number_links
    global switch_ports
    global waiting
    global link_status
    from fileinput import input, close
    for line in input(filename):
        if not line.startswith("#"):
            number_switches+=1
            line = line.rstrip().split(',')
            switch_ports[line.pop(0)] = line
            for w in line:
                if w.startswith("s"):
                    number_links+=1
    close()

    waiting = [0]*number_switches

    for sw, v in switch_ports.items():
        port=1
        for dst in v:
            if dst.startswith('s'): link_status[(sw,port)] = [dst, 0, 0]
            if dst.startswith('h'): link_status[(sw,port)] = [dst, 0, 0]
            if dst.startswith('d'): link_status[(sw,port)] = [dst, 0, 0]
            port+=1


def send_orchestrator(ip="127.0.0.1", port=50008, filename="paths"):
    """
    This functions sends a file to the orchestrator.
    """
    s = socket.socket()
    try:
        s.connect((ip, port))
        f = open(filename,'rb')
        l = f.read(1024)
        while (l):
            s.sendall(l)
            l = f.read(1024)
        f.close()
        s.shutdown(socket.SHUT_WR)
    except socket.error as msg:
        print "Socket Error: %s %s" % (msg, filename)
    except TypeError as msg:
        print "Type Error: %s" % msg
    s.close()


def ip_to_name(ip="10.0.5.10"):
    """
    Given an IP address in string dotted format,
    return the standard name for that host.
    E.g. '10.0.5.10' => 'h10'
    """
    return "h"+ip.split('.')[-1]


def mac_to_ip(mac = "00:00:00:00:00:01"):
    """
    Given a MAC address in string dotted format,
    return the standard IP address for that host.
    E.g. '00:00:00:00:00:09' => '10.0.5.9'
    """
    for k,v in ip_to_mac.items():
        if v == mac:
            return k
    return None


def mac_to_name(mac = "00:00:00:00:00:01"):
    """
    Given an IP address in string dotted format,
    return the standard name for that host.
    E.g. '00:00:00:00:00:09' => 'h9'
    """
    return ip_to_name(mac_to_ip(mac))


def host_to_switch(host = 'h1', filename="ext/switch_portsF.csv"):
    """
    Given a host name, returns the name of the switch attached
    to that host (name in the form 's1')
    """
    from fileinput import input, close
    for line in input(filename):
        if not line.startswith("#"):
            line = line.rstrip().split(",")
            switch = line.pop(0)
            if host in line:
                close()
                return switch
    close()
    return None

def name_to_ip(name="h1"):
    number = int(name[1:])
    if number < 10: 
        number = "0"+str(number) 
    else: 
        number = str(number)
    mac = "00:00:00:00:00:"+number
    return mac_to_ip(mac)


def parse_flows(filename, src, dst):
    from fileinput import input, close
    for line in input(filename):
        in_port = None
        dlsrc = None
        dldst = None
        if line.find('tcp') != -1:
            line = line.split(',')
            for parameter in line:
                if parameter.startswith("in_port"):
                    in_port = str(parameter.split('=')[-1])
                elif in_port is not None and parameter.startswith("dl_src"):
                    if str(parameter.split('=')[-1]) == src:
                        dlsrc =  str(parameter.split('=')[-1])
                    else:
                        break
                elif dlsrc is not None and parameter.startswith("dl_dst"):
                    if str(parameter.split('=')[-1]) == dst:
                        dldst =  str(parameter.split('=')[-1])
                        close()
                        return (in_port, dlsrc, dldst)
                    else:
                        break
    return (None, None, None)
		

def change_route(ip="127.0.0.1"):
    """
    It receives messages ordering to change the route between two hosts.
    """
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = ip
    port = 50010
    try:
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        serversocket.bind((host, port))
    except socket.error as msg:
        print ('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
        return
    serversocket.listen(socket.SOMAXCONN)      
    while True:
        clientsocket, addr = serversocket.accept()      
        print("Got a connection from %s..." % str(addr))
        data = clientsocket.recv(1024)
        if not data:
            print "no data"
            break
        else:                                         # src,dst,route
            message = data.decode('utf-8').split("|") # "h3|h1|1"

            msg0 = str(message[0])
            msg1 = str(message[1])
            msg2 = str(message[2])
            
            default_route[(msg0, msg1)] = paths[(msg0, msg1)][int(message[2])]
            default_route[(msg1, msg0)] = paths[(msg1, msg0)][int(message[2])]
            for i in range(1, number_switches+1):
                call("sudo ovs-ofctl dump-flows s"+str(i)+" > flows.txt", shell=True)
                inport, src, dst = parse_flows("flows.txt", ip_to_mac[name_to_ip(msg0)], ip_to_mac[name_to_ip(msg1)])
                if inport is not None and src is not None and dst is not None:
                    print "removing", inport, src, dst, default_route[(msg0, msg1)]
                    s = 'sudo ovs-ofctl --strict del-flows s'+str(i)+' "table=0, tcp,in_port='+inport+',vlan_tci=0x0000,dl_src='+src+',dl_dst='+dst+',nw_tos=0"'
                    call(s, shell=True)

                inport, src, dst = parse_flows("flows.txt", ip_to_mac[name_to_ip(msg1)], ip_to_mac[name_to_ip(msg0)])
                if inport is not None and src is not None and dst is not None:
                    print "removing", inport, src, dst, default_route[(msg1, msg0)]
                    s = 'sudo ovs-ofctl --strict del-flows s'+str(i)+' "table=0, tcp,in_port='+inport+',vlan_tci=0x0000,dl_src='+src+',dl_dst='+dst+',nw_tos=0"'
                    call(s, shell=True)
    clientsocket.close()


class topoDiscovery(EventMixin):
    def __init__(self):
        self.links = 0
        def startup():
            core.openflow.addListeners(self, priority = 0)
            core.openflow_discovery.addListeners(self)
        core.call_when_ready(startup, ('openflow','openflow_discovery'))


    @staticmethod
    def calculate_paths():
        """
        Computes all possibles paths from one node to another.
        """
        global paths

        paths[  ( 'h1', 'h2' ) ] = [['s1', 'h51', 's2'], ['s1', 's3', 'h52', 's2']]
        paths[  ( 'h1', 'h3' ) ] = [['s1', 'h51', 's2'], ['s1', 's3', 'h52', 's2']]
        paths[  ( 'h1', 'h4' ) ] = [['s1', 'h51', 's2'], ['s1', 's3', 'h52', 's2']]

        paths[  ( 'h2', 'h1' ) ] = [['s2', 'h51', 's1'], ['s2', 'h52', 's3', 's1']]
        paths[  ( 'h3', 'h1' ) ] = [['s2', 'h51', 's1'], ['s2', 'h52', 's3', 's1']]
        paths[  ( 'h4', 'h1' ) ] = [['s2', 'h51', 's1'], ['s2', 'h52', 's3', 's1']]

        paths[  ( 'h5', 'h2' ) ] = [['s1', 'h51', 's2'], ['s1', 's3', 'h52', 's2']]
        paths[  ( 'h5', 'h3' ) ] = [['s1', 'h51', 's2'], ['s1', 's3', 'h52', 's2']]
        paths[  ( 'h5', 'h4' ) ] = [['s1', 'h51', 's2'], ['s1', 's3', 'h52', 's2']]

        paths[  ( 'h2', 'h5' ) ] = [['s2', 'h51', 's1'], ['s2', 'h52', 's3', 's1']]
        paths[  ( 'h3', 'h5' ) ] = [['s2', 'h51', 's1'], ['s2', 'h52', 's3', 's1']]
        paths[  ( 'h4', 'h5' ) ] = [['s2', 'h51', 's1'], ['s2', 'h52', 's3', 's1']]
        paths[  ( 'h2', 'h3' ) ] = [ ['s2']  ]
        paths[  ( 'h3', 'h2' ) ] = [ ['s2']  ]
        paths[  ( 'h4', 'h2' ) ] = [ ['s2']  ]
        paths[  ( 'h2', 'h4' ) ] = [ ['s2']  ]
        paths[  ( 'h3', 'h4' ) ] = [ ['s2']  ]
        paths[  ( 'h4', 'h3' ) ] = [ ['s2']  ]
        paths[  ( 'h4', 'h4' ) ] = [ ['s2']  ]
        paths[  ( 'h3', 'h3' ) ] = [ ['s2']  ]
        paths[  ( 'h2', 'h2' ) ] = [ ['s2']  ]
        paths[  ( 'h1', 'h1' ) ] = [ ['s1']  ]
        paths[  ( 'h5', 'h5' ) ] = [ ['s1']  ]


    @staticmethod
    def print_paths():
        global paths
        for k,v in paths.items():
            print("*****",k," ******")
            for i in v:
                print i


    @staticmethod
    def setDefault():
        """
        The first path in paths vector is the one used by the controller.
        """
        for k,v in paths.items():
             default_route[k] = v[0]


    @staticmethod
    def send_paths_orchestrator():
        """
        It sends the calculated paths to the orchestrator.
        """
        global paths
        filename = "paths"
        f = open(filename,'wb')
        pickle.dump(paths,f)
        f.close() 
        send_orchestrator(port=50008, filename="paths")

    
    @staticmethod
    def send_link_status_orchestrator():
        """
        It sends the calculated paths for a given switch to the orchestrator.
        """
        global link_status
        file_name = "link_status"
        f = open(file_name,'wb')
        pickle.dump(link_status,f)
        f.close() 
        send_orchestrator(port=50009, filename=file_name)


    def _handle_LinkEvent(self, event):
        l = event.link
        sw1 = "s"+str(l.dpid1)
        sw2 = "s"+str(l.dpid2)
        G.add_node( sw1 )
        G.add_node( sw2 )
        if event.added:
            G.add_edge(sw1,sw2)
            self.links+=1
            if self.links == 1:
                topoDiscovery.calculate_paths()
                topoDiscovery.setDefault()
                topoDiscovery.print_paths()
                topoDiscovery.send_paths_orchestrator()
        if event.removed:
            try:
                self.links-=1
            except:
                print "remove edge error"
   

class Switch (object):
    def __init__ (self, connection, swnumber):
        self.connection = connection
        self.switch_number = int(swnumber)
        self.switch_name = "s"+str(self.switch_number)
        connection.addListeners(self)

    def _handle_PacketIn (self, event):
        packet = event.parsed
        if packet.type == ethernet.IPV6_TYPE: return # Doesn't handle IPV6 
        if packet.dst.is_multicast:
            #print "src/dst", packet.src, packet.next.protodst, ip_to_mac[packet.next.protodst.toStr()]
            packet.dst = EthAddr(ip_to_mac[packet.next.protodst.toStr()])
            
        srcname = mac_to_name(packet.src.toStr())
        dstname = mac_to_name(packet.dst.toStr())
        
        #print "Adding at sw ", self.switch_name, (srcname, dstname), p
        next = False
        destination = dstname
        for s in default_route[(srcname, dstname)]:
            if s == self.switch_name: # Found current switch
                next = True
            elif next:
                destination = s
                break

        outport = 1
        for ethend in switch_ports[self.switch_name]:
            if ethend == destination:
                break
            else:
                outport+=1

        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet, event.port)
        msg.match.tp_src = None
        msg.match.tp_dst = None
        msg.match.nw_dst = None
        msg.match.nw_src = None
        msg.idle_timeout = 0
        msg.hard_timeout = 0
        msg.actions.append(of.ofp_action_output(port = outport))
        print self.switch_name, "forwarding ", srcname, " to ", dstname, "at", outport
        msg.data = event.ofp
        self.connection.send(msg.pack())


class connectedSwitch (object):
    def __init__ (self):
        core.openflow.addListeners(self)

    def _handle_ConnectionUp (self, event):
        log.debug("Connection %s" % (event.connection,))
        Switch(event.connection, dpid_to_str(event.dpid)[-2]+dpid_to_str(event.dpid)[-1])


def _timer_func ():
    '''
    handler for timer function that sends the requests to all the
    switches connected to the controller.
    '''
    for connection in core.openflow._connections.values():
        connection.send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
  

def _handle_portstats_received (event):
    '''
    This funtion calculates the traffic, in bytes, in each link during the last time step.
    The information is stored into link_status global variable. 
    This variable is identified by a tuple (sw_name, port) and returns a list with [out_sw, cumulativeTraffic, lastTraffic]
    '''
    stats = flow_stats_to_list(event.stats) # list of dict
    sw_number = str(int(dpidToStr(event.connection.dpid).split("-")[-1]))
    global waiting
    global link_status
    global number_switches
    waiting[int(sw_number)-1] = 1 # -1 because s1 is at position 0 and so on.
    print "#####################################"
    print sw_number
    for port in stats:
        if ("s"+sw_number, port['port_no']) in link_status:
            print sw_number, port['port_no'], link_status[ ("s"+sw_number, port['port_no']) ][0], " | ", port['rx_bytes'], port['tx_bytes'], port['rx_bytes'] + port['tx_bytes'] , port['tx_bytes'] + port['rx_bytes'] - link_status[ ("s"+sw_number, port['port_no']) ][-2]
            link_status[ ("s"+sw_number, port['port_no']) ][-1] = port['tx_bytes'] + port['rx_bytes'] - link_status[ ("s"+sw_number, port['port_no']) ][-2]
            link_status[ ("s"+sw_number, port['port_no']) ][-2] = port['tx_bytes'] + port['rx_bytes']
    if 0 not in waiting:
        waiting = [0]*number_switches
        topoDiscovery.send_link_status_orchestrator()
        


def launch ():
    initialise()
    thread.start_new_thread(change_route, ("127.0.0.1",))
    core.registerNew(connectedSwitch)
    core.registerNew(topoDiscovery)
            
    core.openflow.addListenerByName("PortStatsReceived", _handle_portstats_received) 
    Timer(2, _timer_func, recurring=True)