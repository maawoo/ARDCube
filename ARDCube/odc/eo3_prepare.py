# https://github.com/opendatacube/datacube-core/blob/develop/docs/ops/dataset_documents.rst

import os
import re
import glob
import yaml
import uuid
from osgeo import gdal
# from progress.bar import Bar
# import rasterio

main_dir = '/home/marco/pypypy/ARDCube_data'

l8_product = os.path.join(main_dir, 'misc/odc', 'landsat8.yaml')
s2_product = os.path.join(main_dir, 'misc/odc', 'sentinel2.yaml')
# s1_product = os.path.join(main_dir, 'misc/odc', 'sentinel1.yaml')


def read_product(product_path):

    with open(product_path) as f:
        yaml_dict = yaml.safe_load(f)

    name = yaml_dict['name']
    satellite = yaml_dict['metadata']['properties']['eo:constellation']
    crs = yaml_dict['storage']['crs']
    res = yaml_dict['storage']['resolution']['x']
    n_measurements = len(yaml_dict['measurements'])

    return {'name': name, 'satellite': satellite, 'crs': crs, 'res': res, 'n_measurements': n_measurements}


def create_file_list(file_dir, product_dict):

    list_out = []

    if product_dict['satellite'] is 'sentinel-1':
        for file in glob.iglob(os.path.join(file_dir, '**/*.tif'), recursive=True):
            list_out.append(file)

    else:
        for file in glob.iglob(os.path.join(file_dir, '**/*BOA.tif'), recursive=True):
            list_out.append(file)

    return list_out


def main(file_dir, product_path, overwrite=True):
    """

    :param file_dir:
    :param product_path:
    :param overwrite:
    :return:
    """

    ## ...
    product_dict = read_product(product_path)

    ## Create list & dict from files in the directory
    file_dict = create_file_list(file_dir, product_dict)

    return file_dict
