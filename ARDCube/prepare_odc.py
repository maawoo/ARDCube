from ARDCube.config import ROOT_DIR
from ARDCube.utils import get_settings

import os
import re
import glob
import yaml
import uuid
import logging
from datetime import datetime
import rasterio


def prepare_odc(sensor, overwrite=True):

    ## Create file dictionary
    file_dict = create_file_dict(sensor=sensor,
                                 overwrite=overwrite)

    print(f"\n#### Creating EO3 YAML files for {len(file_dict)} {sensor} files.")

    ## Create metadata YAML files in EO3 format
    create_eo3_yaml(sensor=sensor,
                    file_dict=file_dict)


def create_file_dict(sensor, overwrite):
    """Recursively searches a given directory for matching GeoTIFF files. Files that return a checksum of 0 for all
    bands will not be included and their path will be stored in a logfile.

    :param sensor:
    :param overwrite:

    :return: Dictionary of the form
        {'tileid__datestring': ['path/to/band_1.tif', 'path/to/band_2.tif', ...]}
        or
        {'tileid__datestring': ['path/to/multiband.tif']}
    """

    settings = get_settings()
    level2_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level2', sensor)

    if sensor == 'sentinel1':
        f_pattern = '**/*.tif'
    else:
        f_pattern = '**/*BOA.tif'

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    log_path = os.path.join(level2_dir, f'{timestamp}__prepare_odc__skipped.log')
    logging.basicConfig(filename=log_path, filemode='a', format='%(message)s', level='INFO')

    dict_out = {}
    for file in glob.iglob(os.path.join(level2_dir, f_pattern), recursive=True):

        ## Skip files that are very small (< 0.5 MB) because some of these are probably not valid.
        ## The log file can be used to check if valid files were skipped as well. If you want to include these, you can
        ## adjust the threshold here and run prepare_odc with overwrite=False. This will create YAML files for any files
        ## that were skipped previously.
        ## TODO: Better to just check the grid & AOI. Also not here but already in generate_ard.py!
        size_mb = os.path.getsize(file) / 10e5
        if size_mb < 0.5:
            logging.info(f"{file} - {size_mb} MB")
            continue
        else:
            ## Create identity key for each file based on date string and tile ID
            identity = _create_identity_string(file_path=file)

            ## Fill dictionary
            ## Bands that are stored as separate files (e.g. Sentinel-1 VV & VH bands) have the same identity key
            dict_keys = list(dict_out.keys())
            if identity not in dict_keys:
                dict_out[identity] = [file]
            else:
                dict_out[identity].append(file)

    if overwrite:
        return dict_out
    else:
        return _update_file_dict(level2_dir=level2_dir, file_dict=dict_out)


def create_eo3_yaml(sensor, file_dict):
    """Creates a YAML file for each entry of the input file dictionary. The YAML files are stored in EO3 format so they
    can be index into an Open Data Cube instance. For more information see:
    https://datacube-core.readthedocs.io/en/latest/ops/dataset_documents.html

    :param sensor:
    :param file_dict: Dictionary created by create_file_dict()

    :return: YAML file
    """

    ## Get information from product YAML(s)
    product_dict = _read_product_yaml(sensor=sensor)

    for key in list(file_dict.keys()):

        file_dict_entry = file_dict[key]
        file_path = file_dict[key][0]

        if sensor == 'sentinel1':
            orbit = _s1_is_asc_or_desc(file_path=file_path)
            prod_key = f"{sensor}_{orbit}.yaml"
        else:
            prod_key = f"{sensor}.yaml"

        shape, transform, crs_wkt = _get_grid_info(file_path=file_path)
        measurements = _get_measurements(sensor=sensor,
                                         file_dict_entry=file_dict_entry,
                                         band_names=product_dict[prod_key]['band_names'])
        meta = _get_metadata(sensor=sensor,
                             file_path=file_path)

        if product_dict[prod_key]['crs'] != crs_wkt:
            raise RuntimeError(f"The CRS specified in the product YAML {product_dict[prod_key]['name']} "
                               f"does not match the CRS of {file_path}")

        yaml_content = {
            'id': str(uuid.uuid4()),
            '$schema': 'https://schemas.opendatacube.org/dataset',
            'product': {'name': product_dict[prod_key]['name']},
            'crs': crs_wkt,
            'grids': {'default': {'shape': shape, 'transform': transform}
                      },
            'measurements': measurements,
            'properties': meta
        }

        yaml_dir = os.path.dirname(file_path)
        yaml_name = _format_yaml_name(sensor=sensor, file_path=file_path)

        with open(os.path.join(yaml_dir, yaml_name), 'w') as stream:
            yaml.safe_dump(yaml_content, stream, sort_keys=False)


def _create_identity_string(file_path):
    """Creates an identity string for a given file based on its tile ID and date string."""

    ## Get date string from filename
    date = _get_date_string(file_path=file_path)

    ## Get tile ID from directory name (FORCE directory structure is assumed!)
    f_dir = os.path.dirname(file_path)
    tile_id = os.path.basename(f_dir)

    ## Create identity string
    identity = f'{tile_id}__{date}'

    return identity


