#!/usr/bin/env bash

ACTUAL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"/..
cd ${ACTUAL_DIR}

NAME="optim_$RANDOM"
IMAGE_TAG="optim"

nvidia-docker run \
        --user=`id -u`:`id -g`\
        --name ${NAME} \
        -v ${ROOT_DIR}:/home/optimizers \
        --rm\
        ${IMAGE_TAG} \
        "$@"
