#!/bin/sh

docker stop gracio_pystocs_instance
docker rm gracio_pystocs_instance
if [ "$#" -gt 0 ]; then
    docker run --name gracio_pystocs_instance -d gracio_pystocs --endpoint $1
else
    docker run --name gracio_pystocs_instance -d gracio_pystocs
fi
docker logs -f gracio_pystocs_instance