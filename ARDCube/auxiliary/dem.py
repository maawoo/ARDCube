## https://pyrosar.readthedocs.io/en/latest/general/DEM.html

from pyroSAR.auxdata import dem_autoload, dem_create
from spatialist import Vector

aoi = '/home/marco/pypypy/ARDCube_data/misc/aoi/th_stripe.geojson'
vrt = '/home/marco/pypypy/ARDCube_data/misc/dem/test/srtm.vrt'

with Vector(aoi) as vec:
    dem_autoload(geometries=[vec], demType='SRTM 1Sec HGT',
                 vrt=vrt, buffer=0.02)


outname = '/home/marco/pypypy/ARDCube_data/misc/dem/test/srtm.tif'

dem_create(src=vrt, dst=outname,
           t_srs=4326,
           resampling_method='bilinear',
           geoid_convert=True, geoid='EGM96')
