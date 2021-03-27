import os
import re
import glob
import yaml
import uuid
import logging
from datetime import datetime
import rasterio


def main(file_dir, product_path, overwrite=None):

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


def read_product(product_path):
    """Returns information from Product YAML as a dictionary."""

    with open(product_path) as f:
        yaml_dict = yaml.safe_load(f)

    name = yaml_dict['name']
    satellite = yaml_dict['metadata']['properties']['eo:constellation']
    crs = yaml_dict['storage']['crs']
    res = yaml_dict['storage']['resolution']['x']
    band_names = [yaml_dict['measurements'][i]['name'] for i in range(len(yaml_dict['measurements']))]

    return {'name': name, 'satellite': satellite, 'crs': crs, 'res': res, 'band_names': band_names}


def create_file_dict(file_dir, product_dict):
    """Recursively searches a given directory for matching GeoTIFF files. Files that return a checksum of 0 for all
    bands will not be included and their path will be stored in a logfile.

    :param file_dir: Path of the file directory. Subdirectories are also searched.
    :param product_dict: Product dictionary created by read_product()

    :return: Dictionary of the form
        {'tileid__datestring': ['path/to/band_1.tif', 'path/to/band_2.tif', ...]}
        or
        {'tileid__datestring': ['path/to/multiband.tif']}
    """

    if product_dict['satellite'] == 'sentinel-1':
        f_pattern = '**/*.tif'
    else:
        f_pattern = '**/*BOA.tif'

    dict_out = {}
    for f in glob.iglob(os.path.join(file_dir, f_pattern), recursive=True):
        if sum(_get_checksums(f)) != 0:

            ## Create identity key for each file based on date string and tile ID
            identity = _create_identity_string(f)

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
    """Recursively searches for existing YAML files in the given directory. If YAML files are found, the input file
    dictionary will be filtered for entries that don't have an associated YAML file already.

    :param file_dir: Path of the file directory. Subdirectories are also searched.
    :param file_dict: Dictionary created by create_file_dict()

    :return: Dictionary of the same form as the input dictionary (see create_file_dict() for examples).
    """

    ## Search for existing YAML-files in the file directory and use same identification as in create_file_dict()
    yaml_dict = {}
    for f in glob.iglob(os.path.join(file_dir, '**/*.yaml'), recursive=True):

        ## Create identity key for each file based on date string and tile ID
        identity = _create_identity_string(f)

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


def create_eo3_yaml(file_dict, product_dict):
    """Creates a YAML file for each entry of the input file dictionary. The YAML files are stored in EO3 format so they
    can be index into an Open Data Cube instance. For more information see:
    https://datacube-core.readthedocs.io/en/latest/ops/dataset_documents.html

    :param file_dict: Dictionary created by create_file_dict() or filtered by check_file_dict().
    :param product_dict: Product dictionary created by read_product()

    :return: YAML file
    """

    product_name = product_dict['name']
    crs = product_dict['crs']
    band_names = product_dict['band_names']

    ## The index 'ind_outname' is used in the for-loop to name the generated YAML-files based on the input files.
    ## Both FORCE and pyroSAR use their own naming conventions, so file names should be consistent.
    if product_dict['satellite'] == 'sentinel-1':
        ind_outname = 27
    else:
        ind_outname = 25

    for key in list(file_dict.keys()):

        shape, transform, crs_wkt = _get_grid_info(file_dict[key])
        measurements = _get_measurements(file_dict[key], band_names)
        meta = _get_metadata(file_dict[key])

        yaml_content = {
            'id': str(uuid.uuid4()),
            '$schema': 'https://schemas.opendatacube.org/dataset',
            'product': {'name': product_name},
            'crs': f"{crs_wkt}",
            'grids': {'default': {'shape': shape, 'transform': transform}
                      },
            'measurements': measurements,
            'properties': meta
        }

        yaml_dir = os.path.dirname(file_dict[key][0])
        yaml_name = f'{os.path.basename(file_dict[key][0])[:ind_outname]}.yaml'

        with open(os.path.join(yaml_dir, yaml_name), 'w') as stream:
            yaml.safe_dump(yaml_content, stream, sort_keys=False)


def _get_checksums(file_path):
    """Returns the checksum for each band of a raster as a list."""

    src = rasterio.open(file_path)
    checksums = [src.checksum(i) for i in src.indexes]
    src.close()

    return checksums


def _create_identity_string(file_path):
    """Creates an identity string for a given file based on its tile ID and date string."""

    ## Get date string from filename
    date = _get_date_string(file_path)

    ## Get tile ID from directory name (FORCE directory structure is assumed!)
    f_dir = os.path.dirname(file_path)
    tile_id = os.path.basename(f_dir)

    ## Create identity string
    identity = f'{tile_id}__{date}'

    return identity


