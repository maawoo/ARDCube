import uuid
import yaml
import os
import re
from pyproj import Transformer
import rasterio
import rasterio.features
import shapely.affinity
import shapely.geometry
import shapely.ops


def _get_rasters(dir_path, regex=None):

    tifpaths = []

    if regex is None:
        raise NameError("Please provide a regex term to search for files!")

    for root, dirs, files in os.walk(dir_path):
        for name in files:
            d = str(root) + "/" + str(name)
            if re.search(regex, d):
                tifpaths.append(d)

    return tifpaths


def _get_time_meta(raster, n_meta):

    # Load meta.txt
    meta = raster[0:-n_meta] + "META.txt"
    meta = open(meta, 'r')
    meta_lines = meta.read().splitlines()

    # Get necessary information
    acq_date = meta_lines[4].split('=')
    scan_time = meta_lines[5].split('=')
    creation_time = meta_lines[10].split('=')

    acq_date = acq_date[1].replace(" ", "")
    scan_time = scan_time[1].replace(" ", "")
    creation_dt = creation_time[1].replace(" ", "")

    # Define time extent
    from_dt = acq_date + " 00" + scan_time[2:]
    center_dt = acq_date + " " + scan_time
    to_dt = acq_date + " 23" + scan_time[2:]

    return creation_dt, from_dt, center_dt, to_dt


def _valid_region(images, mask_value=None):
    mask = None
    for fname in images:
        # ensure formats match
        with rasterio.open(str(fname), 'r') as ds:
            transform = ds.transform
            img = ds.read(1)

            if mask_value is not None:
                new_mask = img & mask_value == mask_value
            else:
                new_mask = img != 0

            if mask is None:
                mask = new_mask
            else:
                mask |= new_mask

    shapes = rasterio.features.shapes(mask.astype('uint8'), mask=mask)
    shape = shapely.ops.unary_union([shapely.geometry.shape(shape) for shape, val in shapes if val == 1])
    type(shapes)
    # convex hull
    geom = shape.convex_hull

    # buffer by 1 pixel
    geom = geom.buffer(1, join_style=3, cap_style=3)

    # simplify with 1 pixel radius
    geom = geom.simplify(1)

    # intersect with image bounding box
    geom = geom.intersection(shapely.geometry.box(0, 0, mask.shape[1], mask.shape[0]))

    # transform from pixel space into CRS space
    geom = shapely.affinity.affine_transform(geom, (transform.a, transform.b, transform.d,
                                                    transform.e, transform.xoff, transform.yoff))

    output = shapely.geometry.mapping(geom)

    return geom


def _conv_coord(x_ext, y_ext, crs_in=None, crs_out=None):
    """Convert x- and y-extents into converted (lat/lon) ul & lr coordinates.

    x_ext = tuple (min, max)
    y_ext = tuple (min, max)
    crs_in = Original CRS
    crs_out = CRS to convert into. Default is EPSG:4326, which is necessary for ODC yaml files.

    output: ul & lr coordinates in lat/lon
    """
    if crs_in is None:
        raise NameError("Please provide input CRS!")
    if crs_out is None:
        crs_out = 'EPSG:4326'

    transformer = Transformer.from_crs(crs_in, crs_out, always_xy=True)

    ul = transformer.transform(x_ext[0], y_ext[1])
    lr = transformer.transform(x_ext[1], y_ext[0])

    return ul, lr


def prepare_dataset(tifpaths, n_meta, exr_string=None, prod_name=None):

    documents = {}
    for raster in tifpaths:

        dir_name = os.path.dirname(raster)

        n_yaml = n_meta - 4
        yaml_name = os.path.basename(raster)
        if exr_string is None:
            yaml_name = yaml_name[0:-n_yaml] + ".yaml"
        else:
            yaml_name = yaml_name[0:-n_yaml] + exr_string + ".yaml"

        # Access meta.txt and extract time information
        creation_dt, from_dt, center_dt, to_dt = _get_time_meta(raster, n_meta)

        # Load rasters
        ras = rasterio.open(raster)

        # Define CRS and extent
        crs_in = str(ras.crs)
        crs_out = 'EPSG:4326'
        x_ext = (ras.bounds[0], ras.bounds[2])
        y_ext = (ras.bounds[1], ras.bounds[3])

        # Convert extent to lat/lon
        ul, lr = _conv_coord(x_ext, y_ext, crs_in, crs_out)

        yaml_content = {
            'id': str(uuid.uuid4()),
            'creation_dt': creation_dt,

            'format': {'name': prod_name},
            'instrument': {'name': 'msi'},
            'platform': {'code': 's2ab'},

            'extent': {
                'coord': {
                    'ul': {'lat': ul[1], 'lon': ul[0]},
                    'ur': {'lat': ul[1], 'lon': lr[0]},
                    'll': {'lat': lr[1], 'lon': ul[0]},
                    'lr': {'lat': lr[1], 'lon': lr[0]}
                },
                'from_dt': from_dt,
                'center_dt': center_dt,
                'to_dt': to_dt
            },

            'grid_spatial': {
                'projection': {
                    'geo_ref_points': {
                        'ul': {'x': x_ext[0], 'y': y_ext[1]},
                        'ur': {'x': x_ext[1], 'y': y_ext[1]},
                        'll': {'x': x_ext[0], 'y': y_ext[0]},
                        'lr': {'x': x_ext[1], 'y': y_ext[0]}
                    },
                    'spatial_reference': str(ras.crs)
                }
            },

            'image': {
                'bands': {
                    'cir': {
                        'path': os.path.basename(raster),
                        'type': 'byte',
                        'band': 1,
                        'cell_size': 10.0
                    }
                }
            },

            'lineage': {'source_datasets': {}},
        }

        documents[yaml_name] = {'dir_name': dir_name,
                                'yaml_content': yaml_content}

    return documents


def main(dir_path, regex=None, n_meta=None, exr_string=None, prod_name=None):

    if prod_name is None:
        raise NameError("Please provide a product name!")

    # Search for rasters
    if regex is None:
        regex = r'.*\_ICIR.TIF'

    tifpaths = _get_rasters(dir_path, regex=regex)

    if n_meta is None:
        n_meta = 8

    # Create yaml dict
    if exr_string is None:
        documents = prepare_dataset(tifpaths=tifpaths, n_meta=n_meta, prod_name=prod_name)
    else:
        documents = prepare_dataset(tifpaths=tifpaths, n_meta=n_meta, exr_string=exr_string, prod_name=prod_name)

    for key in documents.keys():

        yaml_name = key
        yaml_path = documents[key]['dir_name'] + "/" + yaml_name
        yaml_content = documents[key]['yaml_content']

        with open(yaml_path, 'w') as stream:
            yaml.dump(yaml_content, stream, sort_keys=False)


##############################################################

dir_path = "/datacube/original_data/2_sen2_counpix/data/"


#############
# 1 (normal)
prod_name = 'ICIR_PIC_geotiff'

main(dir_path, prod_name=prod_name)

"""
#############
# 2 (deflate)
prod_name = 'ICIR_PIC_cog_d'
suffix = "_COG_deflate"
regex = r'.*\_ICIR_COG_deflate.TIF'
n = 20

main(dir_path, regex=regex, n_meta=n, exr_string=suffix, prod_name=prod_name)

#############
# 3 (zstd)
prod_name = 'ICIR_PIC_cog_z'
suffix = "_COG_zstd"
regex = r'.*\_ICIR_COG_zstd.TIF'
n = 17

main(dir_path, regex=regex, n_meta=n, exr_string=suffix, prod_name=prod_name)

"""