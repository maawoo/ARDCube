#!/bin/bash

# Singularity compose doesn't currently support an environment section, 
# so an environment file is bound to the instance as a workaround.
# https://github.com/singularityhub/singularity-compose/blob/master/docs/spec/spec-1.0.md#environment

DB_HOSTNAME=postgres
DB_USERNAME=opendatacube
DB_PASSWORD=opendatacubepassword
DB_DATABASE=opendatacube

export DB_HOSTNAME
export DB_USERNAME
export DB_PASSWORD
export DB_DATABASE
