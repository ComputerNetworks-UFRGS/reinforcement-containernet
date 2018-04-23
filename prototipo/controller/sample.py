def read_switch_ports(filename="switch_ports.csv"):
    """
    Initialises a hash (switch_ports) mapping what is
    in each output port for each switch.
    """
    number_links = 0
    number_switches = 0
    switch_ports = {}
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
    number_links /= 2
    return number_links


def host_to_switch(host = 'h1', filename="switch_ports.csv"):
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