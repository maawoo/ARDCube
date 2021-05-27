from ARDCube.config import FORCE_PATH
import ARDCube.utils.general as utils

import os
import sys
import glob
import shutil
from pathlib import Path
from spython.main import Client
import fiona


def download_catalogues(directory):
    """Download metadata catalogues necessary for the 'force-level1-csd' module of FORCE."""

    while True:
        answer = input(f"\nTo download datasets via FORCE, it is necessary to have "
                       f"metadata catalogues stored in a local directory (size ~9 GB).\n "
                       f"More information: https://force-eo.readthedocs.io/en/latest/howto/level1-csd.html#downloading-the-metadata-catalogues \n"
                       f"Do you want to download the latest catalogues into {directory}? (y/n)")

        if answer in ['y', 'yes']:
            print("\n#### Starting download of metadata catalogues...")
            utils.isdir_mkdir(directory)

            out = Client.execute(FORCE_PATH, ["force-level1-csd", "-u", directory],
                                 options=["--cleanenv"], stream=True)
            for line in out:
                print(line, end='')

        elif answer in ['n', 'no']:
            print("\n#### Download cancelled...")
            sys.exit()
        else:
            print(f"\n{answer} is not a valid answer!")
            continue


def create_kml_grid(directory):
    """Wrapper for 'force-tabulate-grid'."""

    aoi_path = utils.get_aoi_path(settings=utils.get_settings())
    prj_dir = _get_datacubeprj_dir(directory)

    ## Get AOI bounds and add a buffer of 1°
    with fiona.open(aoi_path) as f:
        bottom = f.bounds[1] - 1
        top = f.bounds[3] + 1
        left = f.bounds[0] - 1
        right = f.bounds[2] + 1

    Client.execute(FORCE_PATH, ["force-tabulate-grid", prj_dir, str(bottom), str(top), str(left), str(right), "kml"],
                   options=["--cleanenv"])


def create_mosaics(directory):
    """Wrapper for 'force-mosaic'."""

    prj_dir = _get_datacubeprj_dir(directory)

    Client.execute(FORCE_PATH, ["force-mosaic", prj_dir],
                   options=["--cleanenv"])


def cube_dataset(directory, prj_file=None, resample='bilinear', resolution=20):
    """Wrapper for 'force-cube'."""

    ##TODO: Fallback datacube.prj file in /settings/pyrosar !

    ## No path provided = A datacube-definition file is assumed to exist in the output directory (manually copied)
    ## Full path provided = Existing datacube-definition file will be copied to output directory
    if prj_file is None:
        prj_file = os.path.join(directory, 'datacube-definition.prj')
        if not os.path.isfile(prj_file):
            raise FileNotFoundError(f"{prj_file} does not exist.")
    else:
        shutil.copyfile(prj_file, os.path.join(directory, os.path.basename(prj_file)))

    ## Get list of all GeoTIFF files
    file_paths = []
    for file in glob.iglob(os.path.join(directory, "**/*.tif"), recursive=True):
        file_paths.append(file)

    ## Execute FORCE command sequentially for each file
    ## Relevant: https://github.com/davidfrantz/force/issues/63
    i = 0
    total = len(file_paths)
    while i < total:
        for file in file_paths:
            i += 1
            utils.progress(i, total, status=f"Running force-cube on {total} files")
            Client.execute(FORCE_PATH, ["force-cube", file, directory, resample, str(resolution)],
                           options=["--cleanenv"])

            os.remove(file)


def _get_datacubeprj_dir(directory):
    """Recursively searches for 'datacube-definition.prj' in a level-2 directory and returns its parent directory."""

    prj_path = []
    for path in Path(directory).rglob('datacube-definition.prj'):
        prj_path.append(path)

    if len(prj_path) < 1:
        raise FileNotFoundError(f"'datacube-definition.prj' not found in {directory}")
    elif len(prj_path) > 1:
        raise RuntimeError(f"'datacube-definition.prj' multiple copies found in {directory}")
    else:
        return prj_path[0].parent
