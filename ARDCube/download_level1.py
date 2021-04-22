from ARDCube.config import FORCE_PATH, SAT_DICT
import ARDCube.utils as utils
import ARDCube.utils_force as force

import os
import logging
import json
from datetime import datetime
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt, SentinelAPIError
from spython.main import Client
import geopandas as gpd


def download_level1(sensor, debug_force=False):
    """Main download script."""

    ## Get settings from 'settings.prm'
    settings = utils.get_settings()

    ## Check if sensor is supported.
    if sensor not in list(SAT_DICT.keys()):
        raise ValueError(f"{sensor} is not supported!")

    ## Collect query information
    query = _collect_query(settings=settings,
                                sensor=sensor)

    print(f"#### Start download query for {sensor}...")
    if sensor == 'sentinel1':
        download_sar(query=query)
    else:
        download_optical(query=query,
                         debug_force=debug_force)


def download_sar(query):
    """Download Sentinel-1 GRD data from Copernicus Open Access Hub based on parameters defined in 'settings.prm'.
    https://github.com/sentinelsat/sentinelsat
    """

    _sentinelsat_logging(query['log_dir'])

    api = SentinelAPI(user=query['username'],
                      password=query['password'],
                      api_url="https://scihub.copernicus.eu/apihub")

    try:
        api_query = api.query(area=query['footprint'],
                              date=query['timespan'],
                              platformname='Sentinel-1',
                              producttype='GRD',
                              orbitdirection=query['direction'])
    except SentinelAPIError:
        footprint = _sentinelsat_footprint(aoi_path=query['aoi_path'], simplify=True)
        api_query = api.query(area=footprint,
                              date=query['timespan'],
                              platformname='Sentinel-1',
                              producttype='GRD',
                              orbitdirection=query['direction'])

    while True:
        answer = input(f"\n{len(query)} Sentinel-1 GRD scenes were found using the following query parameters:\n"
                       f"- Timespan: {query['timespan'][0]} - {query['timespan'][1]} \n"
                       f"- Orbit direction(s): {query['direction']} \n"
                       f"- AOI file: {query['aoi_path']} \n"
                       f"\nTotal file size: {api.get_products_size(api_query)} GB \n"
                       f"Output directory: {query['out_dir']} \n"
                       f"Do you want to proceed with the download? (y/n)")
        if answer in ['y', 'yes']:
            print("\n#### Starting download...")
            try:
                api.download_all(api_query, directory_path=query['out_dir'])
            except Exception as e:
                print(f"Download was cancelled because of exception: {e}\n"
                      f"Please check log file for more information!\n"
                      f"Log file is located at: {query['log_dir']}")
            break
        elif answer in ['n', 'no']:
            print("\n#### Download cancelled...")
            break
        else:
            print(f"\n{answer} is not a valid answer!")
            continue


def download_optical(query, debug_force):
    """Download optical satellite data from Google Cloud Storage based on parameters defined in 'settings.prm'.
    https://force-eo.readthedocs.io/en/latest/howto/level1-csd.html#tut-l1csd
    """

    Client.debug = debug_force
    if debug_force:
        quiet = False
    else:
        quiet = True

    meta_dir = query['meta_dir']
    if not os.path.exists(meta_dir) or len(os.listdir(meta_dir)) == 0:
        force.download_catalogues(meta_dir)

    timespan = f"{query['timespan'][0]},{query['timespan'][1]}"

    ## Send query to FORCE Singularity container as dry run first ("--no-act") and print output
    output = Client.execute(FORCE_PATH, ["force-level1-csd", "--no-act", "-s", query['force_abbr'], "-d", timespan,
                                         "-c", query['cloudcover'], meta_dir, query['out_dir'],
                                         query['queue_file'], query['aoi_path']],
                            options=["--cleanenv"])

    if isinstance(output, list):
        for line in output:
            print(line)
    else:
        print(output)

    ## Before starting the download, ask for user confirmation.
    while True:
        answer = input(f"Output directory: {query['out_dir']} \n"
                       f"Do you want to proceed with the download? (y/n)")

        if answer in ['y', 'yes']:
            print("\n#### Starting download... \n"
                  "If the download takes longer than you intended, you can just cancel the process \n"
                  "and start it again at a later time using the same settings. \n"
                  "Only incomplete and new scenes will be downloaded!\n")

            out = Client.execute(FORCE_PATH, ["force-level1-csd", "-s", query['force_abbr'], "-d", timespan,
                                              "-c", query['cloudcover'], meta_dir, query['out_dir'],
                                              query['queue_file'], query['aoi_path']],
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


def _collect_query(settings, sensor):

    out_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level1', sensor)
    utils.isdir_mkdir(out_dir)
    data_dir = settings['GENERAL']['DataDirectory']
    aoi_path = utils.get_aoi_path(settings)

    query = {'out_dir': out_dir,
             'aoi_path': aoi_path,
             'timespan': (settings['DOWNLOAD']['TimespanMin'],
                          settings['DOWNLOAD']['TimespanMax'])}

    if sensor == 'sentinel1':
        query['direction'] = _sentinelsat_orbitdir(settings)
        query['footprint'] = _sentinelsat_footprint(aoi_path)
        query['username'] = settings['DOWNLOAD']['CopernicusUser']
        query['password'] = settings['DOWNLOAD']['CopernicusPassword']
        query['log_dir'] = os.path.join(data_dir, 'log')
    else:
        query['force_abbr'] = SAT_DICT[sensor]
        query['cloudcover'] = f"{settings['DOWNLOAD']['OpticalCloudCoverRangeMin']}," \
                              f"{settings['DOWNLOAD']['OpticalCloudCoverRangeMax']}"
        query['queue_file'] = os.path.join(out_dir, 'queue.txt')
        query['meta_dir'] = os.path.join(data_dir, 'meta/catalogues')

    return query


def _sentinelsat_logging(directory):
    """https://sentinelsat.readthedocs.io/en/stable/api.html#logging"""

    utils.isdir_mkdir(directory)
    log_file = os.path.join(directory, f"{datetime.now().strftime('%Y%m%dT%H%M%S__sentinel1__download_level1')}.log")
    logging.basicConfig(filename=log_file, filemode='w', format='%(message)s', level='INFO')


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
        raise ValueError(f"{field} not recognized. Valid options are 'asc', 'desc' or 'both'!")


def _sentinelsat_footprint(aoi_path, simplify=False):
    """..."""

    ## Read AOI file, convert to WGS84 (required by sentinelsat) and convert to json string
    ## Also simplify the polygon if option set to True
    if simplify:
        json_str = gpd.read_file(aoi_path).to_crs(4326).convex_hull.to_json()
    else:
        json_str = gpd.read_file(aoi_path).to_crs(4326).to_json()

    ## Convert json str to dict and then WKT... ¯\_(ツ)_/¯
    json_obj = json.loads(json_str)
    footprint = geojson_to_wkt(json_obj)

    return footprint
