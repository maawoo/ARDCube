from ARDCube.config import ROOT_DIR, FORCE_PATH, PYROSAR_PATH, SAT_DICT
from ARDCube.read_settings import get_settings
from ARDCube.auxiliary.aux import create_dem

import os
from datetime import datetime
from spython.main import Client


def process_ard(dataset):
    """..."""

    ## Check if dataset is supported.
    if dataset not in list(SAT_DICT.keys()):
        raise NotImplemented(f"{dataset} not supported!")

    ## Get settings
    settings = get_settings()

    ## Check if level-1 directory exist, if not raise an error
    level1_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level1', dataset)
    if not os.path.isdir(level1_dir):
        raise NotADirectoryError(f"{level1_dir} not found. \nDoes level-1 data for {dataset} exist?\n"
                                 f"If not, you can use 'download_level1()' to download some data first! :)")

    ## Process ARD!
    if dataset == 'Sentinel1':
        process_sar(settings=settings)
    else:
        process_optical(settings=settings,
                        dataset=dataset)


def process_sar(settings):
    """..."""
    pass

    ## TODO: Implement SAR processing with pyroSAR container


def process_optical(settings, dataset, debug_force=False):
    """..."""

    ## TODO: Add some useful messages
    ## TODO: Check how many scenes will be processed and ask for user confirmation before starting

    Client.debug = debug_force

    ## If UseDefault = True, a copy of FORCE_default.prm will automatically filled with all necessary information and
    ## used for processing
    if settings.getboolean('PROCESSING', 'UseDefault'):
        prm_file = _mod_force_default_prm(settings, dataset)

        output = Client.execute(FORCE_PATH, ["force-level2", prm_file],
                                options=["--cleanenv"])
    ## If UseDefault = False, the file FORCE_custom.prm will be used for processing and not changed in any way!
    else:
        prm_file = os.path.join(ROOT_DIR, 'misc/force', 'FORCE_custom.prm')

        output = Client.execute(FORCE_PATH, ["force-level2", prm_file],
                                options=["--cleanenv"])

    if debug_force:
        for line in output:
            print(line)
    else:
        print(output)


def _mod_force_default_prm(settings, dataset):
    """..."""

    ## Get DataDirectory from settings
    data_dir = settings['GENERAL']['DataDirectory']

    ## Get path to default parameter file
    prm_path = os.path.join(ROOT_DIR, 'misc/force', 'FORCE_default.prm')
    if not os.path.isfile(prm_path):
        raise FileNotFoundError(f"{prm_path} could not be found.")

    ## Read parameter file and get all lines as a list
    with open(prm_path, 'r') as file:
        lines = file.readlines()

    ## Get all necessary information for the parameter file
    file_queue = os.path.join(data_dir, f'level1/{dataset}', 'pool.txt')
    dir_level2 = os.path.join(data_dir, f'level2/{dataset}')
    dir_log = os.path.join(data_dir, f'log/{dataset}')
    dir_tmp = os.path.join(data_dir, 'temp')
    dem_nodata = settings['GENERAL']['DEM_NoData']
    nproc = settings['PROCESSING']['NPROC']
    nthread = settings['PROCESSING']['NTHREAD']
    file_dem = settings['GENERAL']['DEM']
    if file_dem == 'srtm':
        file_dem = create_dem(settings)  # Create DEM if 'srtm' selected

    ## These paths might not exists at this point, so before running FORCE we should make sure they do!
    paths_to_check = [dir_level2, dir_log, dir_tmp]
    for path in paths_to_check:
        if not os.path.exists(path):
            os.makedirs(path)

    ## Lists of parameter fields that need to be changed (parameters) and the content that will be used (values)
    ## The order of both lists need to be the same!!
    parameters = ['FILE_QUEUE', 'DIR_LEVEL2', 'DIR_LOG', 'DIR_TEMP', 'FILE_DEM', 'DEM_NODATA', 'NPROC', 'NTHREAD']
    values = [file_queue, dir_level2, dir_log, dir_tmp, file_dem, dem_nodata, nproc, nthread]

    ## Search for parameters in the list of lines and return the index
    indexes = []
    for p in parameters:
        ind = [i for i, item in enumerate(lines) if item.startswith(p)]
        if len(ind) != 1:
            raise IndexError(f"The field '{p}' was found more than once in FORCE_default.prm, which should not be "
                             f"the case!")

        indexes.append(ind[0])

    ## Change parameter fields at selected indexes
    for p, v, i in zip(parameters, values, indexes):
        lines[i] = f"{p} = {v}\n"

    ## Create copy of FORCE_default.prm with adjusted parameter fields and return its path
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    prm_path_new = os.path.join(ROOT_DIR, 'misc/force', f'FORCE_default__{now}.prm')
    with open(prm_path_new, 'w') as file:
        file.writelines(lines)

    return prm_path_new
