import os


def get_aoi_path(settings):
    """Gets the full path to the AOI file based on settings."""

    if os.path.isdir(settings['GENERAL']['AOI']):
        aoi_path = settings['GENERAL']['AOI']
    else:
        aoi_path = os.path.join(settings['GENERAL']['DataDirectory'], 'misc/aoi', settings['GENERAL']['AOI'])

    return aoi_path


def get_force_path():
    """Gets the full path to the FORCE Singularity container (force.sif)."""

    ## Ask for input, if not found in expected directory (/cwd/singularity/force).
    force_dir = os.path.join(os.getcwd(), 'singularity/force')
    if 'force.sif' not in os.listdir(force_dir):
        force_path = input(f"\'force.sif\' could not be found in \'{force_dir}\'.\n"
                           f"Please provide the full path to \'force.sif\' "
                           f"(e.g. \'/path/to/force.sif\'): ")
    else:
        force_path = os.path.join(force_dir, 'force.sif')

    return force_path


def get_pyrosar_path():
    """Gets the full path to the pyroSAR Singularity container (pyrosar.sif)."""

    ## Ask for input, if not found in expected directory (/cwd/singularity/pyrosar).
    pyro_dir = os.path.join(os.getcwd(), 'singularity/pyrosar')
    if 'pyrosar.sif' not in os.listdir(pyro_dir):
        pyro_path = input(f"\'pyrosar.sif\' could not be found in \'{pyro_dir}\'.\n"
                           f"Please provide the full path to \'pyrosar.sif\' "
                           f"(e.g. \'/path/to/pyrosar.sif\'): ")
    else:
        pyro_path = os.path.join(pyro_dir, 'pyrosar.sif')

    return pyro_path
