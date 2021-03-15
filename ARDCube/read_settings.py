import configparser
import os


def get_settings(section=None, check=False):
    """Gets the path of the settings file, reads it, checks it and returns it as a ConfigParser object."""

    ## Get path of settings file. Ask for input, if not found in current work directory.
    if 'settings.prm' not in os.listdir(os.getcwd()):
        s_path = str(input(f"\'settings.prm\' could not be found in {os.getcwd()}.\n"
                           f"Please provide the full path to your settings file "
                           f"(e.g. \'/path/to/settings.prm\'): "))
    else:
        s_path = os.path.join(os.getcwd(), 'settings.prm')

    ## Read settings file
    settings = configparser.ConfigParser(allow_no_value=True)
    settings.read(s_path)

    ## Check content of settings file only if parameter is set to True
    ## The check will already be run once during module import (see last few lines of this script)
    if check:
        _check_settings(settings, s_path)

    ## Return either full settings or only a specific section
    if section is None:
        return settings
    else:
        return settings[section]


def _check_settings(settings, path):
    """Helper function to check certain fields in the settings file."""

    ## TODO: Use something else then assert-statements? Apparently they should only be used during development.

    try:
        general = settings['GENERAL']
    except KeyError:
        raise KeyError(f"Can\'t find section \'GENERAL\' in settings file: {path}")

    assert os.path.isdir(general['DataDirectory']), f"Field \'DataDirectory\': " \
                                                    f"{general['DataDirectory']} is not a valid path!"
    # assert FilenameAOI / PathAOI
    # assert FilenameDEM / PathDEM
    # assert Timespan

    for sensor in ['Sentinel1', 'Sentinel2', 'Landsat8']:
        try:
            general.getboolean(sensor)
        except ValueError:
            raise ValueError(f"Field \'{sensor}\': Must be a boolean!")

    assert general['SAROrbitDirection'] is None or 'asc' or 'desc', f"Field \'SAROrbitDirection\': " \
                                                                    f"{general['SAROrbitDirection']} " \
                                                                    f"is not a valid option!"
    # assert OpticalCloudCoverRange

    # assert fields in [PROCESSING]
    # ...


## Do a check once during module import and leave it as optional afterwards.
## This way it doesn't need to be executed all the time get_settings() is called.
get_settings(check=True)
