from pathlib import Path
import subprocess
import os
import re
import glob
import nasa_hls

hls_dir = Path("/home/du23yow/Documents/MA/test_data/HLS/S30")
max_cloud = 100

## ---------------------------------------------------------------------------------------------------------------------

## Create list of all .hdf files
hdf_list = [os.path.join(hls_dir, f) for f in os.listdir(hls_dir) if
            re.search(r'.*\.hdf$', f)]

## Convert to GeoTIFF format
for file in hdf_list:
    nasa_hls.convert_hdf2tiffs(Path(f"{file}"),
                               hls_dir,
                               max_cloud_coverage=max_cloud
                               )
    ## Clean up
    #os.remove(file)
    #os.remove(f'{file}.hdr')

## Use gdalwarp to reproject each .tif file and create internal tiles
for file in glob.iglob(os.path.join(hls_dir, '**/*.tif'), recursive=True):

    ## Define new filename
    basename = os.path.basename(file)
    basename_tmp = basename[:-len(Path(basename).suffix)]
    basename_new = f"{basename_tmp}_25832.tif"

    ## Define new directory (and create it, if it doesn't exist already)
    tile = basename[9:14]  # Neither HLS nor Sentinel naming conventions will change any time soon, ...
    date = basename[15:22]  # ...so I guess this is reasonably safe
    dir_new = os.path.join(hls_dir, tile, date)
    if not os.path.exists(dir_new):
        os.makedirs(dir_new)

    ## Complete output path
    file_out = os.path.join(dir_new, basename_new)

    ## Execute gdalwarp
    subprocess.call(f'gdalwarp -t_srs EPSG:25832 -co TILED=YES -co BLOCKXSIZE=512 -co BLOCKYSIZE=512 '
                    f'{file} {file_out}', shell=True)

    ## Clean up
    os.remove(file)

## Clean up (remove empty subdirectories)
for root, dirs, files in os.walk(hls_dir):
    if not len(dirs) and not len(files):
        os.rmdir(root)
