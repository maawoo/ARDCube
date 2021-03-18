from ARDCube.config import ROOT_DIR, PYROSAR_PATH
from ARDCube.read_settings import get_settings
from ARDCube.auxiliary.aux import get_aoi_path

import os
from spython.main import Client


def create_dem():
    settings = get_settings()

    if settings['GENERAL']['DEM'] == 'srtm':

        dem_py_path = os.path.join(ROOT_DIR, 'ARDCube/auxiliary/dem.py')
        aoi_path = get_aoi_path(settings)

        out_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'misc/dem/test')
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        Client.execute(PYROSAR_PATH, ["python", f"{dem_py_path}", f"{aoi_path}", f"{out_dir}"],
                       options=["--cleanenv"])
