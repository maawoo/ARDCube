import sys
import os
from pyroSAR.auxdata import dem_autoload, dem_create
from spatialist import Vector

aoi_path = sys.argv[1]
out_file = sys.argv[2]
dem_type = sys.argv[3]

vrt = f"{os.path.splitext(out_file)[0]}.vrt"

with Vector(aoi_path) as vec:
    dem_autoload(geometries=[vec], demType=dem_type,
                 vrt=vrt, buffer=0.02, username=None, password=None, product='dem')

dem_create(src=vrt, dst=out_file,
           t_srs=4326, tr=None,
           resampling_method='bilinear',
           geoid_convert=True, geoid='EGM96')

os.remove(vrt)
