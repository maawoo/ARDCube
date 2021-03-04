# You can follow the steps below in order to get yourself a local ODC.
# Once running, you can access a Jupyter environment 
# at 'http://localhost' with password 'secretpassword'

# Tini is used to avoid kernel crashes:
# https://jupyter-notebook.readthedocs.io/en/stable/public_server.html#docker-cmd
# 

build:
	singularity-compose build

up:
	singularity-compose up

down:
	singularity-compose down

shell:
	singularity-compose shell --cleanenv jupyter

init:
	singularity-compose exec jupyter datacube -v system init

product:
	singularity-compose exec jupyter \
		datacube product add https://raw.githubusercontent.com/digitalearthafrica/config/master/products/esa_s2_l2a.odc-product.yaml

index:

jupyter:
	singularity-compose exec jupyter \
		/bin/tini -- jupyter notebook --notebook-dir=/opt/notebooks --ip='0.0.0.0' --NotebookApp.token='secretpassword' \
			--allow-root --no-browser




