from ARDCube.read_settings import get_settings

import os
import logging
from datetime import datetime
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from spython.main import Client


def download_level1():
    """Main download script."""

    ## Get user defined settings
    settings = get_settings(section='GENERAL')

    ## Check which datasets should be downloaded based on settings.
    ## TODO: Make settings file and code more flexible, so it's easier to add other sensors (e.g. Landsat!).
    sat_dict = {'Sentinel1': ['S1', ''],
                'Sentinel2': ['S2', 'S2A,S2B'],
                'Landsat8': ['L8', 'LC08']}
    sats = _get_sat_settings(settings=settings,
                             sat_dict=sat_dict)

    if 'Sentinel1' in list(sats.keys()):
        print("#### \nStarting download script for Sentinel-1... \n####")
        download_sar(settings=settings,
                     out_dir=sats['Sentinel1'][2])

    if 'Sentinel2' in list(sats.keys()):
        print("#### \nStarting download script for Sentinel-2... \n####")
        download_optical(settings=settings,
                         out_dir=sats['Sentinel2'][2],
                         force_abbr=sats['Sentinel2'][1])

    if 'Landsat8' in list(sats.keys()):
        print("#### \nStarting download script for Landsat 8... \n####")
        download_optical(settings=settings,
                         out_dir=sats['Landsat8'][2],
                         force_abbr=sats['Landsat8'][1])


def download_sar(settings, out_dir, log=False):
    """Download Sentinel-1 GRD data from Copernicus Open Access Hub based on parameters defined in 'settings.prm'.
    https://github.com/sentinelsat/sentinelsat
    """
    ## TODO: Include SAROrbitDirection

    ## https://sentinelsat.readthedocs.io/en/stable/api.html#logging
    if log:
        filename = os.path.join(settings['GENERAL']['DataDirectory'], 'log',
                                f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S__download_s1')}.log")
        logging.basicConfig(filename=filename, filemode='w', format='%(message)s', level='INFO')

    ## Get footprint from AOI
    aoi_path = _get_aoi_path(settings)
    footprint = geojson_to_wkt(read_geojson(aoi_path))

    ## Get timespan
    timespan = (settings['DOWNLOAD']['TimespanMin'], settings['DOWNLOAD']['TimespanMax'])

    ## Connect to Copernicus Open Access Hub using provided credentials.
    ## The API defaults to https://scihub.copernicus.eu/apihub
    api = SentinelAPI(settings['DOWNLOAD']['CopernicusUser'], settings['DOWNLOAD']['CopernicusPassword'])

    ## Perform a query using provided parameters
    query = api.query(footprint,
                      date=timespan,
                      platformname='Sentinel-1',
                      producttype='GRD')

    ## Print query information and ask user if download should be started or not.
    while True:
        answer = input(f"{len(query)} Sentinel-1 GRD files were found between {timespan[0]} and {timespan[1]} \n"
                       f"for the AOI defined by \'{aoi_path}\'. \n"
                       f"The total file size is {api.get_products_size(query)} GB \n"
                       f"Do you want to proceed with the download? (y/n)")
        if answer in ['y', 'yes', 'n', 'no']:
            break
        else:
            print(f"{answer} is not a valid answer! \n ----------")
            continue

    if answer in ['y', 'yes']:
        api.download_all(query, directory_path=out_dir)


def download_optical(settings, out_dir, force_abbr, debug=False):
    """Download optical satellite data from Google Cloud Storage based on parameters defined in 'settings.prm'.
    https://force-eo.readthedocs.io/en/latest/howto/level1-csd.html#tut-l1csd
    """

    sensors = force_abbr
    daterange = f"{settings['DOWNLOAD']['TimespanMin']}," \
                f"{settings['DOWNLOAD']['TimespanMax']}"
    cloudcover = f"{settings['DOWNLOAD']['OpticalCloudCoverRangeMin']}," \
                 f"{settings['DOWNLOAD']['OpticalCloudCoverRangeMax']}"
    meta_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'meta/force')
    aoi_path = _get_aoi_path(settings)

    force_path = _get_force_path()
    Client.debug = debug

    output = Client.execute(force_path, ["force-level1-csd", "--no-act", "-s", sensors, "-d", daterange,
                                         "-c", cloudcover, meta_dir, out_dir, "queue.txt", aoi_path],
                            options=["--cleanenv"])

    ## Print query information for dry run ("--no-act") first and then ask user if download should be started or not.
    if debug:
        for line in output:
            print(line)
    else:
        print(output)

    while True:
        answer = input(f"Do you want to proceed with the download? (y/n)")
        if answer in ['y', 'yes', 'n', 'no']:
            break
        else:
            print(f"{answer} is not a valid answer! \n ----------")
            continue

    ## Start download only if confirmed by user
    if answer in ['y', 'yes']:
        print("\n#### \nStarting download... \n"
              "Depending on the dataset size and your internet speed, this might take a while. \n"
              "Unfortunately there's currently no good solution to show the download progress. \n"
              "If the download takes longer than you intended, you can just cancel the process and start it again \n"
              "at a later time using the same settings in the settings.prm file. \n"
              "FORCE checks for existing scenes and will only download new scenes!")
        Client.execute(force_path, ["force-level1-csd", "-s", sensors, "-d", daterange,
                                    "-c", cloudcover, meta_dir, out_dir, "queue.txt", aoi_path],
                       options=["--cleanenv"])


def _get_aoi_path(settings):
    """Gets the full path to the AOI file based on settings."""

    if os.path.isdir(settings['GENERAL']['AOI']):
        aoi_path = settings['GENERAL']['AOI']
    else:
        aoi_path = os.path.join(settings['GENERAL']['DataDirectory'], 'misc/aoi', settings['GENERAL']['AOI'])

    return aoi_path


def _get_sat_settings(settings, sat_dict):
    """Creates a dictionary based on which satellite fields were set to True in settings file."""

    dict_out = {}

    for sat in list(sat_dict.keys()):
        if settings.getboolean(sat):

            s_full = sat
            s_short = sat_dict[sat][0]
            force_abbr = sat_dict[sat][1]
            out_dir = os.path.join(settings['GENERAL']['DataDirectory'], f"level-1/{s_short}")

            dict_out[s_full] = [s_short, force_abbr, out_dir]

            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

    return dict_out


def _get_force_path():
    """Gets the full path to the FORCE Singularity container (force.sif)."""

    ## TODO: Move this to an auxiliary module? Need to get the path during processing as well...

    ## Ask for input, if not found in expected directory (/cwd/singularity/force).
    force_dir = os.path.join(os.getcwd(), 'singularity/force')
    if 'force.sif' not in os.listdir(force_dir):
        force_path = input(f"\'force.sif\' could not be found in \'{force_dir}\'.\n"
                           f"Please provide the full path to \'force.sif\' "
                           f"(e.g. \'/path/to/force.sif\'): ")
    else:
        force_path = os.path.join(force_dir, 'force.sif')

    return force_path
