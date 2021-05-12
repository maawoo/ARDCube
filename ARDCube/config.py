import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORCE_PATH = os.path.join(ROOT_DIR, 'singularity/force', 'force_365.sif')
PYROSAR_PATH = os.path.join(ROOT_DIR, 'singularity/pyrosar', 'pyrosar_0121.sif')
POSTGRES_PATH = os.path.join(ROOT_DIR, 'singularity/postgres', 'postgres.sif')

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
