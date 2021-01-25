import os
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
from datetime import date
import geojson
import logging

logging.basicConfig(filename='test.log', filemode='a', format='%(message)s', level='INFO')
# logging.basicConfig(format='%(message)s', level='INFO')

maindir = '/home/marco/pypypy/00_data/pyro_test'
s1_dir = os.path.join(maindir, 'S1')
aoi = os.path.join(maindir, 'misc', 'jena.geojson')

api = SentinelAPI('maawoo', '2ZSuBPsU8YQkzUsDz6c3pS8nMn', 'https://scihub.copernicus.eu/apihub/')
footprint = geojson_to_wkt(read_geojson(aoi))
products = api.query(footprint,
                     date=('20200601', '20200701'),
                     platformname='Sentinel-1',
                     producttype='GRD')

print(f"Total size of queried products: {api.get_products_size(products)} GB")

# api.download(id=list(products.keys())[0])  # Download single product based on index
api.download_all(products, directory_path=s1_dir)  # Download all queried products

"""
## Export footprints and metadata of queried products as GeoJSON

all_path = os.path.join(maindir, 'misc', 'test.geojson')
all_geojson = api.to_geojson(products)
with open(all_path, 'w') as f:
    geojson.dump(all_geojson, f)
"""
