# Python files must be in the same folder as Dockerfile
# Build with $ sudo docker build -t phfaustini/firewall .
# Run with $ sudo docker run --privileged=true --name my_instance -i -t phfaustini/firewall
# More: https://www.digitalocean.com/community/tutorials/docker-explained-using-dockerfiles-to-automate-building-of-images

FROM ubuntu:14.04
MAINTAINER Pedro Faustini

RUN sudo apt-get update

RUN sudo apt-get install iptables bridge-utils ebtables -y
