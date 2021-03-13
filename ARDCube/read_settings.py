import configparser
import os


def get_settings():
    """Gets the path of the settings file, reads it, checks it and returns it as a ConfigParser object."""

    ## Get path of settings file. Ask for input, if not found in current work directory.
    if 'settings.prm' not in os.listdir(os.getcwd()):
        s_path = str(input(f'\'settings.prm\' could not be found in {os.getcwd()}.\n'
                           f'Please provide the full path to your settings file '
                           f'(e.g. \'/path/to/settings.prm\'): '))
    else:
        s_path = os.path.join(os.getcwd(), 'settings.prm')

    ## Read settings file
    settings = configparser.ConfigParser()
    settings.read(s_path)

    ## Check content of settings file
    check_settings(settings, s_path)

    return settings


def check_settings(settings, path):
    """Helper function to check certain fields in the settings file."""

    try:
        general = settings['GENERAL']
    except KeyError:
        print(f'Can\'t find section \'[GENERAL]\' in settings file: {path}')

    assert os.path.isdir(general['DataDirectory']), f"{general['DataDirectory']} is not a valid path!"
    # assert FilenameAOI / PathAOI
    # assert FilenameDEM / PathDEM
    # assert Timespan
    general.getboolean('Sentinel1')
    general.getboolean('Sentinel2')
    general.getboolean('Landsat8')
    assert general['SAROrbitDirection'] == 'both' or 'asc' or 'desc', f"{general['SAROrbitDirection']} is not a valid" \
                                                                      f" option for the field \'SAROrbitDirection\'!" \
                                                                      f"\n Valid options are: " \
                                                                      f"\'asc\', \'desc\' or \'both\'."
    # assert OpticalCloudCoverRange

    # assert fields in [PROCESSING]
    # ...

    # return something?
