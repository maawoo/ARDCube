from ARDCube.config import ROOT_DIR, FORCE_PATH, PYROSAR_PATH, SAT_DICT
import ARDCube.utils.general as utils
import ARDCube.utils.force as force

import os
import glob
import multiprocessing as mp
from datetime import datetime
from spython.main import Client
import fiona
import geopandas as gpd
import rasterio
import rasterio.mask
from rasterio.windows import get_data_window


def generate_ard(sensor, debug=False):
    """Main function of this module. Will collect necessary information from 'settings.prm' and either run
    process_sar() or process_optical(), depending on chosen sensor.

    Parameters
    ----------
    sensor: string
        Name of the sensor that Analysis Ready Data should be processed for. It is assumed that a subdirectory
        containing level-1 data for this sensor already exist in /{DataDirectory}/level1/{sensor} .
        Valid options are defined in SAT_DICT.keys().
        Example: 'landsat8'
    debug: boolean (optional)
        Optional parameter to print Singularity debugging information.

    Returns
    -------
    None
    """

    ## Get settings from 'settings.prm'
    settings = utils.get_settings()

    ## Check if sensor is supported and if level-1 directory exists
    if sensor not in list(SAT_DICT.keys()):
        raise ValueError(f"{sensor} is not supported!")

    level1_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level1', sensor)
    if not os.path.isdir(level1_dir):
        raise NotADirectoryError(f"{level1_dir} not found. \nDoes level-1 data for {sensor} exist?\n"
                                 f"If not, you can use 'download_level1()' to download some data first! :)")

    print(f"#### Start processing of {sensor} data...")
    if sensor == 'sentinel1':
        process_sar(settings=settings,
                    debug=debug)
    else:
        process_optical(settings=settings,
                        sensor=sensor,
                        debug=debug)


def process_sar(settings, debug):
    """

    Parameters
    ----------
    settings: ConfigParser object
        A dictionary-like object created by ARDCube.utils.get_settings
    debug: boolean (optional)
        Optional parameter to print Singularity debugging information.

    Returns
    -------
    None
    """

    Client.debug = debug
    if debug:
        quiet = False
    else:
        quiet = True

    snap_py_path = os.path.join(ROOT_DIR, 'ARDCube', 'singularity', 'pyrosar', 'py_scripts', 'snap.py')
    in_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level1', 'sentinel1')
    out_dir_pyro = os.path.join(settings['GENERAL']['DataDirectory'], 'level2', 'sentinel1_pyrosar')
    out_dir_force = os.path.join(settings['GENERAL']['DataDirectory'], 'level2', 'sentinel1')
    utils.isdir_mkdir([out_dir_pyro, out_dir_force])

    aoi_path = utils.get_aoi_path(settings)
    dem_path, dem_nodata = utils.get_dem_path(settings)

    out = Client.execute(PYROSAR_PATH, ["python", snap_py_path, in_dir, out_dir_pyro, aoi_path, dem_path],
                         options=["--cleanenv"], quiet=quiet, stream=True)

    for line in out:
        print(line, end='')

    print("\n#### Cropping files to AOI...")
    _crop_by_aoi(settings=settings, directory_src=out_dir_pyro, directory_dst=out_dir_force)
    print("\n#### Datacubing via FORCE....")
    force.cube_dataset(directory=out_dir_force)

    print("\n#### Finished processing! Creating additional outputs...\n")
    force.create_mosaics(directory=out_dir_force)
    force.create_kml_grid(directory=out_dir_force)
    print("Done!")