def _update_file_dict(level2_dir, file_dict):
    """Recursively searches for existing YAML files in the given directory. If YAML files are found, the input file
    dictionary will be filtered for entries that don't have an associated YAML file already.

    :param level2_dir: Path of the file directory. Subdirectories are also searched.
    :param file_dict: Dictionary created by create_file_dict()

    :return: Dictionary of the same form as the input dictionary (see create_file_dict() for examples).
    """

    ## Search for existing YAML-files in the file directory and use same identification as in create_file_dict()
    yaml_dict = {}
    for f in glob.iglob(os.path.join(level2_dir, '**/*.yaml'), recursive=True):

        ## Create identity key for each file based on date string and tile ID
        identity = _create_identity_string(file_path=f)

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


def _get_date_string(file_path, do_format=False):
    """Extracts the date string from a file name."""

    f_base = os.path.basename(file_path)

    ## Search either for the 8 digit pattern (YYYYmmdd) used in files that were processed with FORCE.
    ## Or the 15 digit pattern (YYYYmmddTHHMMSS) used in files that were processed with pyroSAR. The underscore is
    ## necessary, because otherwise only the former pattern is found.
    rs = re.search(r'\d{8}|_\d{8}T\d{6}', f_base)
    date = rs.group()
    date = date.replace("_", "")

    if do_format:
        return _format_date_string(date=date)
    else:
        return date


def _format_date_string(date):
    """Formats a date string from either YYYYmmdd or YYYYmmddTHHMMSS to YYYY-mm-ddTHH:MM:SS.000Z."""

    if len(date) == 8:
        date = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%dT10:00:00.000Z')  # Use 10 am as a default?
    elif len(date) == 15:
        date = datetime.strptime(date, '%Y%m%dT%H%M%S').strftime('%Y-%m-%dT%H:%M:%S.000Z')
    else:
        raise RuntimeError('Length of date string is expected to be of length 8 or 15 based on existing file naming '
                           'conventions.')

    return date


def _read_product_yaml(sensor):
    """Returns information from Product YAML as a dictionary."""

    if sensor == 'sentinel1':
        product_path = [os.path.join(ROOT_DIR, 'settings/odc', f"{sensor}_asc.yaml"),
                        os.path.join(ROOT_DIR, 'settings/odc', f"{sensor}_desc.yaml")]
    else:
        product_path = [os.path.join(ROOT_DIR, 'settings/odc', f"{sensor}.yaml")]

    dict_out = {}
    for path in product_path:
        with open(path) as f:
            yaml_dict = yaml.safe_load(f)

            name = yaml_dict['name']
            crs = yaml_dict['storage']['crs']
            res = yaml_dict['storage']['resolution']['x']
            band_names = [yaml_dict['measurements'][i]['name'] for i in range(len(yaml_dict['measurements']))]

        dict_out[os.path.basename(path)] = {'name': name, 'crs': crs, 'res': res, 'band_names': band_names}

    return dict_out


def _s1_is_asc_or_desc(file_path):
    """..."""

    file = os.path.basename(file_path)

    if file[10:11] == 'A':
        return 'asc'
    elif file[10:11] == 'D':
        return 'desc'
    else:
        raise RuntimeError(f"Can't determine orbit direction of {file_path}")


def _get_grid_info(file_path):
    """Get shape and transform information for a raster file."""

    with rasterio.open(file_path) as src:
        shape = list(src.shape)
        transform = list(src.transform)
        crs = src.crs.wkt

    return shape, transform, crs


def _get_measurements(sensor, file_dict_entry, band_names):
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
    if sensor == 'sentinel1':
        if len(file_dict_entry) != len(band_names):
            raise RuntimeError(f"An equal number of files and band names is expected for sentinel1: \n"
                               f"file_dict_entry: {file_dict_entry} \n"
                               f"band_names: {band_names}")

        for band in band_names:
            path = [path for path in file_dict_entry if band in path][0]
            path_rel = os.path.basename(path)
            dict_out[band] = {'path': path_rel}
    else:
        for band, i in zip(band_names, range(len(band_names))):
            path_rel = os.path.basename(file_dict_entry[0])
            dict_out[band] = {'path': path_rel, 'band': i+1}  # +1 because range() starts at 0 not 1

        ## Replace entry for pixel_qa band
        dict_out['pixel_qa'] = {'path': os.path.basename(file_dict_entry[0]).replace('BOA', 'QAI')}

    return dict_out


def _get_metadata(sensor, file_path):
    """Creates a dictionary that can be used as direct input for the properties section of an EO3 YAML file.

    ODC currently uses the EO3 format for the YAML files, which is supposed to be an intermediate format before moving
    on to STAC. The 'properties' section in the YAML, which is filled with the dictionary created in this function,
    already uses STAC standard names. For more information see:
    https://datacube-core.readthedocs.io/en/latest/ops/dataset_documents.html
    https://github.com/radiantearth/stac-spec/tree/master/item-spec
    https://github.com/radiantearth/stac-spec/tree/master/extensions/sar (other extensions in parent directory!)

    Timestamp is the only compulsory field. Other useful metadata can/should be added later on.

    :param sensor:
    :param file_path:

    :return: Dictionary with entries for each metadata field.
    """

    date = _get_date_string(file_path=file_path, do_format=True)

    if sensor == 'sentinel1':
        orbit = _s1_is_asc_or_desc(file_path=file_path)
        return {'datetime': date,
                'sat:orbit_state': orbit}
    else:
        return {'datetime': date}


def _format_yaml_name(sensor, file_path):
    """..."""

    if sensor == 'sentinel1':
        return f"{os.path.splitext(os.path.basename(file_path))[0]}.yaml"
    else:
        return f"{os.path.basename(file_path).replace('_BOA.tif', '.yaml')}"
