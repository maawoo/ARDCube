import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORCE_PATH = os.path.join(ROOT_DIR, 'singularity/force', 'force.sif')
PYROSAR_PATH = os.path.join(ROOT_DIR, 'singularity/pyrosar', 'pyrosar.sif')
POSTGRES_PATH = os.path.join(ROOT_DIR, 'singularity/postgres', 'postgres.sif')
