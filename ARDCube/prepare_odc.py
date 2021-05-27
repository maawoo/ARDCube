from ARDCube.config import ROOT_DIR
from ARDCube.utils.general import get_settings

import os
import re
import glob
import yaml
import uuid
import logging
from datetime import datetime
import rasterio


def prepare_odc(sensor, overwrite=True):
    """Main function of this module, which creates 'Dataset Documents' to index each GeoTIFF file of a given dataset
    into an Open Data Cube (ODC) instance. The documents are saved alongside each source file and stored in the YAML
    format and in the ODC EO3 schema. More information can be found here:
    https://datacube-core.readthedocs.io/en/latest/ops/dataset_documents.html
    Note that a 'Product Definition' file for the dataset needs to be created beforehand and is expected to be located
    in the /settings/odc directory.

    Parameters
    ----------
    sensor: string
        Name of the sensor/dataset that ODC Dataset Documents should be created for.
        Example: 'landsat8'
    overwrite: boolean (optional)
        If set to False, only Dataset Documents for new files will be created.
    """

    file_dict = create_file_dict(sensor=sensor, overwrite=overwrite)

    print(f"\n#### Creating ODC YAML files for {len(file_dict)} {sensor} files.")
    create_eo3_yaml(sensor=sensor, file_dict=file_dict)

    # Index into ODC instance


def create_file_dict(sensor, overwrite):
    """Recursively searches a level-2 directory for GeoTIFF files and creates a dictionary of the form
    {'tileID__date': ['path_to_VV_band', 'path_to_VH_band']}. If bands are not stored separately, which is the case for
    optical data processed with FORCE, the list only contains a single path to the multiband GeoTIFF."""

    settings = get_settings()
    level2_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'level2', sensor)

    if sensor == 'sentinel1':
        f_pattern = '**/*.tif'
    else:
        f_pattern = '**/*BOA.tif'

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    log_dir = os.path.join(settings['GENERAL']['DataDirectory'], 'log')
    log_path = os.path.join(log_dir, f'{timestamp}__{sensor}__prepare_odc.log')

    file_dict = {}
    for file in glob.iglob(os.path.join(level2_dir, f_pattern), recursive=True):

        ## Skip files that are very small as they probably only contain no data values and are therefore not valid.
        ## This bug has been observed for Sentinel-1 data after tiling it using 'force-cube'.
        ## The log file can be used to check which files were skipped. If you notice that any valid files have been
        ## skipped as well, you can adjust the threshold here and run prepare_odc() again with overwrite=False.
        ## This will create YAML files for any files that were skipped previously.
        ## TODO: Better to just check the grid & AOI. Also not here but already in generate_ard.py!
        ## 2021-05-26: Leaving this for now as it's a 'force-cube' bug and should be fixed there.
        size_mb = os.path.getsize(file) / 10e5
        if size_mb < 0.42:
            logging.basicConfig(filename=log_path, filemode='a', format='%(message)s', level='INFO')
            logging.info(f"{file} - {size_mb} MB")
            continue
        else:
            ## Create identity key for each file based on date string and tile ID
            identity = _create_identity_string(file_path=file)

            ## Fill dictionary
            ## Bands that are stored as separate files (e.g. Sentinel-1 VV & VH bands) have the same identity key
            dict_keys = list(file_dict.keys())
            if identity not in dict_keys:
                file_dict[identity] = [file]
            else:
                file_dict[identity].append(file)

    if overwrite:
        return file_dict
    else:
        return _update_file_dict(level2_dir=level2_dir, file_dict=file_dict)


def create_eo3_yaml(sensor, file_dict):
    """Creates a YAML file in the EO3 schema for each entry of the provided file dictionary."""

    product_dict = _read_product_yaml(sensor=sensor)

    for key in list(file_dict.keys()):

        file_dict_entry = file_dict[key]

        if sensor == 'sentinel1':
            orbit = _s1_is_asc_or_desc(file_path=file_dict_entry[0])
            prod_key = f"{sensor}_{orbit}.yaml"
        else:
            prod_key = f"{sensor}.yaml"

        shape, transform, crs_wkt = _get_grid_info(file_path=file_dict_entry[0])
        measurements = _get_measurements(sensor=sensor, file_dict_entry=file_dict_entry,
                                         band_names=product_dict[prod_key]['band_names'])
        properties = _get_properties(sensor=sensor, file_path=file_dict_entry[0])

        if product_dict[prod_key]['crs'] != crs_wkt:
            raise RuntimeError(f"The CRS specified in the product YAML {product_dict[prod_key]['name']} "
                               f"does not match the CRS of {file_dict_entry[0]}")

        yaml_content = {
            'id': str(uuid.uuid4()),
            '$schema': 'https://schemas.opendatacube.org/dataset',
            'product': {'name': product_dict[prod_key]['name']},
            'crs': crs_wkt,
            'grids': {'default': {'shape': shape,
                                  'transform': transform}
                      },
            'measurements': measurements,
            'properties': properties
        }

        yaml_dir = os.path.dirname(file_dict_entry[0])
        yaml_name = _format_yaml_name(sensor=sensor, file_path=file_dict_entry[0])

        with open(os.path.join(yaml_dir, yaml_name), 'w') as stream:
            yaml.safe_dump(yaml_content, stream, sort_keys=False)


