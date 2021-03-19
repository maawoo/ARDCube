import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORCE_PATH = os.path.join(ROOT_DIR, 'singularity/force', 'force.sif')
PYROSAR_PATH = os.path.join(ROOT_DIR, 'singularity/pyrosar', 'pyrosar.sif')
POSTGRES_PATH = os.path.join(ROOT_DIR, 'singularity/postgres', 'postgres.sif')

## Key = Satellite sensor name as listed in settings.prm
## Value = Abbreviation used in FORCE download module
SAT_DICT = {'Sentinel1': None,
            'Sentinel2': 'S2A,S2B',
            'Landsat4': 'LT04',
            'Landsat5': 'LT05',
            'Landsat7': 'LE07',
            'Landsat8': 'LC08'}
