import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORCE_PATH = os.path.join(ROOT_DIR, 'singularity/force', 'force_365.sif')
PYROSAR_PATH = os.path.join(ROOT_DIR, 'singularity/pyrosar', 'pyrosar.sif')
POSTGRES_PATH = os.path.join(ROOT_DIR, 'singularity/postgres', 'postgres.sif')

## Key = Supported sensors
## Value = Abbreviation used in FORCE download module
SAT_DICT = {'sentinel1': None,
            'sentinel2': 'S2A,S2B',
            'landsat4': 'LT04',
            'landsat5': 'LT05',
            'landsat7': 'LE07',
            'landsat8': 'LC08'}
