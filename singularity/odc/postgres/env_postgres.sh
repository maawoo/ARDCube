#!/bin/bash

# Singularity compose doesn't currently support an environment section, 
# so an environment file is bound to the instance as a workaround.
# https://github.com/singularityhub/singularity-compose/blob/master/docs/spec/spec-1.0.md#environment

POSTGRES_DB=opendatacube
POSTGRES_PASSWORD=opendatacubepassword
POSTGRES_USER=opendatacube

export POSTGRES_DB
export POSTGRES_PASSWORD
export POSTGRES_USER
      
