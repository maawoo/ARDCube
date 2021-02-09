# https://github.com/opendatacube/datacube-core/blob/develop/docs/ops/dataset_documents.rst

import os
import re
import glob
import yaml
import uuid
import logging
from datetime import datetime
import rasterio

main_dir = '/home/marco/pypypy/ARDCube_data'

l8_product = os.path.join(main_dir, 'misc/odc', 'landsat8.yaml')
s2_product = os.path.join(main_dir, 'misc/odc', 'sentinel2.yaml')
s1_product = os.path.join(main_dir, 'misc/odc', 'sentinel1.yaml')

time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_path = os.path.join(main_dir, 'log', f'{time}__eo3_prepare_failed_checksum.log')
logging.basicConfig(filename=log_path, filemode='a', format='%(message)s', level='INFO')  # save to file


def read_product(product_path):

    with open(product_path) as f:
        yaml_dict = yaml.safe_load(f)

    name = yaml_dict['name']
    satellite = yaml_dict['metadata']['properties']['eo:constellation']
    crs = yaml_dict['storage']['crs']
    res = yaml_dict['storage']['resolution']['x']
    n_measurements = len(yaml_dict['measurements'])

    return {'name': name, 'satellite': satellite, 'crs': crs, 'res': res, 'n_measurements': n_measurements}


def get_checksums(file):

    src = rasterio.open(file)
    checksums = [src.checksum(i) for i in src.indexes]
    src.close()

    return checksums


def create_file_dict(file_dir, product_dict):

    if product_dict['satellite'] == 'sentinel-1':
        f_pattern = '**/*.tif'
        t_pattern = r'\d{8}T\d{6}'
    else:
        f_pattern = '**/*BOA.tif'
        t_pattern = r'\d{8}'

    dict_out = {}
    for f in glob.iglob(os.path.join(file_dir, f_pattern), recursive=True):
        if sum(get_checksums(f)) != 0:

            ## Get date string from filename
            f_base = os.path.basename(f)
            rs = re.search(t_pattern, f_base)
            date = rs.group()

            ## Get tile ID from directory name (FORCE directory structure is assumed!)
            f_dir = os.path.dirname(f)
            tile_id = os.path.basename(f_dir)

            ## Create identity key for each file based on date string and tile ID
            identity = f'{tile_id}__{date}'

            ## Create dictionary
            ## Bands that are stored as separate files (e.g. Sentinel-1 VV & VH bands) have the same identity key
            dict_keys = list(dict_out.keys())
            if identity not in dict_keys:
                dict_out[identity] = [f]
            else:
                dict_out[identity].append(f)

        else:
            ## Log file path if sum of checksums is 0, which means that something is likely wrong with that file
            logging.info(f)

    return dict_out


def check_file_dict(file_dict):
    return None


def get_grid_info(file_dict_entry):

    src = rasterio.open(file_dict_entry[0])
    shape = list(src.shape)
    transform = list(src.transform)
    src.close()

    return shape, transform


def get_measurements(file_dict_entry):
    return None


def get_metadata(file_dict_entry):
    return None


def create_eo3_yaml(file_dict, product_dict):

    product_name = product_dict['name']
    crs = product_dict['crs']

    ## ...
    if product_dict['satellite'] == 'sentinel-1':
        ind_out_name = 27
    else:
        ind_out_name = 25

    for key in list(file_dict.keys()):

        shape, transform = get_grid_info(file_dict[key])
        measurements = get_measurements(file_dict[key])
        meta = get_metadata(file_dict[key])

        yaml_content = {
            'id': str(uuid.uuid4()),
            '$schema': 'https://schemas.opendatacube.org/dataset',
            'product': {'name': product_name},
            'crs': f"epsg:{crs}",
            'grids': {'default': {'shape': shape, 'transform': transform}
                      },
            'measurements': measurements,
            'properties': meta
        }

        yaml_dir = os.path.dirname(file_dict[key][0])
        yaml_name = f'{os.path.basename(file_dict[key][0])[:ind_out_name]}.yaml'

        with open(os.path.join(yaml_dir, yaml_name), 'w') as stream:
            yaml.safe_dump(yaml_content, stream, sort_keys=False)


def main(file_dir, product_path, overwrite=True):
    """

    :param file_dir:
    :param product_path:
    :param overwrite:
    :return:
    """

    ## Create product dictionary
    product_dict = read_product(product_path)

    ## Create file dictionary
    file_dict = create_file_dict(file_dir, product_dict)

    ## ...
    if not overwrite:
        file_dict = check_file_dict(file_dict)

    ## Create metadata YAMLs in EO3 format
    create_eo3_yaml(file_dict, product_dict)

    return None


#########

#file_dir_s1 = os.path.join(main_dir, 'level-2/S1_20')
#file_dir_l8 = os.path.join(main_dir, 'level-2/L8_30')

#file_dict = main(file_dir_l8, l8_product)
#file_dict_s1 = main(file_dir_s1, s1_product)




