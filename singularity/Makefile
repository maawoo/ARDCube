SHELL := /bin/bash

## General

start:
	singularity instance start ./pyrosar/pyrosar.sif pyrosar_c
	singularity instance start ./force/force.sif force_c
	singularity instance start -B ./postgres/postgres_data:/var/lib/postgresql/data \
		-B ./postgres/postgres_run:/var/run/postgresql ./postgres/postgres.sif postgres_c
	singularity instance start ./datacube/datacube.sif datacube_c

	@echo "------------"
	@echo "Don't forget to stop all instances when you're done by using the 'make stop' command!"		
	@echo "------------"

	singularity instance list

stop:
	singularity instance stop pyrosar_c
	singularity instance stop force_c
	singularity instance stop postgres_c
	singularity instance stop datacube_c


## ODC

start-db:
	# This starts the postgres server in the background, which will list on port 5432. 
	# Session output (stdout & stderr) will be written to 'postgres_log'. Useful resources:
	# https://www.postgresql.org/docs/current/server-start.html
	# https://hub.docker.com/r/postgis/postgis
	singularity run instance://postgres_c >postgres_log 2>&1 &

init-db:
	# Only necessary to run this once to initialize the Data Cube database schema.
	singularity exec --env DB_HOSTNAME=$HOSTNAME instance://datacube_c datacube -v system init

check-db:
	# Check and display current configuration.
	singularity exec --env DB_HOSTNAME=$HOSTNAME instance://datacube_c datacube system check

product:
	singularity-compose exec jupyter \
		datacube product add https://raw.githubusercontent.com/digitalearthafrica/config/master/products/esa_s2_l2a.odc-product.yaml

index:


## Jupyter

jupyter:
	singularity-compose exec jupyter \
		/bin/tini -- jupyter notebook --notebook-dir=/opt/notebooks --ip='0.0.0.0' --allow-root --no-browser

# Tini is used to avoid kernel crashes:
# https://jupyter-notebook.readthedocs.io/en/stable/public_server.html#docker-cmd
