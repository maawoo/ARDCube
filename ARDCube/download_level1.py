from ARDCube.read_settings import get_settings

import os
import logging
from datetime import datetime
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from spython.main import Client


def download_s1(log=False):
    """Download Sentinel-1 GRD data from Copernicus Open Access Hub based on parameters defined in 'settings.prm'.
    Incomplete downloads are continued and complete files are skipped.
    """

    ## Get user defined settings
    settings = get_settings()

    ## Define output directory
    main_dir = settings.get('GENERAL', 'DataDirectory')
    s1_dir = os.path.join(main_dir, 'level-1/S1')
    if not os.path.exists(s1_dir):
        os.makedirs(s1_dir)

    ## https://sentinelsat.readthedocs.io/en/stable/api.html#logging
    if log:
        filename = os.path.join(main_dir, 'log', f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S__download_s1')}.log")
        logging.basicConfig(filename=filename, filemode='w', format='%(message)s', level='INFO')

    ## Get footprint from AOI
    if os.path.isdir(settings.get('GENERAL', 'AOI')):  # Returns True if a path was provided
        aoi_path = settings.get('GENERAL', 'AOI')
        footprint = geojson_to_wkt(read_geojson(aoi_path))
    else:
        aoi_path = os.path.join(main_dir, 'misc/aoi', settings.get('GENERAL', 'AOI'))
        footprint = geojson_to_wkt(read_geojson(aoi_path))

    ## Get timespan
    timespan = (settings.get('GENERAL', 'TimespanMin'),
                settings.get('GENERAL', 'TimespanMax'))

    ## Connect to Copernicus Open Access Hub using provided credentials.
    ## The API defaults to https://scihub.copernicus.eu/apihub
    api = SentinelAPI(settings.get('GENERAL', 'CopernicusUser'),
                      settings.get('GENERAL', 'CopernicusPassword'))

    ## Perform a query using provided parameters
    query = api.query(footprint,
                      date=timespan,
                      platformname='Sentinel-1',
                      producttype='GRD')

    print(f"{len(query)} scenes // {api.get_products_size(query)} GB total file size")

    api.download_all(query, directory_path=s1_dir)  # Download all queried products (s1)


#def force_download():
#    """
#    force-level1-csd -s sensors -d daterange -c cloudcover metadata_dir level-1_dir queue.txt aoi-file
#    :return:
#    """

#    force_c = Client.instance(os.path.join(maindir, 'singularity/force', 'force.sif'), name='force_c')
