import sys
import os
import glob
from pyroSAR import snap

in_dir = sys.argv[1]
out_dir = sys.argv[2]
aoi_path = sys.argv[3]
dem_path = sys.argv[4]

snap_gpt = '/opt/snap/bin/gpt'

list_scenes = []
for file in glob.iglob(os.path.join(in_dir, 'S1*zip'), recursive=True):
    list_scenes.append(file)

print(f"Number of scenes found: {len(list_scenes)}")

for scene in list_scenes:
    print(os.path.basename(scene))

    ## All parameters (except the ones that are filled by variables obviously) are left as default based on the
    ## pyroSAR v0.12 docs: https://pyrosar.readthedocs.io/en/v0.12/pyroSAR.html#module-pyroSAR.snap.util
    snap.geocode(infile=scene, outdir=out_dir, t_srs=4326, tr=20, polarizations='all', shapefile=aoi_path,
                 scaling='dB', geocoding_type='Range-Doppler', removeS1BorderNoise=True,
                 removeS1BorderNoiseMethod='pyroSAR', removeS1ThermalNoise=True, offset=None, allow_RES_OSV=False,
                 externalDEMFile=dem_path, externalDEMNoDataValue=None, externalDEMApplyEGM=True,
                 terrainFlattening=True, basename_extensions=None, test=False, export_extra=None, groupsize=1,
                 cleanup=True, tmpdir=None, gpt_exceptions=None, gpt_args=None, returnWF=False, nodataValueAtSea=True,
                 demResamplingMethod='BILINEAR_INTERPOLATION', imgResamplingMethod='BILINEAR_INTERPOLATION',
                 alignToStandardGrid=False, standardGridOriginX=0, standardGridOriginY=0,
                 speckleFilter=False, refarea='gamma0')

    print('-' * 10)
