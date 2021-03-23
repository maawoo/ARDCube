import os
from pyroSAR import snap
from spatialist.ancillary import finder

maindir = '/home/marco/pypypy/00_data/pyro_test'
outdir = os.path.join(maindir, 'out_2')
snap_gpt = '/opt/snap/bin/gpt'
shape = os.path.join(maindir, 'misc', 'th_stripe.geojson')  # TH_shape_25832.gpkg
dem_lidar = os.path.join(maindir, 'dem', 'TH_LidarDEM_10m.tif')  # 10m
dem_srtm = os.path.join(maindir, 'dem', 'TH_SRTM_30m.tif')  # 30m
epsg = 25832

scenes = finder(os.path.join(maindir, 'S1'), ['S1*zip'])
print(f"Number of scenes found: {len(scenes)} ")

for scene in scenes:
    print(os.path.basename(scene))

    snap.geocode(infile=scene, outdir=outdir, t_srs=epsg, tr=20,
                 shapefile=None, scaling='db', allow_RES_OSV=True,
                 externalDEMFile=dem_srtm, externalDEMApplyEGM=False, groupsize=1,
                 export_extra=None, test=False
                 )
    print('-' * 10)