def process_optical(settings, sensor, debug):
    """

    Parameters
    ----------
    settings: ConfigParser object
        A dictionary-like object created by ARDCube.utils.get_settings
    sensor: string
        Name of the sensor that Analysis Ready Data should be processed for. It is assumed that a subdirectory
        containing level-1 data for this sensor already exist in /{DataDirectory}/level1/{sensor} .
        Valid options are defined in SAT_DICT.keys().
        Example: 'landsat8'
    debug: boolean
        Singularity debugging information is printed if set to True.

    Returns
    -------
    None
    """

    Client.debug = debug
    if debug:
        quiet = False
    else:
        quiet = True

    ## A timestamped copy of FORCE_params__template.prm will be filled with all necessary information and
    ## used for processing.
    prm_file, out_dir = _mod_force_template_prm(settings, sensor)

    ## Get path to file queue from parameter file and check how many scenes will be processed.
    ## The function asks for user confirmation and returns a boolean.
    check = _check_force_file_queue(prm_file)

    if check:
        print("\n#### Start processing...")
        print("\nUnfortunately the output printed by force-level2 cannot be streamed at the moment, which means that \n"
              "you cannot track the progress in here. However, you can regularly check the queue file mentioned \n"
              "above to see if the processing continues as expected.")

        Client.execute(FORCE_PATH, ["force-level2", prm_file],
                       options=["--cleanenv"], quiet=quiet)

        print("\n#### Finished processing! Creating additional outputs...\n")
        force.create_mosaics(directory=out_dir)
        force.create_kml_grid(directory=out_dir)
        print("Done!")

    else:
        print("\n#### Processing cancelled...")


def _mod_force_template_prm(settings, sensor):
    """Helper function for process_optical(). The template parameter file used for the 'force-level2' module of FORCE
    will be filled with parameters defined in the ['PROCESSING'] section of 'settings.prm'.
    Instead of overwriting the template, a modified and timestamped copy will be saved."""

    ## Get path to default parameter file and get all lines as a list
    prm_path = os.path.join(ROOT_DIR, 'settings', 'force', 'FORCE_params__template.prm')
    if not os.path.isfile(prm_path):
        raise FileNotFoundError(f"{prm_path} could not be found.")

    with open(prm_path, 'r') as file:
        prm_lines = file.readlines()

    ## Get all necessary information to fill parameters that are not pre-defined
    data_dir = settings['GENERAL']['DataDirectory']
    file_queue = os.path.join(data_dir, 'level1', sensor, 'queue.txt')
    dir_level2 = os.path.join(data_dir, 'level2', sensor)
    dir_log = os.path.join(data_dir, 'log', sensor)
    dir_tmp = os.path.join(data_dir, 'temp')
    file_dem, dem_nodata = utils.get_dem_path(settings=settings)
    nproc = settings['PROCESSING']['NPROC']
    nthread = settings['PROCESSING']['NTHREAD']

    ## Create these directories (if necessary) before running FORCE
    utils.isdir_mkdir(directory=[dir_level2, dir_log, dir_tmp])

    ## Parameter fields that need to be changed (parameters) and the content that will be used (values)
    parameters = ['FILE_QUEUE', 'DIR_LEVEL2', 'DIR_LOG', 'DIR_TEMP', 'FILE_DEM', 'DEM_NODATA', 'NPROC', 'NTHREAD']
    values = [file_queue, dir_level2, dir_log, dir_tmp, file_dem, dem_nodata, nproc, nthread]

    ## Search for parameters in the list of lines and return the index
    indexes = []
    for p in parameters:
        ind = [i for i, item in enumerate(prm_lines) if item.startswith(p)]
        if len(ind) != 1:
            raise IndexError(f"The field '{p}' was found more than once in FORCE_params__template.prm, which "
                             f"should not be the case!")
        else:
            indexes.append(ind[0])

    ## Change parameter fields at selected indexes
    for p, v, i in zip(parameters, values, indexes):
        prm_lines[i] = f"{p} = {v}\n"

    ## Define new output directory and create it if necessary
    prm_dir_new = os.path.join(ROOT_DIR, 'settings', 'force', 'history')
    utils.isdir_mkdir(directory=prm_dir_new)

    ## Create copy of FORCE_params__template.prm with adjusted parameter fields and return full path
    now = datetime.now().strftime('%Y%m%dT%H%M%S')
    prm_path_new = os.path.join(prm_dir_new, f"FORCE_params__{sensor}_{now}.prm")
    with open(prm_path_new, 'w') as file:
        file.writelines(prm_lines)

    return prm_path_new, dir_level2


