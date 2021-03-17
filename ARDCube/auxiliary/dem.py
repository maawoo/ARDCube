import sys
import os
from pyroSAR.auxdata import dem_autoload, dem_create
from spatialist import Vector

aoi_path = sys.argv[1]
out_dir = sys.argv[2]

vrt = os.path.join(out_dir, 'srtm.vrt')
tif = os.path.join(out_dir, 'srtm.tif')

with Vector(aoi_path) as vec:
    dem_autoload(geometries=[vec], demType='SRTM 1Sec HGT',
                 vrt=vrt, buffer=0.02)

dem_create(src=vrt, dst=tif,
           t_srs=4326,
           resampling_method='bilinear',
           geoid_convert=True, geoid='EGM96')
