#!/bin/sh

if [ "$#" -gt 0 ]; then # if command line arguments were given
    docker stop gracio_pystocs_instance_$1
    docker rm gracio_pystocs_instance_$1
    docker run --name gracio_pystocs_instance_$1 -d gracio_pystocs --endpoint $1
    # docker logs -f gracio_pystocs_instance_$1  ## do not force logs when multiple instances start

else # no command line args -> don't choose endpoint
    docker stop gracio_pystocs_instance
    docker rm gracio_pystocs_instance
    docker run --name gracio_pystocs_instance -d gracio_pystocs --endpoint $1
    docker logs -f gracio_pystocs_instance
fi
