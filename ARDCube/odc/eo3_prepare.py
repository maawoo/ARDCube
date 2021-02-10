import os
import re
import glob
import yaml
import uuid
import logging
from datetime import datetime
import rasterio

## True = existing YAML-files will be overwritten // False = YAML-files will only be generated for new files
overwrite = True

## Set paths
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
    band_names = [yaml_dict['measurements'][i]['name'] for i in range(len(yaml_dict['measurements']))]

    return {'name': name, 'satellite': satellite, 'crs': crs, 'res': res, 'band_names': band_names}


def get_checksums(file_path):

    src = rasterio.open(file_path)
    checksums = [src.checksum(i) for i in src.indexes]
    src.close()

    return checksums


def get_date_string(file_path):

    f_base = os.path.basename(file_path)
    rs = re.search(r'\d{8}|_\d{8}T\d{6}', f_base)  # Without the underscore it only finds the 8 digit pattern
    date = rs.group()
    date = date.replace("_", "")  # Remove underscore if it exists

    return date


def format_date_string(date):

    if len(date) == 8:
        date = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%dT10:00:00.000Z')
    elif len(date) == 15:
        date = datetime.strptime(date, '%Y%m%dT%H%M%S').strftime('%Y-%m-%dT%H:%M:%S.000Z')
    else:
        raise IndexError('Length of date string is expected to be of length 8 or 15 based on existing file naming '
                         'conventions.')

    return date


def create_identity_string(file_path):

    ## Get date string from filename
    date = get_date_string(file_path)

    ## Get tile ID from directory name (FORCE directory structure is assumed!)
    f_dir = os.path.dirname(file_path)
    tile_id = os.path.basename(f_dir)

    ## Create identity key for each file based on date string and tile ID
    identity = f'{tile_id}__{date}'

    return identity


def create_file_dict(file_dir, product_dict):

    if product_dict['satellite'] == 'sentinel-1':
        f_pattern = '**/*.tif'
    else:
        f_pattern = '**/*BOA.tif'

    dict_out = {}
    for f in glob.iglob(os.path.join(file_dir, f_pattern), recursive=True):
        if sum(get_checksums(f)) != 0:

            ## Create identity key for each file based on date string and tile ID
            identity = create_identity_string(f)

            ## Fill dictionary
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


def check_file_dict(file_dir, file_dict):

    ## Search for existing YAML-files in the file directory and use same identification as in create_file_dict()
    yaml_dict = {}
    for f in glob.iglob(os.path.join(file_dir, '**/*.yaml'), recursive=True):

        ## Create identity key for each file based on date string and tile ID
        identity = create_identity_string(f)

        ## Fill dictionary
        yaml_dict[identity] = f

    ## Create new file dictionary if existing YAML files were found, else return initial file dictionary
    if len(list(yaml_dict.keys())) != 0:

        file_dict_new = {}
        for key in list(file_dict.keys()):

            if key in list(yaml_dict.keys()):
                continue
            else:
                file_dict_new[key] = file_dict[key]

        return file_dict_new

    else:
        return file_dict


def get_grid_info(file_dict_entry):

    src = rasterio.open(file_dict_entry[0])
    shape = list(src.shape)
    transform = list(src.transform)
    src.close()

    return shape, transform


def get_measurements(file_dict_entry, multi_band_tif, band_names):
    """
    Example output if multi_band_tif is False:
    {'VH': {'path': vh.tif},
     'VV': {'path': vv.tif}
     }

    Example output if multi_band_tif is True:
    {'blue': {'path': multi_band.tif, 'band': 1},
     'green': {'path': multi_band.tif, 'band': 2},
     ...
    }

    :param file_dict_entry:
    :param multi_band_tif:
    :param band_names:
    :return:
    """

    dict_out = {}

    if multi_band_tif:
        for band, i in zip(band_names, range(len(band_names))):
            path = os.path.basename(file_dict_entry[0])
            dict_out[band] = {'path': path, 'band': i+1}

    else:
        assert len(file_dict_entry) == len(band_names), 'An equal number of file paths as band names is expected!'

        for band in band_names:
            path = [path for path in file_dict_entry if band in path][0]
            path = os.path.basename(path)
            dict_out[band] = {'path': path}

    return dict_out


def get_metadata(file_dict_entry):
    """
    ODC currently uses the EO3 format for the YAML files, which is supposed to be an intermediate format before moving
    on to STAC. The 'properties' section in the YAML, which is filled with the dictionary created in this function,
    already uses STAC standard names. For more information see:
    https://datacube-core.readthedocs.io/en/latest/ops/dataset_documents.html
    https://github.com/radiantearth/stac-spec/tree/master/item-spec
    https://github.com/radiantearth/stac-spec/tree/master/extensions/sar (other extensions in parent directory!)

    Timestamp is the only compulsory field. Other useful metadata can be added later on.

    :param file_dict_entry:
    :param satellite:
    :return:
    """

    dict_out = {}
    dict_out['datetime'] = format_date_string(get_date_string(file_dict_entry[0]))

    return dict_out


def create_eo3_yaml(file_dict, product_dict):

    product_name = product_dict['name']
    crs = product_dict['crs']
    band_names = product_dict['band_names']

    ## The index 'ind_outname' is used in the for-loop to name the generated YAML-files based on the input files.
    ## Both FORCE and pyroSAR use their own naming conventions, so file names should be consistent.
    ## Also 'multi_band_tif' is set to True or False, depending on SAR or optical imagery. The default for pyroSAR is to
    ## store VH & VV bands in separate GeoTIFFs, whereas FORCE stores multiple bands in a single GeoTIFF file.
    if product_dict['satellite'] == 'sentinel-1':
        ind_outname = 27
        multi_band_tif = False
    else:
        ind_outname = 25
        multi_band_tif = True

    for key in list(file_dict.keys()):

        shape, transform = get_grid_info(file_dict[key])
        measurements = get_measurements(file_dict[key], multi_band_tif, band_names)
        meta = get_metadata(file_dict[key])

        yaml_content = {
            'id': str(uuid.uuid4()),
            '$schema': 'https://schemas.opendatacube.org/dataset',
            'product': {'name': product_name},
            'crs': f"{crs}",
            'grids': {'default': {'shape': shape, 'transform': transform}
                      },
            'measurements': measurements,
            'properties': meta
        }

        yaml_dir = os.path.dirname(file_dict[key][0])
        yaml_name = f'{os.path.basename(file_dict[key][0])[:ind_outname]}.yaml'

        with open(os.path.join(yaml_dir, yaml_name), 'w') as stream:
            yaml.safe_dump(yaml_content, stream, sort_keys=False)


def main(file_dir, product_path, overwrite=None):
    """

    :param file_dir:
    :param product_path:
    :param overwrite:
    :return:
    """

    assert isinstance(overwrite, bool), 'Parameter \'overwrite\' is expected to be set to True or False!'

    ## Create product dictionary
    product_dict = read_product(product_path)

    ## Create file dictionary
    file_dict = create_file_dict(file_dir, product_dict)

    ## Check for existing YAML files and create new dict, if overwrite is set to 'False'
    if overwrite is False:
        file_dict = check_file_dict(file_dir, file_dict)

    ## Create metadata YAML files in EO3 format
    create_eo3_yaml(file_dict, product_dict)

    return product_dict



