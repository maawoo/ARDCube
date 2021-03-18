import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORCE_DIR = os.path.join(ROOT_DIR, 'singularity/force')
PYROSAR_DIR = os.path.join(ROOT_DIR, 'singularity/pyrosar')
POSTGRES_DIR = os.path.join(ROOT_DIR, 'singularity/postgres')
