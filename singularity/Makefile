
## General

start:
	#singularity instance start ./pyrosar/pyrosar.sif pyrosar_c
	#singularity instance start ./force/force.sif force_c

	singularity instance start -B ./postgres/postgres_data:/var/lib/postgresql/data \
		-B ./postgres/postgres_run:/var/run/postgresql ./postgres/postgres.sif postgres_c

	@echo "------------"
	@echo "Don't forget to stop all instances when you're done by using the 'make stop' command!"		
	@echo "------------"

	singularity instance list

	## This starts the postgres server in the background, which will list on port 5432. 
	## Session output (stdout & stderr) will be written to 'postgres_log'. Useful resources:
	## https://www.postgresql.org/docs/current/server-start.html
	## https://hub.docker.com/r/postgis/postgis
	singularity run instance://postgres_c >postgres_log 2>&1 &
	

stop:
	#singularity instance stop pyrosar_c
	#singularity instance stop force_c
	singularity instance stop postgres_c


# datacube -v system init
# dropdb -h $HOSTNAME -U odcuser opendatacube
# createdb -h $DB_HOSTNAME -U $DB_USERNAME opendatacube

## Deleting products is a bit more complicated: https://gist.github.com/omad/1ae3463a123f37a9acf37213bebfde86
# datacube product add /home/marco/pypypy/ARDCube/misc/odc/product_definitions/*.yaml
# datacube dataset add /home/marco/pypypy/ARDCube_data/level-2/*/*/*.yaml
