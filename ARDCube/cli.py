from ARDCube.config import SAT_DICT
from ARDCube.utils.general import setup_project, isdir_mkdir
from ARDCube.download_level1 import download_level1
from ARDCube.generate_ard import generate_ard
from ARDCube.prepare_odc import prepare_odc

import click


@click.group()
def cli():
    pass


@cli.command()
@click.option('-p', '--path', required=True, type=click.Path(writable=True, readable=True),
              help='Path to an empty directory that you want to use for your project. The necessary '
                   'directory structure is set up automatically and necessary files (e.g., for parameterization) are '
                   'copied over to get things started.')
@click.option('--build', is_flag=True,
              help="Build all Singularity containers that are provided in the '/singularity/recipe' subdirectory. "
                   "NOTE: This requires sudo privileges and will ask for your password!")
def setup(path, build):
    click.echo('#### Setting up project directory...')
    isdir_mkdir(directory=path)
    setup_project(directory=path, build_containers=build)


@cli.command()
@click.option('-s', '--sensor', required=True, type=click.Choice(list(SAT_DICT.keys()), case_sensitive=True))
@click.option('--debug', is_flag=True,
              help='Print debugging information of the FORCE Singularity container. Has no effect when downloading SAR '
                   'data, as no Singularity container is being used.')
def download(sensor, debug):
    download_level1(sensor=sensor, debug=debug)


@cli.command()
@click.option('-s', '--sensor', required=True, type=click.Choice(list(SAT_DICT.keys()), case_sensitive=True))
@click.option('--debug', is_flag=True,
              help='Print debugging information of the Singularity container used during processing.')
@click.option('--clean', is_flag=True,
              help='Automatically remove intermediate processing results that are created during processing of SAR '
                   'data. Has no effect when processing optical data.')
def process(sensor, debug, clean):
    generate_ard(sensor=sensor, debug=debug, clean=clean)


@cli.command()
@click.option('-s', '--sensor', required=True, type=click.Choice(list(SAT_DICT.keys()), case_sensitive=True))
@click.option('-o', '--overwrite', default=True,
              help='If set to False, only YAML files for new scenes will be created.')
def prepare(sensor, overwrite):
    prepare_odc(sensor=sensor, overwrite=overwrite)
