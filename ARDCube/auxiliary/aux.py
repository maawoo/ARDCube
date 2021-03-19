from ARDCube.config import ROOT_DIR, PYROSAR_PATH

import os
from spython.main import Client


def get_aoi_path(settings):
    """Gets the full path to the AOI file based on settings."""

    if os.path.isfile(settings['GENERAL']['AOI']):
        ## Full path provided and file exists! Whoop!
        aoi_path = settings['GENERAL']['AOI']
    else:
        ## Filename provided only, which is assumed to be located in the subdirectory '/DataDirectory/misc/aoi'
        ## as described in settings.prm!
        aoi_path = os.path.join(settings['GENERAL']['DataDirectory'], 'misc/aoi',
                                settings['GENERAL']['AOI'])

        ## Check if the file actually exists...
        if not os.path.isfile(aoi_path):
            raise FileNotFoundError(f"{aoi_path} does not exist! \n"
                                    f"Please check your settings.prm for correct input of field 'AOI'!")

    return aoi_path


def check_sat_settings(settings):
    """Creates a dictionary based on which satellite fields were set to True in settings file."""

    ## Key = Satellite sensor name as listed in settings.prm
    ## Value = Abbreviation used in FORCE download module
    sat_dict = {'Sentinel1': None,
                'Sentinel2': 'S2A,S2B',
                'Landsat4': 'LT04',
                'Landsat5': 'LT05',
                'Landsat7': 'LE07',
                'Landsat8': 'LC08'}

    dict_out = {}
    for sat in list(sat_dict.keys()):
        if settings.getboolean(sat):

            ## Define dict content and create entry
            force_abbr = sat_dict[sat]
            level1_dir = os.path.join(settings['GENERAL']['DataDirectory'], f"level1/{sat}")
            level2_dir = os.path.join(settings['GENERAL']['DataDirectory'], f"level2/{sat}")

            dict_out[sat] = {'force_abbr': force_abbr,
                             'level1_dir': level1_dir,
                             'level2_dir': level2_dir}

            ## Create directories for level1 (download) and level2 (processing) if they don't exist already
            if not os.path.exists(level1_dir):
                os.makedirs(level1_dir)
            if not os.path.exists(level2_dir):
                os.makedirs(level2_dir)

    return dict_out


def create_dem(settings):
    """..."""

    dem_py_path = os.path.join(ROOT_DIR, 'ARDCube/auxiliary/dem.py')
    aoi_path = get_aoi_path(settings)

    out_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'misc/dem')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    Client.execute(PYROSAR_PATH, ["python", f"{dem_py_path}", f"{aoi_path}", f"{out_dir}"],
                   options=["--cleanenv"])

    return os.path.join(out_dir, 'srtm.tif')
