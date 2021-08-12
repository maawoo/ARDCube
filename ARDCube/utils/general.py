from ARDCube import ROOT_DIR
from ARDCube.config import PROJ_DIR, PYROSAR_PATH, DEM_TYPES

import os
import shutil
import sys
from spython.main import Client
import geopandas as gpd
import rasterio


def setup_project(directory, build_containers=False):
    """Sets up the necessary directory structure and copies files related to parameterization and Singularity into the
    'management' subdirectory."""

    ## Create directory structure
    dirs_main = {'data': ['level1', 'level2', 'log', 'meta', 'misc', 'temp'],
                 'management': ['settings', 'singularity']}
    for main_dir, sub_dirs in dirs_main.items():
        isdir_mkdir(os.path.join(directory, main_dir))
        for sub in sub_dirs:
            isdir_mkdir(os.path.join(directory, main_dir, sub))

    ## Copy files
    for sub in dirs_main['management']:
        _copytree(src=os.path.join(ROOT_DIR, 'resources', sub),
                  dst=os.path.join(directory, 'management', sub))

    ## Save 'ProjectDirectory' parameter in settings.prm
    _save_projdir(project_directory=directory)

    ## Build Singularity containers
    if build_containers:
        print('#### Building Singularity containers...')
        singularity_dir = os.path.join(directory, 'management', 'singularity')
        cookbook = ['force.def', 'postgres.def', 'pyrosar.def']

        for recipe in cookbook:
            image, out = Client.build(recipe=os.path.join(singularity_dir, 'recipes', recipe),
                                      image=os.path.join(singularity_dir,
                                                         f"{os.path.basename(recipe).split('.')[0]}.sif"),
                                      stream=True)

            for line in out:
                print(line, end='')

            print(f'Finished building {image}')


def _copytree(src, dst, symlinks=False, ignore=None):
    """Helper function for setup_project(). https://stackoverflow.com/a/12514470"""

    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            try:
                shutil.copytree(s, d, symlinks, ignore)
            except FileExistsError:
                pass
        else:
            if not os.path.exists(d):
                shutil.copy2(s, d)


def _save_projdir(project_directory):
    """Save the user selected project directory in the original settings.prm, i.e. located where the ARDCube package was
    installed, as well as the copied version located in the newly created project directory.
    The former is done to make sure that the project directory can be accessed during different sessions, while
    avoiding the creation of a system-wide environmental variable."""

    settings_file_local = os.path.join(ROOT_DIR, 'resources', 'settings', 'settings.prm')
    settings_proj = os.path.join(project_directory, 'management', 'settings', 'settings.prm')

    prm_paths = [settings_file_local, settings_proj]
    for prm in prm_paths:
        with open(prm, 'r') as file:
            prm_lines = file.readlines()
            ind = [i for i, item in enumerate(prm_lines) if item.startswith('ProjectDirectory')]
        prm_lines[ind[0]] = f"ProjectDirectory = {project_directory}\n"
        with open(prm, 'w') as file:
            file.writelines(prm_lines)


def get_aoi_path(settings):
    """Returns the full path of the AOI file based on what was provided in the 'AOI' field in 'settings.prm'"""

    aoi_field = settings['GENERAL']['AOI']

    if len(aoi_field) == 0:
        raise RuntimeError("Field 'AOI': Input missing!")

    ## Field can be filename (assumed to be located in the directory /{ProjectDirectory}/data/misc/aoi ) or full path
    if not os.path.isfile(aoi_field):
        aoi_path = os.path.join(PROJ_DIR, 'data', 'misc', 'aoi', aoi_field)
    else:
        aoi_path = aoi_field

    if not os.path.isfile(aoi_path):
        raise FileNotFoundError(f"{aoi_path} does not exist! \n"
                                f"Please check your settings.prm for correct input of field 'AOI'!")

    return aoi_path