def _get_date_string(file_path):
    """Extracts the date string from a file name."""

    f_base = os.path.basename(file_path)

    ## Search either for the 8 digit pattern (YYYYmmdd) used in files that were processed with FORCE.
    ## Or the 15 digit pattern (YYYYmmddTHHMMSS) used in files that were processed with pyroSAR. The underscore is
    ## necessary, because otherwise only the former pattern is found.
    rs = re.search(r'\d{8}|_\d{8}T\d{6}', f_base)
    date = rs.group()
    date = date.replace("_", "")

    return date


def _format_date_string(date):
    """Formats a date string from either YYYYmmdd or YYYYmmddTHHMMSS to YYYY-mm-ddTHH:MM:SS.000Z."""

    if len(date) == 8:
        date = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%dT10:00:00.000Z')  # Use 10 am as a default?
    elif len(date) == 15:
        date = datetime.strptime(date, '%Y%m%dT%H%M%S').strftime('%Y-%m-%dT%H:%M:%S.000Z')
    else:
        raise IndexError('Length of date string is expected to be of length 8 or 15 based on existing file naming '
                         'conventions.')

    return date


def _get_grid_info(file_dict_entry):
    """Get shape and transform information for a raster file."""

    src = rasterio.open(file_dict_entry[0])
    shape = list(src.shape)
    transform = list(src.transform)
    crs = src.crs.wkt

    src.close()

    return shape, transform, crs


def _get_measurements(file_dict_entry, band_names):
    """Creates a dictionary that can be used as direct input for the measurement section of an EO3 YAML file.

    :param file_dict_entry: Either ['path/to/multiband.tif'] or ['path/to/band_1.tif', 'path/to/band_2.tif', ...]
    :param band_names: List of band names

    :return: Dictionary of the form
        {'VH': {'path': vh.tif},
        'VV': {'path': vv.tif}}
        or
        {'blue': {'path': multi_band.tif, 'band': 1},
         'green': {'path': multi_band.tif, 'band': 2},
         ...}
    """

    dict_out = {}

    ## Landsat 8 & Sentinel 2
    if len(file_dict_entry) == 1:
        for band, i in zip(band_names, range(len(band_names))):
            path = os.path.basename(file_dict_entry[0])
            dict_out[band] = {'path': path, 'band': i+1}  # +1 because range() starts at 0 not 1

        ## Add QAI file
        base_name = os.path.basename(file_dict_entry[0])
        qai_band = base_name.replace('BOA', 'QAI')
        dict_out['qai'] = {'path': qai_band, 'band': len(band_names)+1}

    ## Sentinel 1
    else:
        assert len(file_dict_entry) == len(band_names), 'An equal number of file paths as band names is expected!'

        for band in band_names:
            path = [path for path in file_dict_entry if band in path][0]
            path = os.path.basename(path)
            dict_out[band] = {'path': path}

    return dict_out


def _get_metadata(file_dict_entry):
    """Creates a dictionary that can be used as direct input for the properties section of an EO3 YAML file.

    ODC currently uses the EO3 format for the YAML files, which is supposed to be an intermediate format before moving
    on to STAC. The 'properties' section in the YAML, which is filled with the dictionary created in this function,
    already uses STAC standard names. For more information see:
    https://datacube-core.readthedocs.io/en/latest/ops/dataset_documents.html
    https://github.com/radiantearth/stac-spec/tree/master/item-spec
    https://github.com/radiantearth/stac-spec/tree/master/extensions/sar (other extensions in parent directory!)

    Timestamp is the only compulsory field. Other useful metadata can/should be added later on.

    :param file_dict_entry: Either ['path/to/multiband.tif'] or ['path/to/band_1.tif', 'path/to/band_2.tif', ...]

    :return: Dictionary with entries for each metadata field.
    """

    dict_out = {}
    dict_out['datetime'] = _format_date_string(_get_date_string(file_dict_entry[0]))

    return dict_out


## True = existing YAML-files will be overwritten // False = YAML-files will only be generated for new files
overwrite = True

## Set paths
data_dir = '/home/marco/pypypy/ARDCube_data'
code_dir = '/home/marco/pypypy/ARDCube'
#l8_product = os.path.join(code_dir, 'misc/odc', 'landsat8_glance.yaml')
s2_product = os.path.join(code_dir, 'misc/odc', 'sentinel2_glance.yaml')
#s1_product = os.path.join(code_dir, 'misc/odc', 'sentinel1_glance.yaml')

time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_path = os.path.join(data_dir, 'log', f'{time}__eo3_prepare_failed_checksum.log')
logging.basicConfig(filename=log_path, filemode='a', format='%(message)s', level='INFO')  # save to file

#main(os.path.join(data_dir, 'level2/Landsat8_glance7'), l8_product, overwrite)
#main(os.path.join(data_dir, 'level2/Sentinel1_glance7'), s1_product, overwrite)
main(os.path.join(data_dir, 'level2/Sentinel2_glance7'), s2_product, overwrite)
