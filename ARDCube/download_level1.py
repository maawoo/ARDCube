from ARDCube import read_settings

import os
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from spython.main import Client
from datetime import date
import geojson
import logging

logging.basicConfig(filename='sentinelsat.log', filemode='a', format='%(message)s', level='INFO')  # save to file
logging.basicConfig(format='%(message)s', level='INFO')  # print in console
settings = read_settings.get_settings('GENERAL')

####################

maindir = '/home/marco/pypypy/pyro_test'
s1_dir = os.path.join(maindir, 'S1')

####################

aoi = settings['']
aoi = os.path.join(maindir, 'misc', 'th_stripe.geojson')
timespan = ('20200601', '20200604')
s1_producttype = 'GRD'

#############################################################

api = SentinelAPI('maawoo', '2ZSuBPsU8YQkzUsDz6c3pS8nMn', 'https://scihub.copernicus.eu/apihub/')
footprint = geojson_to_wkt(read_geojson(aoi))

products_s1 = api.query(footprint, date=timespan, platformname='Sentinel-1', producttype=s1_producttype)
products_s2 = api.query(footprint, date=timespan, platformname='Sentinel-2', producttype=s2_producttype,  cloudcoverpercentage=s2_cloudcover)
print(f"Sentinel-1: {len(products_s1)} scenes // {api.get_products_size(products_s1)} GB total file size \n"
      f"Sentinel-2: {len(products_s2)} scenes // {api.get_products_size(products_s2)} GB total file size")

# api.download(id=list(products.keys())[0])  # Download single product based on index
api.download_all(products_s1, directory_path=s1_dir)  # Download all queried products (s1)
# api.download_all(products_s2, directory_path=s2_dir)  # Download all queried products (s2)


"""
## Export footprints and metadata of queried products as GeoJSON

all_path = os.path.join(maindir, 'misc', 'test.geojson')
all_geojson = api.to_geojson(products)
with open(all_path, 'w') as f:
    geojson.dump(all_geojson, f)
"""

def force_download(settings):
    """
    force-level1-csd -s sensors -d daterange -c cloudcover metadata_dir level-1_dir queue.txt aoi-file
    :return:
    """

    force_c = Client.instance(os.path.join(maindir, 'singularity/force', 'force.sif'), name='force_c')
