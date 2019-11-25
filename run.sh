#!/bin/sh

docker stop gracio_pystocs_instance
docker rm gracio_pystocs_instance
if [ "$#" -gt 0 ]; then # if command line arguments were given
    docker run --name gracio_pystocs_instance -d gracio_pystocs --endpoint $1
else # no command line args -> don't choose endpoint
    docker run --name gracio_pystocs_instance -d gracio_pystocs
fi
docker logs -f gracio_pystocs_instance