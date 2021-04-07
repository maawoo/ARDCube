from ARDCube.config import FORCE_PATH
import ARDCube.utils as utils

import os
import sys
import glob
import shutil
from pathlib import Path
from spython.main import Client
import fiona


def get_meta_catalogues(meta_dir):
    """Download metadata catalogues necessary for downloading via FORCE if user confirms."""

    while True:
        answer = input(f"\n{meta_dir} does not exist. \nTo download datasets via FORCE, it is necessary to have "
                       f"metadata catalogues stored in a local directory.\n "
                       f"Do you want to download the latest catalogues into {meta_dir}? (y/n)")

        if answer in ['y', 'yes']:
            print("\n#### Starting download...")
            os.makedirs(meta_dir)
            out = Client.execute(FORCE_PATH, ["force-level1-csd", "-u", meta_dir],
                                 options=["--cleanenv"], stream=True)

            for line in out:
                print(line, end='')

        elif answer in ['n', 'no']:
            print("\n#### Download cancelled...")
            sys.exit()

        else:
            print(f"\n{answer} is not a valid answer!")
            continue


def create_kml_grid(level2_dir, aoi_path=None):
    """..."""

    ## Use AOI defined in settings.prm if no other path is provided
    if aoi_path is None:
        aoi_path = utils.get_aoi_path(utils.get_settings())

    ## Get directory of datacube-definition.prj
    prj_dir = _get_datacubeprj_dir(level2_dir)

    ## Get AOI bounds and add a buffer of 0.5°
    with fiona.open(aoi_path) as f:
        bottom = f.bounds[1] - 1
        top = f.bounds[3] + 1
        left = f.bounds[0] - 1
        right = f.bounds[2] + 1

    ## Execute FORCE command with Singularity container
    Client.execute(FORCE_PATH, ["force-tabulate-grid", prj_dir, str(bottom), str(top), str(left), str(right), "kml"],
                   options=["--cleanenv"])


def create_mosaics(level2_dir):
    """..."""

    ## Get directory of datacube-definition.prj
    prj_dir = _get_datacubeprj_dir(level2_dir)

    ## Execute FORCE command with Singularity container
    Client.execute(FORCE_PATH, ["force-mosaic", prj_dir],
                   options=["--cleanenv"])


def cube_dataset(in_dir, out_dir, prj_path=None, resample='bilinear', resolution='20'):
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
            utils.progress(i, total, status=f"Running force-cube on {total} files")
            Client.execute(FORCE_PATH, ["force-cube", file, out_dir, resample, resolution],
                           options=["--cleanenv"])


def _get_datacubeprj_dir(level2_dir):
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
