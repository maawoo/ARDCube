from ARDCube.config import ROOT_DIR, FORCE_PATH, PYROSAR_PATH, SAT_DICT
from ARDCube.settings import get_settings
from ARDCube.utils import get_aoi_path

import os
from datetime import datetime
from spython.main import Client


def generate_ard(dataset):
    """..."""

    ## Check if dataset is supported.
    if dataset not in list(SAT_DICT.keys()):
        raise NotImplemented(f"{dataset} is not supported!")

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

    Client.debug = debug_force

    ## If UseDefault = True, a copy of FORCE_default_template.prm will automatically be filled with all necessary
    ## information and used for processing. If UseDefault = False, the file FORCE_custom.prm will be used for
    ## processing and not changed in any way!
    if settings.getboolean('PROCESSING', 'UseDefault'):  # = if True / Will also raise an error if field is not boolean
        prm_file = _mod_force_default_prm(settings, dataset)
    else:
        prm_file = os.path.join(ROOT_DIR, 'misc/force', 'FORCE_custom.prm')

    ## Get path to file queue from parameter file and check how many scenes will be processed.
    ## The function asks for user confirmation and returns a boolean.
    check = _check_force_file_queue(prm_file)

    if check:  # if answer was 'yes', start processing

        ## TODO: Stream output instead??
        output = Client.execute(FORCE_PATH, ["force-level2", prm_file],
                                options=["--cleanenv"])
        if debug_force:
            for line in output:
                print(line)
        else:
            print(output)

    else:
        print("\n#### \nProcessing cancelled...")


def create_dem(settings):
    """..."""

    out_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'misc/dem')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    dem_py_path = os.path.join(ROOT_DIR, 'ARDCube/pyroSAR/dem.py')
    aoi_path = get_aoi_path(settings)
    aoi_name = os.path.splitext(os.path.basename(aoi_path))[0]

    out_file = os.path.join(out_dir, f"SRTM_1Sec_DEM__{aoi_name}.tif")

    if os.path.isfile(out_file):
        while True:
            answer = input(f"{out_file} already exist.\n"
                           f"Do you want to create a new SRTM 1Sec DEM for your AOI and overwrite the existing file? \n"
                           f"If not, the existing DEM will be used for processing! (y/n)")

            if answer in ['y', 'yes']:
                Client.execute(PYROSAR_PATH, ["python", f"{dem_py_path}", f"{aoi_path}", f"{out_file}"],
                               options=["--cleanenv"])
                break

            elif answer in ['n', 'no']:
                break

            else:
                print(f"---------- \n{answer} is not a valid answer! \n----------")
                continue

    else:
        Client.execute(PYROSAR_PATH, ["python", f"{dem_py_path}", f"{aoi_path}", f"{out_file}"],
                       options=["--cleanenv"])

    return out_file


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
    file_dem = settings['PROCESSING']['DEM']
    dem_nodata = settings['PROCESSING']['DEM_NoData']
    if file_dem == 'srtm':
        file_dem = create_dem(settings)  # Create DEM if 'srtm' selected!
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
            raise IndexError(f"The field '{p}' was found more than once in FORCE_default.prm, which should not be "
                             f"the case!")

        indexes.append(ind[0])

    ## Change parameter fields at selected indexes
    for p, v, i in zip(parameters, values, indexes):
        lines[i] = f"{p} = {v}\n"

    ## Create copy of FORCE_default.prm with adjusted parameter fields and return its path
    now = datetime.now().strftime('%Y%m%dT%H%M%S')
    prm_path_new = os.path.join(ROOT_DIR, 'misc/force', f'FORCE_default__{now}.prm')
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

    ## Check if field exists and for duplicate entries, just to be sure..
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
        answer = input(f"The following queue file will be queried by FORCE: {queue_path}\n"
                       f"{n_done} scenes are marked as 'DONE' \n{n_queued} scenes are marked as 'QUEUED'\n"
                       f"Do you want to proceed with the batch processing of all {n_queued} scenes marked as 'QUEUED'?"
                       f" (y/n)")

        if answer in ['y', 'yes']:
            return True

        elif answer in ['n', 'no']:
            return False

        else:
            print(f"---------- \n{answer} is not a valid answer! \n----------")
            continue
