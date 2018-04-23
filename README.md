
# Português - Portuguese
### Setup
* Virtual Box 5.1. Duas opções diferentes de configurações:
* 1) Vá em File -> Preferences -> Network -> "Add host-only network" button com configurações default. Isso permite, se necessário no futuro, acessar a VM a partir da máquina host (e.g. __ssh__).
* 2) Botão direito sobre Docker Clone -> Network -> Adapter 2 -> Desabilite a caixa "Enable Network Adapter". Isso não permite um ssh na VM, mas por ora é irrelevante.

### Controlador:

* Executar:
	`cd ~/pox && ./pox.py log.level --INFO spanning_tree samples.pretty_log openflow.discovery`

* def initialise(filename="ext/switch_portsF.csv"):
	* Recebe um .csv com a topologia. Cada linha diz respeito a um switch. Primeira coluna informa o switch. As colunas seguintes informam o que se conecta a cada porta daquele switch.


* def send_orchestrator(ip="127.0.0.1", port=50008, filename="paths"):
	* Envia ao orquestrador, por TCP, algum arquivo.

* def change_route(ip="127.0.0.1"):
	* Recebe um pedido do orquestrador para alterar uma rota entre dois hosts. O formato é a seguinte string:
		* ##### "src,dst,route", como, por exemplo, "h3|h1|1" (optar pela rota 1 entre h3 e h1)

* def calculate_paths():
	* Calcula os caminhos, em switches, entre dois hosts. Por ora, está estático.
	

* Estruturas de dados:
	* paths: dicionário. Chave é uma tupla de strings representando hosts (e.g. ("h1, h3")). Conteúdo é uma lista de lista. Cada sublista representa um caminho entre os dois hosts. São formadas por strings. Cada string é o nome de um switch que compõe a rota entre os hosts. (e.g. paths[("h1, h3")] = [ ['s1', 's3']  , ['s1', 's2', 's3']  ]

	* default_route: dicionário. Chave é uma tupla de strings representando hosts. Valor é o caminho, dentre os possíveis descritos na variável 'path', efetivamente adotado pelo controlador.

	* switch_ports: dicionário. Chave é um switch, e valor é uma lista com o que está conectado a cada porta do switch. Por exemplo, # switch_ports['s1'] = ['s2','s3','s5','h1','nat0''], siginifica que s2 está na porta eth1, s3 está conectado à porta eth2, e assim por diante.

	* link_status. Dicionário que traz informações sobre os links. A chave é uma tupla de strings, contendo switch e porta. Por exemplo, link_status[(s1, 1)] = [s2, cumulative, differenceFromLastTimStep], link_status[(s1, 2)] = [s3, 5025252562155, 43242],  # link s1-eth2, indo para s3, tinha 43242 bytes de tráfego no último time step, e 5025252562155 bytes trafegados desde o princípio.

	* ip_to_mac: dicionário que mapeia, como o nome diz, um endereço IP para um endereço MAC. Por ora, está estático. Assim como a descoberta de topologia, feita por um arquivo csv, pode ser dinamizada.


### OrchestratorFirewall

* Ambiente com hosts e conteiners. Para inicializar, basta digitar em um terminal `sudo python orchestratorFirewall.py`

* O terminal exibe informacoes da rede. Terminais xterm dos clientes abrem. Ao digitar `sh start.sh`, o respectivo cliente solicita um arquivo a um servidor.

* No mesmo arquivo há dois simples firewalls que bloqueiam o tráfego de um dado host. A linhas 328-331 mostram comandos de exemplo para se fazer isso com um host.

---

# Inglês - English
### Setup
* Virtual Box 5.1. Two different configuration options:
* 1) Click on File -> Preferences -> Network -> "Add host-only network" button with default configurations. This allows, if necessary, to access the VM through __ssh__.
* 2) Right click on Docker Clone -> Network -> Adapter 2 -> Desable "Enable Network Adapter". This does not allows ssh to the VM, but it is initially irrelevant.

### Controller:

* Execute:
	`cd ~/pox && ./pox.py log.level --INFO spanning_tree samples.pretty_log openflow.discovery`

* def initialise(filename="ext/switch_portsF.csv"):
	* Receives a .csv with the topology. Each line deals with one switch. The first column identifies the switch, and the following columns which connections are made.

* def send_orchestrator(ip="127.0.0.1", port=50008, filename="paths"):
	* Sends to the orchestrator, through TCP, a file.

* def change_route(ip="127.0.0.1"):
	* Receives a request from the orchestrator as to change the route between two hosts. The format is given by the following string:
		* ##### "src,dst,route", e.g. "h3|h1|1" (choose route 1 between h3 and h1)

* def calculate_paths():
	* Calculates the path between two hosts through the switches. By now, it is static.

* Data structure:
	* paths: dictionary. A key is a tuple of strings representing two hosts (e.g. ("h1, h3")). The content is a list of lists. Each sublist represents a path between two hosts. Each string is the name of a switch that composes a route between the hosts (e.g. paths[("h1, h3")] = [ ['s1', 's3']  , ['s1', 's2', 's3'] ]).

	* default_route: dictionary. A key is a tuple of strings representing hosts. A value is the path, chosen among the possible ones in the variable 'path', effectively adopted by the controller.

	* switch_ports: dictionary. A key is a swicth, and a value is a list containing what is connected to each port of the switch. As an example, ##### switch_ports['s1'] = ['s2','s3','s5','h1','nat0''], means that s2 is at port eth1, s3 is connected to eth2, and so on.

	* link_status: dictionary containing info about the links. The key is a tuple of strings, containing switch and port. As an example, link_status[(s1, 1)] = [s2, cumulative, differenceFromLastTimStep], link_status[(s1, 2)] = [s3, 5025252562155, 43242],  ##### link s1-eth2, going to s3, had 43242 bytes of traffic in the last time step, and 5025252562155 bytes since the start.

	* ip_to_mac: dictionary that maps, as the name says, an IP address to a MAC address. For now, it is static. As the topology discovery, done by a csv file, it can be dynamized.


### OrchestratorFirewall

* It is an environment with hosts and containers. To initialize it, type on the terminal `sudo python orchestratorFirewall.py`

* The terminal shows info about the network. The client's xterm terminals will open. By typing `sh start.sh`, the current client requests a file to the server.

* In the same file there are two simple firewalls that block the traffic from a specific host. Lines 328-331 show example commands to do so with a host.

* The most important structure is __q_table_traffic__, that receives the rewards of the balancing accordingly with the SARSA update equation (function: update_q_table_traffic(self, reward, state, action)). 

### Dockerfiles

* They host the function networks (e.g. firewall), but are versatile and can host multiple functions. One example is the use of it as server containers.

* The first line of the Dockerfile contains info of how to build them, execute them separately etc.
