## General

start:
	singularity instance start ./pyrosar/pyrosar.sif pyrosar_c
	singularity instance start ./force/force.sif force_c
	singularity instance start -B ./odc/postgres/postgres_data:/var/lib/postgresql/data \
		-B ./odc/postgres/postgres_run:/var/run/postgresql ./odc/postgres/postgres.sif postgres_c
	singularity instance start ./odc/datacube/datacube.sif datacube_c

	@echo "------------"
	@echo "Don't forget to stop all instances when you're done by using the 'make stop' command!"		
	@echo "------------"

stop:
	singularity instance stop pyrosar_c
	singularity instance stop force_c
	singularity instance stop postgres_c
	singularity instance stop datacube_c


## ODC

start_db:
	singularity run instance://postgres_c
	# No runscript is defined in the postgres.def file, so the container will run whatever was defined by the original Docker image. 
	# https://hub.docker.com/r/postgis/postgis

init:
	singularity exec instance://datacube_c datacube -v system init

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
