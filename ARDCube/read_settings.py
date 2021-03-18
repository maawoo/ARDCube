from ARDCube.config import ROOT_DIR

import configparser
import os


def get_settings(check=False):
    """Gets the path of the settings file, reads it, checks it and returns it as a ConfigParser object."""

    ## Get path of settings file. Ask for input, if not found in current work directory.
    if 'settings.prm' not in os.listdir(ROOT_DIR):
        s_path = input(f"\'settings.prm\' could not be found in {ROOT_DIR}.\n"
                       f"Please provide the full path to your settings file "
                       f"(e.g. \'/path/to/settings.prm\'): ")
    else:
        s_path = os.path.join(ROOT_DIR, 'settings.prm')

    ## Read settings file
    settings = configparser.ConfigParser(allow_no_value=True)
    settings.read(s_path)

    ## Check content of settings file only if parameter is set to True
    ## The check will already be run once during module import (see last few lines of this script)
    if check:
        _check_settings(settings)

    return settings


def _check_settings(settings):
    """Helper function to check certain fields in the settings file."""

    ## TODO: Use something else then assert-statements? Apparently they should only be used during development.

    ## ['GENERAL']
    assert os.path.isdir(settings['GENERAL']['DataDirectory']), \
        f"Field \'DataDirectory\': {settings['GENERAL']['DataDirectory']} is not a valid path!"
    # assert AOI?
    # assert DEM?
    for sensor in ['Sentinel1', 'Sentinel2', 'Landsat8']:
        try:
            settings.getboolean('GENERAL', sensor)
        except ValueError:
            raise ValueError(f"Field \'{sensor}\': Must be a boolean!")

    ## ['DOWNLOAD']
    # assert Timespan
    # assert OpticalCloudCoverRange
    assert settings['DOWNLOAD']['SAROrbitDirection'] is None or 'asc' or 'desc', \
        f"Field \'SAROrbitDirection\': {settings['DOWNLOAD']['SAROrbitDirection']} is not a valid option!"

    ## [PROCESSING]
    # ...


## Do a check once during module import and leave it as optional afterwards.
## This way it doesn't need to be executed all the time get_settings() is called.
get_settings(check=True)
