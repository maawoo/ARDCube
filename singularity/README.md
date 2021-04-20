
### ODC 

https://datacube-core.readthedocs.io/en/latest/ops/config.html#configuration-via-environment-variables

`datacube -v system init`  

`datacube product add /home/marco/pypypy/ARDCube/settings/odc/*.yaml`
`datacube dataset add /home/marco/pypypy/ARDCube_data/level2/*/*/*.yaml`

Deleting products:  
https://gist.github.com/omad/1ae3463a123f37a9acf37213bebfde86  
(not sure how up-to-date this is)

Reset database:
- `dropdb -h $HOSTNAME -U odcuser opendatacube`
- `createdb -h $DB_HOSTNAME -U $DB_USERNAME opendatacube` 
- `datacube -v system init`  


### Jupyter Lab

https://pangeo.io/setup_guides/hpc.html#

Terrasense:
jupyter lab --no-browser --ip=`hostname` --port=8888 --notebook-dir=/home/du23yow/ARDCube_use

Laptop:
ssh -N -L 8888:geo01.rz.uni-jena.de:8888 du23yow@geo01.rz.uni-jena.de