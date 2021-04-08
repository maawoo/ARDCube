from ARDCube.config import FORCE_PATH, SAT_DICT
import ARDCube.utils as utils
from ARDCube.utils_force import download_catalogues

import os
import logging
from datetime import datetime
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from spython.main import Client
import geopandas as gpd


def download_level1(sensor, debug_force=False):
    """Main download script."""

    ## Check if sensor is supported.
    if sensor not in list(SAT_DICT.keys()):
        raise ValueError(f"{sensor} is not supported!")

    ## Get user defined settings
    settings = utils.get_settings()

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

    ## Set logging
    _sentinelsat_logging(settings)

    ## Create directory if it doesn't exist yet
    out_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level1', 'sentinel1')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    ## Get footprint/AOI path, timespan & orbit direction(s)
    footprint, aoi_path = _sentinelsat_footprint(settings)
    timespan = (settings['DOWNLOAD']['TimespanMin'],
                settings['DOWNLOAD']['TimespanMax'])
    direction = _sentinelsat_orbitdir(settings)

    ## Connect to Copernicus Open Access Hub using provided credentials.
    ## The API defaults to https://scihub.copernicus.eu/apihub
    api = SentinelAPI(settings['DOWNLOAD']['CopernicusUser'],
                      settings['DOWNLOAD']['CopernicusPassword'])

    ## Perform a query using provided parameters
    query = api.query(area=footprint,
                      date=timespan,
                      platformname='Sentinel-1',
                      producttype='GRD',
                      orbitdirection=direction)

    ## Before starting the download, print out query information and then ask for user confirmation.
    while True:
        answer = input(f"\n{len(query)} Sentinel-1 GRD scenes were found using the following query parameters:"
                       f"- Timespan: {timespan[0]} - {timespan[1]} \n"
                       f"- Orbit direction(s): {direction} \n"
                       f"- AOI file: {aoi_path} \n"
                       f"\nTotal file size: {api.get_products_size(query)} GB \n"
                       f"Output directory: {out_dir} \n"
                       f"Do you want to proceed with the download? (y/n)")

        if answer in ['y', 'yes']:
            print("\n#### Starting download...")
            api.download_all(query,
                             directory_path=out_dir)
            break

        elif answer in ['n', 'no']:
            print("\n#### Download cancelled...")
            break

        else:
            print(f"\n{answer} is not a valid answer!")
            continue


def download_optical(settings, sensor, debug_force):
    """Download optical satellite data from Google Cloud Storage based on parameters defined in 'settings.prm'.
    https://force-eo.readthedocs.io/en/latest/howto/level1-csd.html#tut-l1csd
    """

    Client.debug = debug_force
    if debug_force:
        quiet = False
    else:
        quiet = True

    ## Collect all information that will be used in the query
    force_abbr = SAT_DICT[sensor]
    daterange = f"{settings['DOWNLOAD']['TimespanMin']}," \
                f"{settings['DOWNLOAD']['TimespanMax']}"
    cloudcover = f"{settings['DOWNLOAD']['OpticalCloudCoverRangeMin']}," \
                 f"{settings['DOWNLOAD']['OpticalCloudCoverRangeMax']}"

    meta_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'meta/catalogues')
    if not os.path.exists(meta_dir) or len(os.listdir(meta_dir)) == 0:
        download_catalogues(meta_dir)

    out_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level1', sensor)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    queue_file = os.path.join(out_dir, 'queue.txt')
    aoi_path = utils.get_aoi_path(settings)

    ## Send query to FORCE Singularity container as dry run first ("--no-act") and print output
    output = Client.execute(FORCE_PATH, ["force-level1-csd", "--no-act", "-s", force_abbr, "-d", daterange,
                                         "-c", cloudcover, meta_dir, out_dir, queue_file, aoi_path],
                            options=["--cleanenv"])

    if isinstance(output, list):
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
            print("\n#### Starting download... \n"
                  "If the download takes longer than you intended, you can just cancel the process \n"
                  "and start it again at a later time using the same settings. \n"
                  "Only incomplete and new scenes will be downloaded!\n")

            out = Client.execute(FORCE_PATH, ["force-level1-csd", "-s", force_abbr, "-d", daterange,
                                              "-c", cloudcover, meta_dir, out_dir, queue_file, aoi_path],
                                 options=["--cleanenv"], quiet=quiet, stream=True)
            for line in out:
                print(line, end='')
            break

        elif answer in ['n', 'no']:
            print("\n#### Download cancelled...")
            break
        else:
            print(f"\n{answer} is not a valid answer!")
            continue


def _sentinelsat_logging(settings):
    """..."""

    ## Create logfile for sentinelsat output by default
    ## https://sentinelsat.readthedocs.io/en/stable/api.html#logging
    log_file = os.path.join(settings['GENERAL']['DataDirectory'], 'log',
                            f"{datetime.now().strftime('%Y%m%dT%H%M%S__download_sentinel1')}.log")

    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))

    logging.basicConfig(filename=log_file, filemode='w', format='%(message)s', level='INFO')


def _sentinelsat_footprint(settings):
    """..."""

    aoi_path = utils.get_aoi_path(settings)
    if aoi_path.endswith(".gpkg"):
        aoi_path = _gpkg_to_geojson(aoi_path)

    footprint = geojson_to_wkt(read_geojson(aoi_path))

    return footprint, aoi_path


def _sentinelsat_orbitdir(settings):
    """..."""

    field = settings['DOWNLOAD']['SAROrbitDirection']
    if field == 'both':
        return ['ASCENDING', 'DESCENDING']
    elif field in ['desc', 'descending']:
        return 'DESCENDING'
    elif field in ['asc', 'ascending']:
        return 'ASCENDING'
    else:
        raise ValueError(f"{field} not recognized. Valid options are 'ascending', 'descending' or 'both'!")


def _gpkg_to_geojson(gpkg_path):
    """..."""

    out_name = os.path.join(os.path.dirname(gpkg_path),
                            f"{os.path.splitext(os.path.basename(gpkg_path))[0]}_4326.geojson")

    if os.path.isfile(out_name):
        pass
    else:
        src = gpd.read_file(gpkg_path)
        gpkg_4326 = src.to_crs(4326)
        gpkg_4326.to_file(out_name, driver="GeoJSON")

    return out_name
