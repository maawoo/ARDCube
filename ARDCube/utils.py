from ARDCube.config import ROOT_DIR, PYROSAR_PATH

import configparser
import os
from spython.main import Client


def get_settings():
    """Gets the path of the settings file, reads it, checks it and returns it as a ConfigParser object."""

    ## Get path of settings file. Ask for input, if not found in current work directory.
    if 'settings.prm' not in os.listdir(ROOT_DIR):
        s_path = input(f"'settings.prm' could not be found in {ROOT_DIR}.\n"
                       f"Please provide the full path to your settings file "
                       f"(e.g. '/path/to/settings.prm'): ")
    else:
        s_path = os.path.join(ROOT_DIR, 'settings.prm')

    ## Read settings file
    settings = configparser.ConfigParser(allow_no_value=True)
    settings.read(s_path)

    # assert os.path.isdir(settings['GENERAL']['DataDirectory']), \
    #     f"Field 'DataDirectory': {settings['GENERAL']['DataDirectory']} is not a valid path!"

    return settings


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


def get_dem_path(settings):
    """..."""

    ## Get input from DEM field
    dem_input = settings['PROCESSING']['DEM']

    ## Check if input exists
    if len(dem_input) == 0:
        raise ValueError("Field 'DEM': Input missing! ")

    ## Check if 'srtm', a filename or a full path was chosen as input...
    if dem_input == 'srtm':
        dem_path = create_dem(settings)
    elif len(os.path.dirname(dem_input)) == 0:
        dem_path = os.path.join(settings['GENERAL']['DataDirectory'], 'misc/dem', dem_input)
    else:
        dem_path = dem_input

    ## Check if file exists
    if not os.path.isfile(dem_path):
        raise FileNotFoundError(f"{dem_path} does not exist!")

    return dem_path


def create_dem(settings):
    """..."""

    out_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'misc/dem')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    dem_py_path = os.path.join(ROOT_DIR, 'ARDCube/pyroSAR/dem.py')
    aoi_path = get_aoi_path(settings)
    aoi_name = os.path.splitext(os.path.basename(aoi_path))[0]

    dem_path = os.path.join(out_dir, f"SRTM_1Sec_DEM__{aoi_name}.tif")

    if os.path.isfile(dem_path):
        while True:
            answer = input(f"{dem_path} already exist.\n"
                           f"Do you want to create a new SRTM 1Sec DEM for your AOI and overwrite the existing file? \n"
                           f"If not, the existing DEM will be used for processing! (y/n)")

            if answer in ['y', 'yes']:
                Client.execute(PYROSAR_PATH, ["python", f"{dem_py_path}", f"{aoi_path}", f"{dem_path}"],
                               options=["--cleanenv"])
                break

            elif answer in ['n', 'no']:
                break

            else:
                print(f"{answer} is not a valid answer!")
                continue

    else:
        Client.execute(PYROSAR_PATH, ["python", f"{dem_py_path}", f"{aoi_path}", f"{dem_path}"],
                       options=["--cleanenv"])

    return dem_path