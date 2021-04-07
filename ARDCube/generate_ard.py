from ARDCube.config import ROOT_DIR, FORCE_PATH, PYROSAR_PATH, SAT_DICT
from ARDCube.utils import get_settings, get_aoi_path, get_dem_path, progress

import os
import glob
import shutil
from pathlib import Path
from datetime import datetime
from spython.main import Client
import fiona
import geopandas as gpd
import rasterio
import rasterio.mask


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

    ## TODO: Implement SAR processing with pyroSAR container

    level2_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level2', 'sentinel1')
    if not os.path.exists(level2_dir):
        os.makedirs(level2_dir)

    in_dir = None
    out_dir = None
    if not os.path.isdir(out_dir):
        os.mkdir(out_dir)

    # _crop_by_aoi(settings=settings, in_dir=in_dir, out_dir=out_dir)
    # force_cube(level2_dir=out_dir)

    ## Create VRT mosaics and grid in KML format
    # force_mosaic(level2_dir=out_dir)
    # force_kml_grid(level2_dir=out_dir)


def process_optical(settings, sensor, debug_force=False):
    """..."""

    Client.debug = debug_force
    if debug_force:
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
                       options=["--cleanenv"], quiet=quiet, stream=False)

        print("\n#### Finished processing! Creating additional outputs: VRT mosaics & KML-file of grid...")

        ## Create VRT mosaics and KML grid
        force_mosaic(level2_dir=out_dir)
        force_kml_grid(level2_dir=out_dir)

    else:
        print("\n#### Processing cancelled...")


def _mod_force_template_prm(settings, sensor):
    """..."""

    ## Get DataDirectory
    data_dir = settings['GENERAL']['DataDirectory']

    ## Get path to default parameter file
    prm_path = os.path.join(ROOT_DIR, 'settings/force', 'FORCE_params__template.prm')
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
            raise IndexError(f"The field '{p}' was found more than once in FORCE_params__template.prm, which "
                             f"should not be the case!")
        else:
            indexes.append(ind[0])

    ## Change parameter fields at selected indexes
    for p, v, i in zip(parameters, values, indexes):
        lines[i] = f"{p} = {v}\n"

    ## Define new output directory and create it if necessary
    prm_dir_new = os.path.join(ROOT_DIR, 'settings/force/history')
    if not os.path.exists(prm_dir_new):
        os.makedirs(prm_dir_new)

    ## Create copy of FORCE_params__template.prm with adjusted parameter fields and return full path
    now = datetime.now().strftime('%Y%m%dT%H%M%S')
    prm_path_new = os.path.join(prm_dir_new, f"FORCE_params__{sensor}_{now}.prm")
    with open(prm_path_new, 'w') as file:
        file.writelines(lines)

    return prm_path_new, dir_level2


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


def get_datacubeprj_dir(level2_dir):
    """Recursively searches for 'datacube-definition.prj' in a level-2 directory and returns its parent directory."""

    prj_path = []
    for path in Path(level2_dir).rglob('datacube-definition.prj'):
        prj_path.append(path)

    if len(prj_path) < 1:
        raise FileNotFoundError(f"'datacube-definition.prj' could not be found in any subdirectory of {level2_dir}")
    elif len(prj_path) > 1:
        raise RuntimeError(f"Multiple files called 'datacube-definition.prj' were found in subdirectories of "
                           f"{level2_dir}. Only one file was expected.")
    else:
        return prj_path[0].parent


def force_kml_grid(level2_dir, aoi_path=None):
    """..."""

    ## Use AOI defined in settings.prm if no other path is provided
    if aoi_path is None:
        aoi_path = get_aoi_path(get_settings())

    ## Get directory of datacube-definition.prj
    prj_dir = get_datacubeprj_dir(level2_dir)

    ## Get AOI bounds and add a buffer of 0.5°
    with fiona.open(aoi_path) as f:
        bottom = f.bounds[1] - 1
        top = f.bounds[3] + 1
        left = f.bounds[0] - 1
        right = f.bounds[2] + 1

    ## Execute FORCE command with Singularity container
    Client.execute(FORCE_PATH, ["force-tabulate-grid", prj_dir, str(bottom), str(top), str(left), str(right), "kml"],
                   options=["--cleanenv"])


def force_mosaic(level2_dir):
    """..."""

    ## Get directory of datacube-definition.prj
    prj_dir = get_datacubeprj_dir(level2_dir)

    ## Execute FORCE command with Singularity container
    Client.execute(FORCE_PATH, ["force-mosaic", prj_dir],
                   options=["--cleanenv"])


def force_cube(in_dir, out_dir, prj_path=None, resample='bilinear', resolution='20'):
    """..."""

    ## No path provided = A datacube-definition file is assumed to exist in the output directory (manually copied)
    ## Full path provided = Existing datacube-definition file will be copied to output directory
    if prj_path is None:
        prj_file = os.path.join(out_dir, 'datacube-definition.prj')
        if not os.path.isfile(prj_file):
            raise FileNotFoundError(f"{prj_file} does not exist.")
    else:
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        shutil.copy(prj_path, out_dir)

    ## Get list of all GeoTIFF files
    file_paths = []
    for file in glob.iglob(os.path.join(in_dir, "**/*.tif"), recursive=True):
        file_paths.append(file)

    ## Execute FORCE command sequentially for each file
    ## Relevant: https://github.com/davidfrantz/force/issues/63
    i = 0
    total = len(file_paths)
    while i < total:
        for file in file_paths:
            i += 1
            progress(i, total, status=f"Running force-cube on {total} files")
            Client.execute(FORCE_PATH, ["force-cube", file, out_dir, resample, resolution],
                           options=["--cleanenv"])


def _crop_by_aoi(settings, in_dir, out_dir):
    """..."""

    ## Create file list
    list_files = []
    for file in glob.iglob(os.path.join(in_dir, '**/*.tif'), recursive=True):
        list_files.append(file)

    ## Get CRS from first file. All other files are assumed to be in the same CRS.
    with rasterio.open(list_files[0]) as raster:
        dst_crs = raster.crs

    ## Get AOI path and get reprojected features
    aoi_path = get_aoi_path(settings)
    features = _get_aoi_features(aoi_path=aoi_path, crs=dst_crs)

    ## Crop each raster based on features
    for file in list_files:
        # print(file)
        with rasterio.open(file) as src:
            try:
                out_image, out_transform = rasterio.mask.mask(src, features, crop=True, all_touched=True)
                out_meta = src.meta.copy()
                src_nodata = src.nodata
            ## ValueError = Raster completely outside of vector
            except ValueError:
                # print(f"Skipped: {file}")
                continue

        ## It can happen that only a nodata part of a raster is inside the vector, which results in a raster without any
        ## valid values. Using the mean seems to work pretty well and efficiently.
        if not out_image.mean() == src_nodata:
            out_meta.update({"driver": "GTiff",
                             "height": out_image.shape[1],
                             "width": out_image.shape[2],
                             "transform": out_transform})

            out_tif = os.path.join(out_dir, os.path.basename(file))
            with rasterio.open(out_tif, "w", **out_meta) as dest:
                dest.write(out_image)


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
