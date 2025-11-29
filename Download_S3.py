import asf_search as asf
import os
from shapely.geometry import box
from datetime import date
import geopandas as gpd

#Read in AOI shapefile
gdf = gpd.read_file("C:\\Users\\hallerdi\\Documents\\Thesis_Work\\Sentinel_Data\\Sentinel_Tiles\\Sentinel_Tiles.shp")
bounds = gdf.total_bounds  # minx, miny, maxx, maxy
gdf_bounds = gpd.GeoSeries([box(*bounds)], crs=gdf.crs)
wkt = gdf_bounds.to_wkt().values.tolist()[0]

#Search for Sentinel-1 data in AOI
results = asf.search(
    platform = asf.PLATFORM.SENTINEL1,
    processingLevel = [asf.PRODUCT_TYPE.GRD_HD],
    start = date(2024, 1, 1),
    end = date(2024, 12, 31),
    intersectsWith = wkt
)
print(f'Total Images Found: {len(results)}')
metadata = results.geojson()

results.download(
    path = ("D:\\Sentinel1_Data"),
    processes = 10
)

