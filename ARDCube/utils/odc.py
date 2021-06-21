from ARDCube.config import ROOT_DIR, POSTGRES_PATH

import os
import configparser
from spython.main import Client


def init_postgres(debug=False):
    """Initializes the PostgreSQL Singularity container."""

    ## https://hub.docker.com/r/postgis/postgis
    ## https://hub.docker.com/_/postgres/

    Client.debug = debug
    if debug:
        quiet = False
    else:
        quiet = True

    pg_dir = os.path.dirname(POSTGRES_PATH)
    pg_data = os.path.join(pg_dir, 'postgres_data')
    pg_run = os.path.join(pg_dir, 'postgres_run')

    output = Client.run(POSTGRES_PATH,
                        bind=[f"{pg_data}:/var/lib/postgresql/data", f"{pg_run}:/var/run/postgresql"],
                        quiet=quiet)

    if isinstance(output, list):
        for line in output:
            print(line)
    else:
        print(output)


def start_postgres(debug=False):
    """Starts the PostgreSQL Singularity container."""

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

    ## Get port from datacube.conf
    port = _get_port()

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
    """Stops the PostgreSQL Singularity container."""

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


def _get_port():
    """Helper function for start_postgres() to get the port defined in datacube.conf"""

    datacube_conf_path = os.path.join(ROOT_DIR, 'settings', 'odc', 'datacube.conf')

    datacube_conf = configparser.ConfigParser(allow_no_value=True)
    datacube_conf.read(datacube_conf_path)

    port = datacube_conf['default']['db_port']

    return port
