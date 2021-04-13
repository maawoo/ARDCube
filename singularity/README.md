**Postgres**   
https://www.postgresql.org/docs/current/server-start.html  
https://hub.docker.com/r/postgis/postgis

`singularity run -B ./postgres/postgres_data:/var/lib/postgresql/data -B ./postgres/postgres_run:/var/run/postgresql 
./postgres/postgres.sif >postgres_log 2>&1 &`

`pkill postgres`

**ODC**  
`createdb -h $DB_HOSTNAME -U $DB_USERNAME opendatacube`
`datacube -v system init`

`dropdb -h $HOSTNAME -U odcuser opendatacube`

`datacube product add /home/marco/pypypy/ARDCube/settings/odc/*.yaml`
`datacube dataset add /home/marco/pypypy/ARDCube_data/level2/*/*/*.yaml`

Deleting products:  
https://gist.github.com/omad/1ae3463a123f37a9acf37213bebfde86  
(not sure how up-to-date this is)