def _create_identity_string(file_path):
    """Helper function for create_file_dict() to create an identifiable string for a given file based on its tile ID and
    acquisition date."""

    date = _get_date_string(file_path=file_path)
    tile_id = os.path.basename(os.path.dirname(file_path))

    return f"{tile_id}__{date}"


def _update_file_dict(level2_dir, file_dict):
    """Helper function for create_file_dict(). Recursively searches for existing YAML files in the given directory.
    If YAML files are found, file_dict will be filtered for entries that do not have an associated YAML file already."""

    ## Search for existing YAML-files in the file directory and use same identification as in create_file_dict()
    yaml_dict = {}
    for file in glob.iglob(os.path.join(level2_dir, '**/*.yaml'), recursive=True):
        identity = _create_identity_string(file_path=file)
        yaml_dict[identity] = file

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


def _get_date_string(file_path, sensor=None, do_format=False):
    """Helper function to extract the date from a file name."""

    f_base = os.path.basename(file_path)

    ## Search either for the 8 digit pattern (YYYYmmdd) used in files that were processed with FORCE.
    ## Or the 15 digit pattern (YYYYmmddTHHMMSS) used in files that were processed with pyroSAR. The underscore is
    ## necessary, because otherwise only the former pattern is found.
    rs = re.search(r'\d{8}|_\d{8}T\d{6}', f_base)
    date = rs.group()
    date = date.replace("_", "")

    if do_format:
        return _format_date_string(date=date, sensor=sensor)
    else:
        return date


def _format_date_string(date, sensor):
    """Helper function to format a date string from either YYYYmmdd or YYYYmmddTHHMMSS to YYYY-mm-ddTHH:MM:SS.000Z."""

    if len(date) == 8:
        if sensor.startswith('landsat'):
            date = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%dT10:00:00.000Z')  # Landsat
        else:
            date = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%dT10:30:00.000Z')  # Sentinel-2
    elif len(date) == 15:
        date = datetime.strptime(date, '%Y%m%dT%H%M%S').strftime('%Y-%m-%dT%H:%M:%S.000Z')  # Sentinel-1
    else:
        raise RuntimeError("Length of date string is expected to be of length 8 or 15 based on existing file naming "
                           "conventions used by pyroSAR and FORCE.")

    return date


def _read_product_yaml(sensor):
    """Helper function for create_eo3_yaml() to return information from Product Definition YAML."""

    if sensor == 'sentinel1':
        product_path = [os.path.join(ROOT_DIR, 'settings', 'odc',  f"{sensor}_asc.yaml"),
                        os.path.join(ROOT_DIR, 'settings', 'odc', f"{sensor}_desc.yaml")]
    else:
        product_path = [os.path.join(ROOT_DIR, 'settings', 'odc', f"{sensor}.yaml")]

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
    """Helper function for create_eo3_yaml() to get information on SAR orbit from filename based on pyroSAR's naming
    convention."""

    file = os.path.basename(file_path)

    if file[10:11] == 'A':
        return 'asc'
    elif file[10:11] == 'D':
        return 'desc'
    else:
        raise RuntimeError(f"Can't determine orbit direction of {file_path}")


def _get_grid_info(file_path):
    """Helper function for create_eo3_yaml() to get necessary shape and transform information from a raster file."""

    with rasterio.open(file_path) as src:
        shape = list(src.shape)
        transform = list(src.transform)
        crs = src.crs.wkt

    return shape, transform, crs


def _get_measurements(sensor, file_dict_entry, band_names):
    """Helper function for create_eo3_yaml() to create a dictionary for the measurement section of the Dataset
    Document. The dictionary has the following form depending on SAR or optical dataset:
        {'VH': {'path': vh_band.tif},
        'VV': {'path': vv_band.tif}}
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

        ## Add pixel_qa band by adjusting the filename (FORCE has a fixed naming convention)
        dict_out['pixel_qa'] = {'path': os.path.basename(file_dict_entry[0]).replace('BOA', 'QAI')}

    return dict_out


def _get_properties(sensor, file_path):
    """Helper function for create_eo3_yaml() to create a dictionary for the properties section of the Dataset Document.
    Datetime is the only compulsory field and orbit state is used to create two separate datasets for ascending and
    descending Sentinel-1 orbit. Other useful properties can be added later on if needed."""

    date = _get_date_string(file_path=file_path, sensor=sensor, do_format=True)

    if sensor == 'sentinel1':
        orbit = _s1_is_asc_or_desc(file_path=file_path)
        return {'datetime': date,
                'sat:orbit_state': orbit}
    else:
        return {'datetime': date}


def _format_yaml_name(sensor, file_path):
    """Helper function for create_eo3_yaml() to format output YAML name depending on sensor."""

    if sensor == 'sentinel1':
        return f"{os.path.splitext(os.path.basename(file_path))[0][:27]}.yaml"
    else:
        return f"{os.path.basename(file_path).replace('_BOA.tif', '.yaml')}"
