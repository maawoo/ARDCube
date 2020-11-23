import nasa_hls

# returns list
urls_datasets = nasa_hls.get_available_datasets(products=["L30", "S30"],
                                                years=[2018],
                                                tiles=["32UPB"])
print("Number of datasets: ", len(urls_datasets))
print("First datasets:\n -", "\n - ".join(urls_datasets[:3]))
print("Last datasets:\n -", "\n - ".join(urls_datasets[-3:]))

df_datasets = nasa_hls.dataframe_from_urls(urls_datasets).head(3)

""" Subset
df_datasets["year"] = df_datasets.date.dt.year
df_datasets["month"] = df_datasets.date.dt.month
df_datasets["day"] = df_datasets.date.dt.day

ls_s2_aquisitions_same_day = df_datasets.duplicated(subset=["tile", "year", "month", "day"], keep=False)

df_download = df_datasets[(ls_s2_aquisitions_same_day) & \
                          #(df_datasets["tile"] == "32UNU") & \
                          (df_datasets["date"].dt.year == 2018) & \
                          (df_datasets["date"].dt.month == 4) ]
df_download = df_download.sort_values(["date", "tile", "product"])
df_download
"""

nasa_hls.download_batch(dstdir="./xxx_uncontrolled_hls/downloads",
                        datasets=df_datasets,
                        version="v1.4",
                        overwrite=False)

