from pathlib import Path
import subprocess
import os
import re

s1_dir = Path("/home/du23yow/Documents/MA/test_data/S1/")

## ---------------------------------------------------------------------------------------------------------------------

## Create list of all .tif files
tif_list = [os.path.join(s1_dir, f) for f in os.listdir(s1_dir) if
            re.search(r'.*\.tif', f)]

for file in tif_list:

    ## Define new filename
    basename = os.path.basename(file)
    basename_new = f"{basename[:-len(Path(basename).suffix)]}_25832.tif"

    ## Search and extract date from filename
    rs = re.search(r'\d{8}T', file)
    date = file[rs.regs[0][0]:rs.regs[0][1]-1]

    ## Define new directory (and create it, if it doesn't exist already)
    dir_new = os.path.join(s1_dir, date)
    if not os.path.exists(dir_new):
        os.makedirs(dir_new)

    ## Complete output path
    file_out = os.path.join(dir_new, basename_new)

    ## Execute gdalwarp
    subprocess.call(f'gdalwarp -t_srs EPSG:25832 -co TILED=YES -co BLOCKXSIZE=512 -co BLOCKYSIZE=512 '
                    f'{file} {file_out}', shell=True)
