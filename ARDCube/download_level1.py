from ARDCube.config import FORCE_PATH
from ARDCube.read_settings import get_settings
from ARDCube.auxiliary.aux import get_aoi_path, check_sat_settings

import os
import logging
from datetime import datetime
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from spython.main import Client


def download_level1(log_sentinelsat=False, debug_force=False):
    """Main download script."""

    ## Get user defined settings
    settings = get_settings()

    ## Check which satellite sensors were selected (= True) in the settings.prm file and create dictionary with
    ## a few useful values (abbreviation used in FORCE, directory to store downloaded scenes, ...)
    sats = check_sat_settings(settings=settings)

    ## Start download functions
    ## Both functions print query information first and then ask for confirmation to start the download.
    for sat in list(sats.keys()):
        print(f"#### \nStarting download script for {sat}...")

        if sat == 'Sentinel1':
            download_sar(settings=settings,
                         out_dir=sats[sat]['level1_dir'],
                         log_sentinelsat=log_sentinelsat)
        else:
            download_optical(settings=settings,
                             out_dir=sats[sat]['level1_dir'],
                             force_abbr=sats[sat]['force_abbr'],
                             debug_force=debug_force)


def download_sar(settings, out_dir, log_sentinelsat=False):
    """Download Sentinel-1 GRD data from Copernicus Open Access Hub based on parameters defined in 'settings.prm'.
    https://github.com/sentinelsat/sentinelsat
    """
    ## TODO: Include SAROrbitDirection to query only ascending/descending scenes

    ## Optionally store sentinelsat logging information in '/DataDirectory/log'
    ## https://sentinelsat.readthedocs.io/en/stable/api.html#logging
    if log_sentinelsat:
        filename = os.path.join(settings['GENERAL']['DataDirectory'], 'log',
                                f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S__download_s1')}.log")
        logging.basicConfig(filename=filename, filemode='w', format='%(message)s', level='INFO')

    ## Get footprint from AOI
    aoi_path = get_aoi_path(settings)
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

    ## Before starting the download, ask for user confirmation. (and print out query information)
    while True:
        answer = input(f"{len(query)} Sentinel-1 GRD files were found between {timespan[0]} and {timespan[1]} \n"
                       f"for the AOI defined by '{aoi_path}'. \n"
                       f"The total file size is {api.get_products_size(query)} GB \n"
                       f"Do you want to proceed with the download? (y/n)")

        if answer in ['y', 'yes']:
            api.download_all(query, directory_path=out_dir)
            break

        elif answer in ['n', 'no']:
            break

        else:
            print(f"---------- \n{answer} is not a valid answer! \n----------")
            continue


def download_optical(settings, out_dir, force_abbr, debug_force=False):
    """Download optical satellite data from Google Cloud Storage based on parameters defined in 'settings.prm'.
    https://force-eo.readthedocs.io/en/latest/howto/level1-csd.html#tut-l1csd
    """

    ## TODO: Check if metadata catalogues exist and if not download them first!

    ## Collect all information that will be used in the query
    sensors = force_abbr
    daterange = f"{settings['DOWNLOAD']['TimespanMin']}," \
                f"{settings['DOWNLOAD']['TimespanMax']}"
    cloudcover = f"{settings['DOWNLOAD']['OpticalCloudCoverRangeMin']}," \
                 f"{settings['DOWNLOAD']['OpticalCloudCoverRangeMax']}"
    meta_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'meta/force')
    aoi_path = get_aoi_path(settings)

    ## Send query to FORCE Singularity container as dry run first ("--no-act") and print output
    Client.debug = debug_force
    output = Client.execute(FORCE_PATH, ["force-level1-csd", "--no-act", "-s", sensors, "-d", daterange,
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
        answer = input(f"Do you want to proceed with the download? (y/n)")

        if answer in ['y', 'yes']:

            print("\n#### \nStarting download... \n"
                  "Depending on the dataset size and your internet speed, this might take a while. \n"
                  "Unfortunately there's currently no good solution to show the download progress. \n"
                  "If the download takes longer than you intended, you can just cancel the process \n"
                  "and start it again at a later time using the same settings in the settings.prm file. \n"
                  "FORCE automatically checks for existing scenes and will only download new scenes!")

            Client.execute(FORCE_PATH, ["force-level1-csd", "-s", sensors, "-d", daterange,
                                        "-c", cloudcover, meta_dir, out_dir, "queue.txt", aoi_path],
                           options=["--cleanenv"])

            break

        elif answer in ['n', 'no']:
            print("\n#### \nDownload cancelled...")
            break

        else:
            print(f"---------- \n{answer} is not a valid answer! \n----------")
            continue
