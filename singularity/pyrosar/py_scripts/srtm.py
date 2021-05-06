import sys
import os
from pyroSAR.auxdata import dem_autoload, dem_create
from spatialist import Vector

aoi_path = sys.argv[1]
out_file = sys.argv[2]

vrt = f"{os.path.splitext(out_file)[0]}.vrt"

with Vector(aoi_path) as vec:
    dem_autoload(geometries=[vec], demType='SRTM 1Sec HGT',
                 vrt=vrt, buffer=0.02)

dem_create(src=vrt, dst=out_file,
           t_srs=4326,
           resampling_method='bilinear',
           geoid_convert=True, geoid='EGM96')

os.remove(vrt)
