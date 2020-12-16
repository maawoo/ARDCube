from pathlib import Path
import os
import re
import glob
import uuid
from progress.bar import Bar
import yaml
import rasterio
from osgeo import gdal

s1_dir = Path("/home/du23yow/MA/S1_Test")
product_name = 's1_test_product_terrasense'
crs = '25832'
cleanup = True

## ---------------------------------------------------------------------------------------------------------------------


def s1_convert(file_dir):

    file_list = [os.path.join(file_dir, f) for f in os.listdir(file_dir) if
                 re.search(r'.*\.tif', f)]

    bar = Bar('Processing', max=len(file_list))
    for f in file_list:

        ## Define new filename
        basename = os.path.basename(f)
        basename_new = f"{basename[:-len(Path(basename).suffix)]}_25832.tif"

        ## Search and extract date from filename
        rs = re.search(r'\d{8}T', f)
        date = f[rs.regs[0][0]:rs.regs[0][1]-1]

        ## Define new directory (and create it, if it doesn't exist already)
        dir_new = os.path.join(s1_dir, date)
        if not os.path.exists(dir_new):
            os.makedirs(dir_new)

        ## Complete output path
        f_out = os.path.join(dir_new, basename_new)

        ## Execute gdalwarp
        warp_options = gdal.WarpOptions(dstSRS='EPSG:25832', options='-co TILED=YES -co BLOCKXSIZE=512 '
                                                                     '-co BLOCKYSIZE=512')
        ds = gdal.Warp(f_out, f, options=warp_options)
        ds = None

        if cleanup:
            ## Remove original file
            os.remove(f)

        bar.next()
    bar.finish()


def create_file_dict(file_dir):

    dict_out = {}
    for f in glob.iglob(os.path.join(file_dir, '**/*.tif'), recursive=True):

        f_base = os.path.basename(f)

        ## Extract entire date string from filename (needed to identify related files (VV/VH)!)
        rs = re.search(r'_\d{8}T\d{6}_', f_base)
        date = f_base[rs.regs[0][0]+1:rs.regs[0][1]-1]

        dict_keys = list(dict_out.keys())
        if date not in dict_keys:
            dict_out[date] = [f]
        else:
            dict_out[date].append(f)

    for key in dict_out:
        if len(dict_out[key]) > 2:
            raise ValueError(f'For each dictionary key a list of two entries (VV & VH) is expected. '
                             f'The key \'{key}\' contains a list of {len(dict_out[key])} entries. Please check!')

    return dict_out


def get_vv_vh_file(file_dict_entry):
    """
    Using regex here instead of the index of file_dict_entry to avoid wrong variable bindings!
    """

    r_vh = re.compile('.*_VH_')
    r_vv = re.compile('.*_VV_')

    vh = os.path.join("/run/user/1000/gvfs/sftp:host=geo01.rz.uni-jena.de",
                      list(filter(r_vh.match, file_dict_entry))[0])
    vv = os.path.join("/run/user/1000/gvfs/sftp:host=geo01.rz.uni-jena.de",
                      list(filter(r_vv.match, file_dict_entry))[0])

    return vh, vv


def get_grid_info(file_dict_entry):

    src1 = rasterio.open(file_dict_entry[0])
    src2 = rasterio.open(file_dict_entry[1])

    shape1 = list(src1.shape)
    shape2 = list(src2.shape)
    transform1 = list(src1.transform)
    transform2 = list(src2.transform)

    if shape1 == shape2 and transform1 == transform2:
        return shape1, transform1
    else:
        raise ValueError(f"Shape and transform information of {os.path.basename(file_dict_entry[0])} and "
                         f"{os.path.basename(file_dict_entry[1])} were expected to be identical!")


def get_metadata(file_dict_entry, file_dict_key):
    """
    file_dict_entry -> ["full_path_to_vv_file", "full_path_to_vh_file"]

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

    date = file_dict_key
    dict_out['datetime'] = f'{date[0:4]}-{date[4:6]}-{date[6:8]}T{date[9:11]}:{date[11:13]}:{date[13:]}.000Z'
    # ...there's probably a more elegant way?

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


def create_eo3_yaml(file_dict, product_name, crs):

    for key in list(file_dict.keys()):

        path_vh, path_vv = get_vv_vh_file(file_dict[key])
        shape, transform = get_grid_info(file_dict[key])
        meta = get_metadata(file_dict[key], key)

        yaml_content = {
            'id': str(uuid.uuid4()),
            '$schema': 'https://schemas.opendatacube.org/dataset',
            'product': {'name': product_name},
            'crs': f"epsg:{crs}",
            'grids': {'default': {'shape': shape, 'transform': transform}
                      },
            'measurements': {'VH': {'path': path_vh},
                             'VV': {'path': path_vv}
                             },
            'properties': meta
        }

        yaml_dir = os.path.dirname(file_dict[key][0])
        yaml_name = f'{os.path.basename(file_dict[key][0])[:27]}.yaml'

        with open(os.path.join(yaml_dir, yaml_name), 'w') as stream:
            yaml.safe_dump(yaml_content, stream, sort_keys=False)


def main(file_dir, product_name, crs):

    ## Convert all files that are listed in file_list
    s1_convert(file_dir)

    ## Create list & dict from files in the directory
    file_dict = create_file_dict(file_dir)

    ## Create metadata YAMLs in EO3 format
    create_eo3_yaml(file_dict, product_name, crs)

    ## Anything else??

    return file_dict


f_dict = main(s1_dir, product_name, crs)


#############
## TEST AREA

#test_file1 = "/home/du23yow/Documents/MA/test_data/S1/20200602/S1A__IW___A_20200602T170001_VH_grd_mli_norm_geo_db_25832.tif"
#test_file2 = "/home/du23yow/Documents/MA/test_data/S1/20200602/S1A__IW___A_20200602T170001_VV_grd_mli_norm_geo_db_25832.tif"
