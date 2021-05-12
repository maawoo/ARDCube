import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORCE_PATH = os.path.join(ROOT_DIR, 'singularity/force', 'force_365.sif')
PYROSAR_PATH = os.path.join(ROOT_DIR, 'singularity/pyrosar', 'pyrosar_0121.sif')
POSTGRES_PATH = os.path.join(ROOT_DIR, 'singularity/postgres', 'postgres.sif')

## Key = Supported sensors
## Value = Abbreviation used in FORCE download module
SAT_DICT = {'sentinel1': None,
            'sentinel2': 'S2A,S2B',
            'landsat4': 'LT04',
            'landsat5': 'LT05',
            'landsat7': 'LE07',
            'landsat8': 'LC08'}

## Available DEM types that can be created with pyroSAR as defined here:
## https://pyrosar.readthedocs.io/en/latest/pyroSAR.html#pyroSAR.auxdata.dem_autoload
## Note that some sources might require authentication, which can be added to the parameters listed in the script
## '/settings/pyrosar/srtm.py' if necessary.
DEM_TYPES = ['AW3D30', 'SRTM 1Sec HGT', 'SRTM 3Sec', 'TDX90m']
