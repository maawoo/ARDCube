from ARDCube.config import ROOT_DIR, PYROSAR_PATH

import configparser
import os
import sys
from spython.main import Client


def get_settings():
    """Gets the path of the settings file, reads it, checks it and returns it as a ConfigParser object."""

    settings_file = os.path.join(ROOT_DIR, 'settings', 'settings.prm')

    if not os.path.isfile(settings_file):
        raise FileNotFoundError(f"{settings_file} does not exist.")

    settings = configparser.ConfigParser(allow_no_value=True)
    settings.read(settings_file)

    isdir_mkdir(settings['GENERAL']['DataDirectory'])

    return settings


def get_aoi_path(settings):
    """Returns the full path of the AOI file based on what was provided in the 'AOI' field in settings.prm"""

    aoi_field = settings['GENERAL']['AOI']

    if len(aoi_field) == 0:
        raise RuntimeError("Field 'AOI': Input missing!")

    ## Field can be filename (assumed to be in the /misc/aoi subdirectory of DataDirectory) or full path
    if not os.path.isfile(aoi_field):
        aoi_path = os.path.join(settings['GENERAL']['DataDirectory'], 'misc', 'aoi', aoi_field)
    else:
        aoi_path = aoi_field

    if not os.path.isfile(aoi_path):
        raise FileNotFoundError(f"{aoi_path} does not exist! \n"
                                f"Please check your settings.prm for correct input of field 'AOI'!")

    return aoi_path


def get_dem_path(settings):
    """Returns the full path of the DEM file based on what was provided in the 'DEM' field in settings.prm"""

    dem_field = settings['PROCESSING']['DEM']

    if len(dem_field) == 0:
        raise RuntimeError("Field 'DEM': Input missing!")

    if not os.path.isfile(dem_field):
        if dem_field == 'srtm':
            dem_path = create_srtm(settings)
            dem_nodata = -32768
        else:
            ## Input -> Filename (and the crystal ball says it's located in the /misc/dem subdirectory of DataDirectory)
            dem_path = os.path.join(settings['GENERAL']['DataDirectory'], 'misc', 'dem', dem_field)
            dem_nodata = settings['PROCESSING']['DEM_NoData']
    else:
        ## Input -> Full path to an existing file
        dem_path = dem_field
        dem_nodata = settings['PROCESSING']['DEM_NoData']

    if not os.path.isfile(dem_path):
        raise FileNotFoundError(f"{dem_path} does not exist!")

    return dem_path, dem_nodata


def create_srtm(settings):
    """Creates a 1Sec SRTM DEM for the AOI using the pyroSAR Singularity container."""

    out_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'misc', 'dem')
    isdir_mkdir(out_dir)

    dem_py_path = os.path.join(ROOT_DIR, 'ARDCube', 'pyroSAR', 'srtm.py')
    aoi_path = get_aoi_path(settings)
    aoi_name = os.path.splitext(os.path.basename(aoi_path))[0]

    dem_path = os.path.join(out_dir, f"SRTM_1Sec_DEM__{aoi_name}.tif")

    if os.path.isfile(dem_path):
        while True:
            answer = input(f"{dem_path} already exist.\n"
                           f"Do you want to create a new SRTM 1Sec DEM for your AOI and overwrite the existing file? \n"
                           f"If not, the existing DEM file will be used for processing! (y/n)")
            if answer in ['y', 'yes']:
                Client.execute(PYROSAR_PATH, ["python", dem_py_path, aoi_path, dem_path],
                               options=["--cleanenv"])
                break
            elif answer in ['n', 'no']:
                break
            else:
                print(f"{answer} is not a valid answer!")
                continue
    else:
        Client.execute(PYROSAR_PATH, ["python", dem_py_path, aoi_path, dem_path],
                       options=["--cleanenv"])

    return dem_path


def isdir_mkdir(directory):
    """Helper function to create a directory (or each directory in a list) if it doesn't exist already."""

    if isinstance(directory, str):
        if not os.path.isdir(directory):
            os.mkdir(directory)
    elif isinstance(directory, list):
        for d in directory:
            if not os.path.isdir(d):
                os.mkdir(d)
    else:
        raise TypeError("Input must be a single PathLike[str] or a list thereof.")


def progress(count, total, status=''):
    """
    Source: https://gist.github.com/vladignatyev/06860ec2040cb497f0f3

    # The MIT License (MIT)
    # Copyright (c) 2016 Vladimir Ignatev
    #
    # Permission is hereby granted, free of charge, to any person obtaining
    # a copy of this software and associated documentation files (the "Software"),
    # to deal in the Software without restriction, including without limitation
    # the rights to use, copy, modify, merge, publish, distribute, sublicense,
    # and/or sell copies of the Software, and to permit persons to whom the Software
    # is furnished to do so, subject to the following conditions:
    #
    # The above copyright notice and this permission notice shall be included
    # in all copies or substantial portions of the Software.
    #
    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
    # INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
    # PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE
    # FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT
    # OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
    # OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    """

    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', status))
    sys.stdout.flush()
