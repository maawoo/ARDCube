
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

delete-db:
	singularity exec --env DB_HOSTNAME=$HOSTNAME instance://datacube_c dropdb -h $HOSTNAME -U odcuser opendatacube

create-db:
	singularity exec --env DB_HOSTNAME=$HOSTNAME instance://datacube_c createdb -h $HOSTNAME -U odcuser opendatacube

check-db:
	# Check and display current configuration.
	singularity exec --env DB_HOSTNAME=$HOSTNAME instance://datacube_c datacube system check

product-add:
	# = Index product YAMLs
	# Deleting products is a bit more complicated: https://gist.github.com/omad/1ae3463a123f37a9acf37213bebfde86
	singularity exec --env DB_HOSTNAME=$HOSTNAME instance://datacube_c \
		datacube product add /home/marco/pypypy/ARDCube/misc/odc/product_definitions/*.yaml

data-add:
	# = Index dataset YAMLs
	singularity exec --env DB_HOSTNAME=$HOSTNAME instance://datacube_c \
		datacube dataset add /home/marco/pypypy/ARDCube_data/level-2/*/*/*.yaml


## Jupyter

jupyter:
	singularity-compose exec instance://datacube_c \
		jupyter notebook --notebook-dir=/home/marco/pypypy/ARDCube/notebooks --ip='0.0.0.0' --allow-root --no-browser --port=8888 --NotebookApp.token='secretpassword'
