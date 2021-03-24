from ARDCube.config import ROOT_DIR, PYROSAR_PATH, SAT_DICT

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

    dict_out = {}
    for sat in list(SAT_DICT.keys()):
        if settings.getboolean('GENERAL', sat):

            ## Define dict content and create entry
            force_abbr = SAT_DICT[sat]
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
