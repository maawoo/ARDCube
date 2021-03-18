import os


def get_aoi_path(settings):
    """Gets the full path to the AOI file based on settings."""

    if os.path.isdir(settings['GENERAL']['AOI']):
        aoi_path = settings['GENERAL']['AOI']
    else:
        aoi_path = os.path.join(settings['GENERAL']['DataDirectory'], 'misc/aoi', settings['GENERAL']['AOI'])

    return aoi_path
