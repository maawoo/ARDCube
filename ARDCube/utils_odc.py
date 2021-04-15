from ARDCube.config import POSTGRES_PATH

import os
from spython.main import Client


def start_postgres(port=5433, debug=False):

    ## https://www.postgresql.org/docs/10/app-pg-ctl.html
    ## https://hub.docker.com/r/postgis/postgis

    Client.debug = debug
    if debug:
        quiet = False
    else:
        quiet = True

    pg_dir = os.path.dirname(POSTGRES_PATH)
    pg_log = os.path.join(pg_dir, 'postgres_log')
    pg_data = os.path.join(pg_dir, 'postgres_data')
    pg_run = os.path.join(pg_dir, 'postgres_run')

    output = Client.run(POSTGRES_PATH, ["pg_ctl", "start", f"--log={pg_log}", f"--options='-p {port}'", "--silent"],
                        bind=[f"{pg_data}:/var/lib/postgresql/data", f"{pg_run}:/var/run/postgresql"],
                        quiet=quiet)

    if output is None:
        print(f"PostgreSQL server started successfully! Port: {port}")
    else:
        if isinstance(output, list):
            for line in output:
                print(line)
        else:
            print(output)


def stop_postgres(debug=False):

    Client.debug = debug
    if debug:
        quiet = False
    else:
        quiet = True

    pg_dir = os.path.dirname(POSTGRES_PATH)
    pg_data = os.path.join(pg_dir, 'postgres_data')
    pg_run = os.path.join(pg_dir, 'postgres_run')

    output = Client.run(POSTGRES_PATH, ["pg_ctl", "stop", "--silent"],
                        bind=[f"{pg_data}:/var/lib/postgresql/data", f"{pg_run}:/var/run/postgresql"],
                        quiet=quiet)

    if output is None:
        print("PostgreSQL server stopped successfully!")
    else:
        if isinstance(output, list):
            for line in output:
                print(line)
        else:
            print(output)


def odc_db_init():
    pass


def odc_db_check():
    pass


def odc_index_products():
    pass


def odc_index_datasets():
    pass
