from pathlib import Path
import subprocess
import os
import re
import uuid
import yaml
import rasterio


s1_dir = Path("/home/du23yow/Documents/MA/test_data/S1/")
product_name = 's1_test_product'
crs = '25832'

## ---------------------------------------------------------------------------------------------------------------------


def create_file_list(file_dir):

    return [os.path.join(file_dir, f) for f in os.listdir(file_dir) if
            re.search(r'.*\.tif', f)]


def create_file_dict(file_list):

    dict_out = {}
    for file in file_list:

        file_base = os.path.basename(file)

        ## Extract entire date string from filename (needed to identify related files (VV/VH)!)
        rs = re.search(r'_\d{8}T\d{6}_', file_base)
        date = file_base[rs.regs[0][0]+1:rs.regs[0][1]-1]

        dict_keys = list(dict_out.keys())
        if date not in dict_keys:
            dict_out[date] = [file]
        else:
            dict_out[date].append(file)

    for key in dict_out:
        if len(dict_out[key]) > 2:
            raise ValueError(f'For each dictionary key a list of two entries (VV & VH) is expected. '
                             f'The key \'{key}\' contains a list of {len(dict_out[key])} entries. Please check!')

    return dict_out


def s1_convert(file_list):

    for file in file_list:

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


def get_vv_vh_file(file_dict_entry):
    """
    Using regex here instead of the index of file_dict_entry to avoid wrong variable bindings!
    """

    r_vh = re.compile('.*_VH_')
    r_vv = re.compile('.*_VV_')

    vh = list(filter(r_vh.match, file_dict_entry))[0]
    vv = list(filter(r_vv.match, file_dict_entry))[0]

    return vh, vv


def get_grid_info(file_dict_entry):

    src1 = rasterio.open(file_dict_entry[0])
    src2 = rasterio.open(file_dict_entry[1])

    shape1 = src1.shape
    shape2 = src2.shape
    transform1 = list(src1.transform)
    transform2 = list(src2.transform)

    if shape1 == shape2 and transform1 == transform2:
        return shape1, transform1
    else:
        raise ValueError(f"Shape and transform information of {os.path.basename(file_dict_entry[0])} and "
                         f"{os.path.basename(file_dict_entry[1])} were expected to be identical!")


def get_metadata(file_dict_entry):
    """
    Extracting metadata that is common to both files in the dictionary entry, so extraction based on only one of the
    files should be okay.

    ODC currently uses the EO3 format for the YAML files, which is supposed to be an intermediate format before moving
    on to STAC. The 'properties' section in the YAML, which is filled with the dictionary created in this function,
    already uses STAC standard names. For more information see:
    https://github.com/radiantearth/stac-spec/blob/master/item-spec/common-metadata.md
    https://github.com/radiantearth/stac-spec/tree/master/extensions/sar (other extensions in parent directory!)
    """

    dict_out = {}
    filename = os.path.basename(file_dict_entry[0])

    dict_out['eo:platform'] = f'Sentinel-1{filename[2:3]}'
    dict_out['eo:instrument'] = 'c-sar'

    date = filename[12:27]
    date_new = f'{date[0:4]}-{date[4:6]}-{date[6:8]}T' \
               f'{date[9:11]}:{date[11:13]}:{date[13:]}.000Z'  # ...there's probably a more elegant way?
    dict_out['datetime'] = f'datetime:{date_new}'

    dict_out['odc:file_format'] = 'GeoTIFF'

    dict_out['sar:instrument_mode'] = filename[5:7]
    dict_out['sar:frequency_band'] = 'C'
    dict_out['sar:polarizations'] = ['VH', 'VV']
    dict_out['sar:product_type'] = 'GRD'

    if filename[10:11] == 'A':
        dict_out['sat:orbit_state'] = 'ascending'
    elif filename[10:11] == 'D':
        dict_out['sat:orbit_state'] = 'descending'
    else:
        dict_out['sat:orbit_state'] = None
        print(f'Based on the naming convention of pyroSAR, either the character \'A\' (ascending) or \'D\' (descending)'
              f' was expected for index [10:11]. The actual character is {filename[10:11]}. '
              f'\'sat:orbit_state\' will be set to \'None\'. Please check file naming of the current dataset!')

    ## Any other metadata that would be useful to search for?
    ## Check pyroSAR naming convention somehow before or after? Or not?

    return dict_out


def create_eo3_yaml(file_dict_entry, product_name, crs):
    """
    file_dict_entry -> ["full_path_to_vv_file", "full_path_to_vh_file"]
    """

    path_vh, path_vv = get_vv_vh_file(file_dict_entry)
    shape, transform = get_grid_info(file_dict_entry)
    meta = get_metadata(file_dict_entry)

    yaml_content = {
        'id': str(uuid.uuid4()),
        '$schema': 'https://schemas.opendatacube.org/dataset',
        'product': {'name': product_name},
        'crs': crs,
        'grids': {'default': {'shape': shape, 'transform': transform}
                  },
        'measurements': {'VH': {'path': path_vh},
                         'VV': {'path': path_vv}
                         },
        'properties': meta
    }

    yaml_dir = os.path.dirname(file_dict_entry[0])
    yaml_name = f'{os.path.basename(file_dict_entry[0])[:27]}.yaml'

    with open(os.path.join(yaml_dir, yaml_name), 'w') as stream:
        yaml.dump(yaml_content, stream, sort_keys=False)


def main(file_dir, product_name, crs):

    ## Create list & dict from files in the directory
    file_list = create_file_list(file_dir)
    file_dict = create_file_dict(file_list)

    ## Convert all files that are listed in file_list
    s1_convert(file_list)

    ## Create metadata YAMLs in EO3 format
    for key in list(file_dict.keys()):
        create_eo3_yaml(file_dict[key], product_name, crs)

    ## Anything else??


#############
## TEST AREA

test_file1 = "/home/du23yow/Documents/MA/test_data/S1/20200602/S1A__IW___A_20200602T170001_VH_grd_mli_norm_geo_db_25832.tif"
test_file2 = "/home/du23yow/Documents/MA/test_data/S1/20200602/S1A__IW___A_20200602T170001_VV_grd_mli_norm_geo_db_25832.tif"
