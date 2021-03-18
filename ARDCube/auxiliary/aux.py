import os


def get_aoi_path(settings):
    """Gets the full path to the AOI file based on settings."""

    if os.path.isfile(settings['GENERAL']['AOI']):
        ## Is full path already and file exists!
        aoi_path = settings['GENERAL']['AOI']
    else:
        ## Is filename only, so it is assumed to be located in the subdirectory '/DataDirectory/misc/aoi'
        ## as described in settings.prm!
        aoi_path = os.path.join(settings['GENERAL']['DataDirectory'], 'misc/aoi',
                                settings['GENERAL']['AOI'])

        ## Check if the file actually exists...
        if not os.path.isfile(aoi_path):
            raise FileNotFoundError(f"{aoi_path} does not exist! \n"
                                    f"Please check your settings.prm for correct input of field 'AOI'!")

    return aoi_path


def check_sat_settings(settings):
    """Creates a dictionary based on which satellite fields were set to True in settings file."""

    sat_dict = {'Sentinel1': ['S1', '-'],
                'Sentinel2': ['S2', 'S2A,S2B'],
                'Landsat8': ['L8', 'LC08']}

    dict_out = {}
    for sat in list(sat_dict.keys()):
        if settings.getboolean(sat):

            s_full = sat
            s_short = sat_dict[sat][0]
            force_abbr = sat_dict[sat][1]
            out_dir = os.path.join(settings['GENERAL']['DataDirectory'], f"level-1/{s_short}")

            dict_out[s_full] = [s_short, force_abbr, out_dir]

            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

    return dict_out
