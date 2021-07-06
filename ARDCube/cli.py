from ARDCube.config import SAT_DICT
from ARDCube.utils.general import setup_project
from ARDCube.download_level1 import download_level1
from ARDCube.generate_ard import generate_ard
from ARDCube.prepare_odc import prepare_odc

import os
import click


@click.group()
def cli():
    pass


@cli.command()
@click.option('-d', '--dir', required=True, type=click.Path(writable=True, readable=True))
def setup(directory):
    click.echo('Setting up project directory.')

    if not os.path.isdir(directory):
        os.mkdir(directory)

    setup_project(directory=directory)


@cli.command()
@click.option('-s', '--sensor', required=True, type=click.Choice(list(SAT_DICT.keys()), case_sensitive=True))
@click.option('--debug', is_flag=True, help='Print debugging information of the FORCE Singularity container. '
                                            'Has no effect when downloading SAR data, as no Singularity container is '
                                            'being used.')
def download(sensor, debug):
    download_level1(sensor=sensor, debug=debug)


@cli.command()
@click.option('-s', '--sensor', required=True, type=click.Choice(list(SAT_DICT.keys()), case_sensitive=True))
@click.option('--debug', is_flag=True, help='Print debugging information of the Singularity container used during '
                                            'processing.')
@click.option('--clean', is_flag=True, help='Automatically remove intermediate processing results that are created '
                                            'during processing of SAR data. Has no effect when processing optical data.')
def process(sensor, debug, clean):
    generate_ard(sensor=sensor, debug=debug, clean=clean)


@cli.command()
@click.option('-s', '--sensor', required=True, type=click.Choice(list(SAT_DICT.keys()), case_sensitive=True))
@click.option('-o', '--overwrite', default=True, help='If set to False, only YAML files for new scenes will be created.')
def prepare(sensor, overwrite):
    prepare_odc(sensor=sensor, overwrite=overwrite)
