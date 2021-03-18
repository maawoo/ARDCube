from ARDCube.config import ROOT_DIR, FORCE_PATH, PYROSAR_PATH
from ARDCube.read_settings import get_settings
from ARDCube.auxiliary.aux import check_sat_settings, create_dem

import os


def process_ARD():

    ##
    settings = get_settings()
    # sat_dict = check_sat_settings(settings=settings)
    sat_short = 'L8'



def _mod_force_default_params(settings, sat):
    """"""

    prm_path = os.path.join(ROOT_DIR, 'misc/force', 'FORCE_default.prm')
    assert os.path.isfile(prm_path), f"{prm_path} is not a valid path."

    with open(prm_path, 'r') as file:
        lines = file.readlines()

    parameters = ['FILE_QUEUE', 'DIR_LEVEL2', 'DIR_LOG', 'DIR_TEMP', 'FILE_DEM', 'DEM_NODATA', 'NPROC', 'NTHREAD']

    main_dir = settings['GENERAL']['DataDirectory']

    path_queue = os.path.join(main_dir, f'level-1/{sat}', 'pool.txt')
    dir_level2 = os.path.join(main_dir, f'level-2/{sat}')
    dir_log = os.path.join(main_dir, f'log/{sat}')
    dir_tmp = os.path.join(main_dir, 'temp')

    path_dem = settings['GENERAL']['DEM']
    if path_dem == 'srtm':
        path_dem = create_dem(settings)

    dem_nodata = settings['GENERAL']['DEM_NoData']
    n_proc = settings['PROCESSING']['NPROC']
    n_thread = settings['PROCESSING']['NTHREAD']

    values = [path_queue, dir_level2, dir_log, dir_tmp, path_dem, dem_nodata, n_proc, n_thread]

    idxs = []
    for p in parameters:
        id = [i for i, item in enumerate(lines) if item.startswith(p)]
        assert len(id) == 1, "Multiple lines found!"
        idxs.append(id[0])

    for p, v, i in zip(parameters, values, idxs):
        lines[i] = f"{p} = {v}\n"

    tmp_prm_path = os.path.join(ROOT_DIR, 'misc/force', 'tmp.prm')
    with open(tmp_prm_path, 'w') as file:
        file.writelines(lines)