def _check_force_file_queue(prm_path):
    """Helper function for process_optical(). """

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
        answer = input(f"\nThe following queue file will be queried by FORCE: \n{queue_path}\n"
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


def _crop_by_aoi(settings, directory_src, directory_dst):
    """..."""

    ## Define log-file
    log_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'log')
    utils.isdir_mkdir(log_dir)
    log_file = os.path.join(log_dir,
                            f"{datetime.now().strftime('%Y%m%dT%H%M%S__crop_by_aoi')}.log")

    ## Create file list
    file_list = []
    for file in glob.iglob(os.path.join(directory_src, '**/*.tif'), recursive=True):
        file_list.append(file)

    ## Get CRS from first file. All other files are assumed to be in the same CRS!
    with rasterio.open(file_list[0]) as raster:
        dst_crs = raster.crs

    ## Get AOI path and get reprojected features
    aoi_path = utils.get_aoi_path(settings)
    features = _get_aoi_features(aoi_path=aoi_path, crs=dst_crs)

    ## Set multiprocessing pool and print useful message
    nproc = settings['PROCESSING']['NPROC']
    pool = mp.Pool(nproc)
    print(f"{len(file_list)}")

    ## TODO: Somehow implement progress bar or something else?
    result_objects = [pool.apply_async(_do_crop, args=(file, features, directory_dst)) for file in file_list]
    results = [f"{r.get()[0]} - {r.get()[1]}" for r in result_objects]

    pool.close()
    pool.join()

    ## TODO: Logging could be improved, but needs some careful work/testing because of parallelism
    ## https://docs.python.org/3/library/multiprocessing.html#logging
    with open(log_file, 'w') as f:
        for item in results:
            f.write("%s\n" % item)


def _do_crop(file, features, directory_dst):

    ## TODO: Rewrite this without the temporary file.
    ## Getting the data window and cropping the output file works without writing to a
    ## temporary file first, but I had some problems with getting the transform right.
    ## It works pretty well as is (especially with multiprocessing), so I'll just leave it for now.
    ## https://rasterio.readthedocs.io/en/latest/topics/windowed-rw.html?highlight=crop#data-windows

    with rasterio.open(file) as src:
        try:
            out_image, out_transform = rasterio.mask.mask(src, features, crop=True, all_touched=True)
            out_meta = src.meta.copy()
            src_nodata = src.nodata

            if not out_image.mean() == src_nodata:
                out_meta.update({"driver": "GTiff",
                                 "height": out_image.shape[1],
                                 "width": out_image.shape[2],
                                 "transform": out_transform})

                tmp_tif = os.path.join(directory_dst, os.path.basename(file).replace('.tif', '_tmp.tif'))
                with rasterio.open(tmp_tif, "w", **out_meta) as dst:
                    dst.write(out_image)

                with rasterio.open(tmp_tif) as src2:
                    window = get_data_window(src2.read(1, masked=True))

                    kwargs = src2.meta.copy()
                    kwargs.update({
                        'height': window.height,
                        'width': window.width,
                        'transform': rasterio.windows.transform(window, src2.transform)})

                    out_name = os.path.basename(tmp_tif.replace('_tmp.tif', '.tif'))
                    out_tif = os.path.join(directory_dst, out_name)

                    try:
                        with rasterio.open(out_tif, 'w', **kwargs) as dst:
                            dst.write(src2.read(window=window))
                        result = "success"
                    except Exception as e:
                        result = f"fail 3: {e}"

                os.remove(tmp_tif)

            else:
                result = "fail 2: Only nodata of raster inside AOI"

        except ValueError:
            result = "fail 1: Raster completely outside AOI"

    return (file, result)


def _get_aoi_features(aoi_path, crs):
    """..."""

    aoi_tmp = gpd.read_file(aoi_path)
    aoi_tmp = aoi_tmp.to_crs({'init': crs})
    aoi_tmp_path = os.path.join(os.path.dirname(aoi_path),
                                f"{os.path.splitext(os.path.basename(aoi_path))[0]}_tmp.geojson")
    aoi_tmp.to_file(aoi_tmp_path, driver="GeoJSON")

    ## Open temporary AOI file with Fiona
    with fiona.open(aoi_tmp_path) as shape:
        features = [feature['geometry'] for feature in shape
                    if feature['geometry']]

    ## Remove temporary AOI file
    os.remove(aoi_tmp_path)

    return features
