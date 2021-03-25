from ARDCube.config import FORCE_PATH, SAT_DICT
from ARDCube.utils import get_settings, get_aoi_path

import sys
import os
import logging
from datetime import datetime
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from spython.main import Client


def download_level1(sensor, debug_force=False):
    """Main download script."""

    ## Check if sensor is supported.
    if sensor not in list(SAT_DICT.keys()):
        raise ValueError(f"{sensor} is not supported!")

    ## Get user defined settings
    settings = get_settings()

    ## Start download functions
    ## Both functions print query information first and then ask for confirmation to start the download.
    print(f"#### Start download query for {sensor}...")

    if sensor == 'sentinel1':
        download_sar(settings=settings)

    else:
        download_optical(settings=settings,
                         sensor=sensor,
                         debug_force=debug_force)


def download_sar(settings):
    """Download Sentinel-1 GRD data from Copernicus Open Access Hub based on parameters defined in 'settings.prm'.
    https://github.com/sentinelsat/sentinelsat
    """
    ## TODO: Include SAROrbitDirection to query only ascending/descending scenes

    out_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level1', 'sentinel1')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    ## Create logfile for sentinelsat output by default
    ## https://sentinelsat.readthedocs.io/en/stable/api.html#logging
    log_file = os.path.join(settings['GENERAL']['DataDirectory'], 'log',
                            f"{datetime.now().strftime('%Y%m%dT%H%M%S__download_sentinel1')}.log")
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))
    logging.basicConfig(filename=log_file, filemode='w', format='%(message)s', level='INFO')

    ## Get footprint from AOI
    aoi_path = get_aoi_path(settings)
    footprint = geojson_to_wkt(read_geojson(aoi_path))

    ## Get timespan
    timespan = (settings['DOWNLOAD']['TimespanMin'],
                settings['DOWNLOAD']['TimespanMax'])

    ## Connect to Copernicus Open Access Hub using provided credentials.
    ## The API defaults to https://scihub.copernicus.eu/apihub
    api = SentinelAPI(settings['DOWNLOAD']['CopernicusUser'],
                      settings['DOWNLOAD']['CopernicusPassword'])

    ## Perform a query using provided parameters
    query = api.query(area=footprint,
                      date=timespan,
                      platformname='Sentinel-1',
                      producttype='GRD')

    ## Before starting the download, print out query information and then ask for user confirmation.
    while True:
        answer = input(f"\n{len(query)} Sentinel-1 GRD scenes were found between {timespan[0]} and {timespan[1]} \n"
                       f"for the AOI defined by '{aoi_path}'. \n"
                       f"\nThe total file size is {api.get_products_size(query)} GB \n"
                       f"\nOutput directory: {out_dir} \n"
                       f"Do you want to proceed with the download? (y/n)")

        if answer in ['y', 'yes']:
            print("#### Starting download...")
            api.download_all(query,
                             directory_path=out_dir)
            break

        elif answer in ['n', 'no']:
            print("#### Download cancelled...")
            break

        else:
            print(f"{answer} is not a valid answer!")
            continue


def download_optical(settings, sensor, debug_force=False):
    """Download optical satellite data from Google Cloud Storage based on parameters defined in 'settings.prm'.
    https://force-eo.readthedocs.io/en/latest/howto/level1-csd.html#tut-l1csd
    """

    Client.debug = debug_force

    ## Collect all information that will be used in the query
    force_abbr = SAT_DICT[sensor]
    daterange = f"{settings['DOWNLOAD']['TimespanMin']}," \
                f"{settings['DOWNLOAD']['TimespanMax']}"
    cloudcover = f"{settings['DOWNLOAD']['OpticalCloudCoverRangeMin']}," \
                 f"{settings['DOWNLOAD']['OpticalCloudCoverRangeMax']}"

    meta_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'meta/catalogues')
    if not os.path.exists(meta_dir):
        _download_meta_catalogues(meta_dir)

    out_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level1', sensor)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    aoi_path = get_aoi_path(settings)

    ## Send query to FORCE Singularity container as dry run first ("--no-act") and print output
    output = Client.execute(FORCE_PATH, ["force-level1-csd", "--no-act", "-s", force_abbr, "-d", daterange,
                                         "-c", cloudcover, meta_dir, out_dir, "queue.txt", aoi_path],
                            options=["--cleanenv"])

    if debug_force:
        for line in output:
            print(line)
    else:
        print(output)

    ## Before starting the download, ask for user confirmation.
    ## Same command as above will be send to container, but without the "--no-act" flag
    while True:
        answer = input(f"Output directory: {out_dir} \n"
                       f"Do you want to proceed with the download? (y/n)")

        if answer in ['y', 'yes']:

            print("#### Starting download... \n"
                  "Depending on the dataset size and your internet speed, this might take a while. \n"
                  "Unfortunately there's currently no good solution to show the download progress. \n"
                  "If the download takes longer than you intended, you can just cancel the process \n"
                  "and start it again at a later time using the same settings in the settings.prm file. \n"
                  "FORCE automatically checks for existing scenes and will only download new scenes!")

            Client.execute(FORCE_PATH, ["force-level1-csd", "-s", force_abbr, "-d", daterange,
                                        "-c", cloudcover, meta_dir, out_dir, "queue.txt", aoi_path],
                           options=["--cleanenv"])

            break

        elif answer in ['n', 'no']:
            print("#### Download cancelled...")
            break

        else:
            print(f"{answer} is not a valid answer!")
            continue


def _download_meta_catalogues(meta_dir):
    """Download metadata catalogues necessary for downloading via FORCE if user confirms."""

    while True:
        answer = input(f"{meta_dir} does not exist. \nTo download datasets via FORCE, it is necessary to have "
                       f"metadata catalogues stored in a local directory.\n "
                       f"Do you want to download the latest catalogues into {meta_dir}? (y/n)")

        if answer in ['y', 'yes']:
            os.makedirs(meta_dir)
            Client.execute(FORCE_PATH, ["force-level1-csd", "-u", meta_dir], options=["--cleanenv"])

        elif answer in ['n', 'no']:
            sys.exit()

        else:
            print(f"{answer} is not a valid answer!")
            continue
