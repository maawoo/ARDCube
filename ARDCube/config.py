from ARDCube import ROOT_DIR

import os
import configparser


def get_settings():
    """Returns the content of the settings file located in the project directory as a dictionary-like ConfigParser
    object."""

    ## Get project directory and settings file from local settings file
    settings_file_local = os.path.join(ROOT_DIR, 'resources', 'settings', 'settings.prm')
    settings_local = configparser.ConfigParser(allow_no_value=True)
    settings_local.read(settings_file_local)
    proj_directory = settings_local['GENERAL']['ProjectDirectory']
    settings_proj = os.path.join(proj_directory, 'management', 'settings', 'settings.prm')

    if not os.path.isfile(settings_proj):
        raise FileNotFoundError(f"{settings_proj} does not exist.")

    settings = configparser.ConfigParser(allow_no_value=True)
    settings.read(settings_proj)

    return settings


settings = get_settings()
PROJ_DIR = settings['GENERAL']['ProjectDirectory']
FORCE_PATH = os.path.join(PROJ_DIR, 'management', 'singularity', 'force.sif')
PYROSAR_PATH = os.path.join(PROJ_DIR, 'management', 'singularity', 'pyrosar.sif')
POSTGRES_PATH = os.path.join(PROJ_DIR, 'management', 'singularity', 'postgres.sif')

## Keys = Supported input for any ARDCube module/function that requires the 'sensor' parameter
## Values = Abbreviations used by the force-level1-csd download module as defined here:
## https://force-eo.readthedocs.io/en/latest/howto/level1-csd.html#optional-arguments
SAT_DICT = {'sentinel1': None,
            'sentinel2': 'S2A,S2B',
            'landsat4': 'LT04',
            'landsat5': 'LT05',
            'landsat7': 'LE07',
            'landsat8': 'LC08'}

## Available DEM types that can be created with pyroSAR as defined here:
## https://pyrosar.readthedocs.io/en/latest/pyroSAR.html#pyroSAR.auxdata.dem_autoload
## Note that some sources might require authentication, which can be added to the parameters listed in the script
## '/settings/pyrosar/dem.py' if necessary.
DEM_TYPES = ['AW3D30', 'SRTM 1Sec HGT', 'SRTM 3Sec', 'TDX90m']
