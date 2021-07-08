### General
- You don't need to use any ' ' or " " for the parameters. 
  Using quotation marks could actually result in parameters not being understood by commands they're parsed to.
- Download / Data availability
    - Optical 
        - Sentinel-2 A/B and Landsat 4, 5, 7, 8
        - From Google Cloud Storage using FORCE (more information 
          [here](https://force-eo.readthedocs.io/en/latest/howto/level1-csd.html#))
        - Creation of a `.boto` file via `gsutil` necessary (currently Sentinel-2 A/B only)! See link above for details.

    - SAR: 
        - Sentinel-1 A/B
        - From Copernicus Open Access Hub (OAH) using sentinelsat (more information 
          [here](https://github.com/sentinelsat/sentinelsat))
        - OAH account credentials necessary!
- ...

---
### `settings.prm`

- **[GENERAL]**
    - **DataDirectory**  
       Example: `/path/to/your/data/directory`  
       Main directory that will be used for downloaded and processed datasets, metadata, logs, auxillary data 
       (e.g. DEM), etc. Any subdirectories that are necessary for the processing for example, will be created 
       automatically.

    - **AOI**  
      Example: `my_aoi.geojson` or `/path/to/my_aoi.geojson`  
      Can either be a filename, or a full path to the AOI file. If only a filename is provided, it is assumed to be 
      located in the subdirectory `/DataDirectory/misc/aoi` (recommended!). In this case you should of course be 
      proactive in creating this subdirectory and moving your file there. GeoJSON, GPKG and Shapefile should all work.  
      http://geojson.io provides a convenient way to create a GeoJSON file for your AOI.

    

- **[DOWNLOAD]**
    - **TimespanMin, TimespanMax**   
      Example: `20200101`, `20200601`  
      Sensors: Optical and SAR  
      Minimum and maximum date to define a timespan used to query optical and SAR data.
    - **OpticalCloudCoverRangeMin, OpticalCloudCoverRangeMax**  
      Example: `0`, `75`  
      Sensors: Optical   
      Minimum and maximum cloud cover (%) used to query optical data.
    - **SAROrbitDirection:**  
      Valid options: `asc`, `desc` or `both`  
      Sensors: SAR   
      Orbit direction (ascending and/or descending) used to query SAR data.
    - **CopernicusUser, CopernicusPassword:**  
      Sensors: SAR   
      As already mentioned in the section 'General notes', Sentinel-1 data will be downloaded from Copernicus Open 
      Access Hub using the Python package sentinelsat. The account credentials can be provided with these parameters. 
      Be aware that access via the API might not be available immediately after account creation and also after any 
      changes to the account were made! 
      (more information [here](https://scihub.copernicus.eu/twiki/do/view/SciHubWebPortal/APIHubDescription?TWIKISID=00a8b7c34c1570fb4a021e5eea7482d4))
    

- **[PROCESSING]**  

    - **DEM:**  
      Example / Valid options: `my_dem.tif`, `/path/to/my_dem.tif` or `srtm`  
      Sensors: Optical and SAR  
      Can either be a filename, or a full path to the DEM (Digital Elevation Model) file. If only a filename is 
      provided, it is assumed to be located in the subdirectory `/DataDirectory/misc/dem` (recommended!). 
      In this case you should of course be proactive in creating this subdirectory and moving your file there.
      Another valid option is `srtm`. This will automatically create a 1 arc-second (~30m spatial resolution) SRTM DEM 
      for the area of interest and use the recommended subdirectory mentioned above as the output directory.  
      Relevant FORCE documentation on how to prepare a DEM: 
      [Here](https://force-eo.readthedocs.io/en/latest/howto/dem.html)
    - **DEM_NoData:**  
      Example: `-9999`  
      Sensors: Optical and SAR  
      No data value of your DEM. This parameter will be ignored if `srtm` was chosen above.
    - **NPROC, NTHREAD:**  
      [Mandatory to read!](https://force-eo.readthedocs.io/en/latest/howto/l2-ard.html#parallel-processing)
      
---
### `/force`

To better understand how level-2 ARD data is processed with FORCE, you should take a look into the 
[documentation](https://force-eo.readthedocs.io/en/latest/howto/l2-ard.html#). 
You can see which parameters are chosen as default in the file `/force/FORCE_params__template.prm` and change them
if you want (see also notes inside the file!). Parameter descriptions are also provided in the file
`/force/FORCE_params__description.prm`. This file will not be queried for any processing and is really only there 
to provide additional parameter descriptions.  

---
### `/odc`

https://datacube-core.readthedocs.io/en/latest/ops/product.html

