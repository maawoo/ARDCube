#!/bin/bash

# https://github.com/singularityhub/singularity-compose/blob/master/docs/spec/spec-1.0.md#environment

DB_HOSTNAME=postgres
DB_USERNAME=opendatacube
DB_PASSWORD=opendatacubepassword
DB_DATABASE=opendatacube

export DB_HOSTNAME
export DB_USERNAME
export DB_PASSWORD
export DB_DATABASE

export GDAL_DATA=$(gdal-config --datadir)
export LC_ALL=C.UTF-8
export PATH="/env/bin:$PATH"