from ARDCube.config import ROOT_DIR, FORCE_PATH, PYROSAR_PATH, SAT_DICT
from ARDCube.utils import get_settings, get_dem_path

import os
from datetime import datetime
from spython.main import Client


def generate_ard(sensor, debug_force=False):
    """..."""

    ## Check if sensor is supported.
    if sensor not in list(SAT_DICT.keys()):
        raise ValueError(f"{sensor} is not supported!")

    ## Get user defined settings
    settings = get_settings()

    ## Check if associated level-1 dataset exists in expected directory
    level1_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level1', sensor)
    if not os.path.isdir(level1_dir):
        raise NotADirectoryError(f"{level1_dir} not found. \nDoes level-1 data for {sensor} exist?\n"
                                 f"If not, you can use 'download_level1()' to download some data first! :)")

    ## Start processing functions
    print(f"#### Start processing of {sensor} dataset...")

    if sensor == 'sentinel1':
        process_sar(settings=settings)

    else:
        process_optical(settings=settings,
                        sensor=sensor,
                        debug_force=debug_force)


def process_sar(settings):
    """..."""

    level2_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level2', 'sentinel1')
    if not os.path.exists(level2_dir):
        os.makedirs(level2_dir)

    ## TODO: Implement SAR processing with pyroSAR container


def process_optical(settings, sensor, debug_force=False):
    """..."""

    Client.debug = debug_force

    ## If UseDefault = True, a timestamped copy of FORCE_default__template.prm will be filled with all necessary
    ## information and used for processing.
    ## If UseDefault = False, the file FORCE_custom.prm will be used for processing as-is.
    if settings.getboolean('PROCESSING', 'UseDefault'):
        prm_file = _mod_force_template_prm(settings, sensor)
    else:
        prm_file = os.path.join(ROOT_DIR, 'misc/force', 'FORCE_custom.prm')

    ## Get path to file queue from parameter file and check how many scenes will be processed.
    ## The function asks for user confirmation and returns a boolean.
    check = _check_force_file_queue(prm_file)

    if check:
        print("\n#### Start processing...")

        out = Client.execute(FORCE_PATH, ["force-level2", prm_file],
                             options=["--cleanenv"], stream=True)

        for line in out:
            print(line, end='')

    else:
        print("\n#### Processing cancelled...")


def _mod_force_template_prm(settings, sensor):
    """..."""

    ## Get DataDirectory
    data_dir = settings['GENERAL']['DataDirectory']

    ## Get path to default parameter file
    prm_path = os.path.join(ROOT_DIR, 'misc/force', 'FORCE_default__template.prm')
    if not os.path.isfile(prm_path):
        raise FileNotFoundError(f"{prm_path} could not be found.")

    ## Read parameter file and get all lines as a list
    with open(prm_path, 'r') as file:
        lines = file.readlines()

    ## Get all necessary information to fill parameters that are not pre-defined
    file_queue = os.path.join(data_dir, f'level1/{sensor}', 'queue.txt')
    dir_level2 = os.path.join(data_dir, f'level2/{sensor}')
    dir_log = os.path.join(data_dir, f'log/{sensor}')
    dir_tmp = os.path.join(data_dir, 'temp')
    file_dem = get_dem_path(settings)
    dem_nodata = settings['PROCESSING']['DEM_NoData']
    nproc = settings['PROCESSING']['NPROC']
    nthread = settings['PROCESSING']['NTHREAD']

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
            raise IndexError(f"The field '{p}' was found more than once in FORCE_default__template.prm, which "
                             f"should not be the case!")
        else:
            indexes.append(ind[0])

    ## Change parameter fields at selected indexes
    for p, v, i in zip(parameters, values, indexes):
        lines[i] = f"{p} = {v}\n"

    ## Create copy of FORCE_default__template.prm with adjusted parameter fields and return its path
    now = datetime.now().strftime('%Y%m%dT%H%M%S')
    prm_path_new = os.path.join(ROOT_DIR, 'misc/force', f"FORCE_default__{now}.prm")
    with open(prm_path_new, 'w') as file:
        file.writelines(lines)

    return prm_path_new


def _check_force_file_queue(prm_path):
    """..."""

    ## Read parameter file and get all lines as a list
    with open(prm_path, 'r') as file:
        lines = file.readlines()

    ## Return index of 'FILE_QUEUE' parameter field
    ind = [i for i, item in enumerate(lines) if item.startswith('FILE_QUEUE')]

    ## Check if field exists and for duplicate entries, just to be sure...
    if len(ind) > 1:
        raise IndexError(f"The field 'FILE_QUEUE' was found more than once in '{prm_path}'")
    elif len(ind) == 0:
        raise IndexError(f"The field 'FILE_QUEUE' could not be found in '{prm_path}'")

    ## Extract path from string, check if file exists and read it
    queue_path = lines[ind[0]].replace('FILE_QUEUE = ', '').replace('\n', '')

    if not os.path.isfile(queue_path):
        raise FileNotFoundError(f"{queue_path} does not exist.")

    with open(queue_path, 'r') as file:
        lines_queue = file.readlines()

    ## Count how many entries in queue file are marked as 'DONE' and how many as 'QUEUED'
    n_done = len([i for i, item in enumerate(lines_queue) if item.endswith('DONE\n')])
    n_queued = len([i for i, item in enumerate(lines_queue) if item.endswith('QUEUED\n')])

    ## Before starting the batch processing, ask for user confirmation. Return boolean depending on answer.
    while True:
        answer = input(f"\nThe following queue file will be queried by FORCE: {queue_path}\n"
                       f"{n_done} scenes are marked as 'DONE' \n{n_queued} scenes are marked as 'QUEUED'\n"
                       f"Do you want to proceed with the batch processing of all {n_queued} scenes marked as 'QUEUED'?"
                       f" (y/n)")

        if answer in ['y', 'yes']:
            return True

        elif answer in ['n', 'no']:
            return False

        else:
            print(f"\n{answer} is not a valid answer!")
            continue