def get_dem_path(settings):
    """Returns the full path of the DEM file based on what was provided in the 'DEM' field in 'settings.prm'"""

    dem_field = settings['PROCESSING']['DEM']

    if len(dem_field) == 0:
        raise RuntimeError("Field 'DEM': Input missing!")

    if not os.path.isfile(dem_field):
        ## Input -> pyroSAR.auxdata.dem_autoload option
        if dem_field in DEM_TYPES:
            dem_path, dem_nodata = create_dem(settings=settings, dem_type=dem_field)
        else:
            ## Input -> Filename of an existing DEM file that is assumed to be located in the directory
            ## /{ProjectDirectory}/data/misc/dem
            dem_path = os.path.join(PROJ_DIR, 'data', 'misc', 'dem', dem_field)
            dem_nodata = settings['PROCESSING']['DEM_NoData']
    else:
        ## Input -> Path to an existing DEM file that is not located in the directory mentioned above
        dem_path = dem_field
        dem_nodata = settings['PROCESSING']['DEM_NoData']

    if not os.path.isfile(dem_path):
        raise FileNotFoundError(f"{dem_path} does not exist!")

    return dem_path, dem_nodata


def create_dem(settings, dem_type):
    """Creates a Digital Elevation Model for the AOI using the pyroSAR Singularity container."""

    out_dir = os.path.join(PROJ_DIR, 'data', 'misc', 'dem')
    isdir_mkdir(out_dir)

    dem_py_path = os.path.join(PROJ_DIR, 'management', 'settings', 'pyrosar', 'dem.py')
    aoi_path = _aoi_wgs84(aoi_path=get_aoi_path(settings))
    aoi_name = os.path.splitext(os.path.basename(aoi_path))[0]

    dem_path = os.path.join(out_dir, f"{dem_type}__{aoi_name}.tif")

    if os.path.isfile(dem_path):
        while True:
            answer = input(f"{dem_path} already exist.\n"
                           f"Do you want to create a new {dem_type} DEM for your AOI and overwrite the existing file? \n"
                           f"If not, the existing file will be used for processing! (y/n)")
            if answer in ['y', 'yes']:
                Client.execute(PYROSAR_PATH, ["python", dem_py_path, aoi_path, dem_path, dem_type],
                               options=["--cleanenv"])
                break
            elif answer in ['n', 'no']:
                break
            else:
                print(f"{answer} is not a valid answer!")
                continue
    else:
        Client.execute(PYROSAR_PATH, ["python", dem_py_path, aoi_path, dem_path, dem_type],
                       options=["--cleanenv"])

    with rasterio.open(dem_path) as dem:
        dem_nodata = dem.nodata

    return dem_path, dem_nodata


def _aoi_wgs84(aoi_path):
    """Helper function for create_dem() to convert AOI to WGS84 if necessary. Otherwise DEM creation fails."""

    aoi = gpd.read_file(aoi_path)

    if not aoi.crs.to_epsg() is 4326:
        base = os.path.splitext(aoi_path)[0]
        suffix = os.path.splitext(aoi_path)[1]
        out_path = f"{base}_4326{suffix}"

        if not os.path.isfile(out_path):
            aoi.to_crs(4326).to_file(filename=out_path, driver=_get_driver(suffix))
        else:
            pass
        return out_path

    else:
        return aoi_path


def _get_driver(suffix):
    """Helper function for _aoi_wgs84() to return OGR format driver based on file suffix."""

    if suffix == ".shp":
        return "ESRI Shapefile"
    elif suffix == ".gpkg":
        return "GPKG"
    elif suffix == ".geojson":
        return "GeoJSON"
    else:
        raise RuntimeError(f"{suffix} is not a supported format for the AOI file.")


def isdir_mkdir(directory):
    """Create a directory (or each directory in a list) if it doesn't exist already."""

    if isinstance(directory, str):
        if not os.path.isdir(directory):
            os.mkdir(directory)
    elif isinstance(directory, list):
        for d in directory:
            if not os.path.isdir(d):
                os.mkdir(d)


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
