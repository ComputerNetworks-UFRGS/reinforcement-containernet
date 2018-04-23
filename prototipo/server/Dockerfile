# Python files must be in the same folder as Dockerfile
# Build with $ sudo docker build -t phfaustini/server .
# Run with $ sudo docker run --name my_instance -i -t phfaustini/server
# More: https://www.digitalocean.com/community/tutorials/docker-explained-using-dockerfiles-to-automate-building-of-images

FROM ubuntu:14.04
MAINTAINER Pedro Faustini

RUN sudo apt-get update

RUN sudo apt-get install python -y

ADD server.py ./home

ADD input.avi ./home

ADD 50mb.flv ./home
