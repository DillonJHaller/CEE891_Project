'''
Code to sample Sentinel-1 data to shapefile points.
'''
import numpy as np
import rasterio
from rasterio.control import GroundControlPoint
from rasterio.transform import from_bounds
from rasterio.warp import transform_bounds
from affine import Affine
import geopandas as gpd
import pandas as pd
import os
from scipy.spatial import cKDTree
import s0_calibration as s0

def sample_sentinel_data(sentinel_vv_path, sentinel_vh_path, points_shapefile):
    """Sample Sentinel-1 VV and VH data at points from a shapefile.

    Parameters
    ----------
    sentinel_vv_path : str
        Path to the Sentinel-1 VV band GeoTIFF.
    sentinel_vh_path : str
        Path to the Sentinel-1 VH band GeoTIFF.
    points_shapefile : str
        Path to the shapefile containing points to sample.

    Returns
    -------
    pd.DataFrame
        DataFrame with sampled VV and VH values at each point.
    """
    # Load points from shapefile
    gdf = gpd.read_file(points_shapefile)
    print(f"Shapefile CRS: {gdf.crs}")
    print(f"Sample point: ({gdf.geometry.iloc[0].x}, {gdf.geometry.iloc[0].y})")
    
    # Reproject points to lat/long
    gdf = gdf.to_crs(epsg=4326)
    print(f"Reprojected sample point: ({gdf.geometry.iloc[0].x}, {gdf.geometry.iloc[0].y})")
    
    # Open VV raster to get metadata
    with rasterio.open(sentinel_vv_path) as vv_src:
        raster_crs = vv_src.crs
        vv_transform = vv_src.transform
        vv_gcps, vv_gcp_crs = vv_src.get_gcps()
        raster_width = vv_src.width
        raster_height = vv_src.height
        
        print(f"Raster CRS: {raster_crs}")
        print(f"Raster transform: {vv_transform}")
        print(f"Raster shape: ({raster_height}, {raster_width})")
        print(f"Raster has {len(vv_gcps)} GCPs with CRS: {vv_gcp_crs}")
        
        # If raster has GCPs, build a coordinate transformer from them
        gcp_transformer = None
        if vv_gcps and len(vv_gcps) >= 3:
            # Use GCPs to create a polynomial fit (via cKDTree nearest neighbor + linear interpolation)
            gcp_pixel_coords = np.array([(gcp.col, gcp.row) for gcp in vv_gcps])
            gcp_world_coords = np.array([(gcp.x, gcp.y) for gcp in vv_gcps])
            
            print(f"GCP pixel coords:\n{gcp_pixel_coords}")
            print(f"GCP world coords:\n{gcp_world_coords}")
            
            # Fit a simple 2D polynomial (order 1 = affine) from world to pixel
            # Using numpy polyfit: pixel = affine_matrix @ [world_x, world_y, 1]
            A = np.column_stack([gcp_world_coords[:, 0], gcp_world_coords[:, 1], np.ones(len(vv_gcps))])
            try:
                # Solve for pixel_col and pixel_row coefficients
                col_coeffs = np.linalg.lstsq(A, gcp_pixel_coords[:, 0], rcond=None)[0]
                row_coeffs = np.linalg.lstsq(A, gcp_pixel_coords[:, 1], rcond=None)[0]
                gcp_transformer = (col_coeffs, row_coeffs)
                print(f"GCP affine transformer fitted successfully")
            except Exception as e:
                print(f"Warning: Could not fit GCP transformer: {e}")
    
    # Function to convert world coordinates to pixel indices using GCPs or transform
    def world_to_pixel(lon, lat, vv_src):
        if gcp_transformer is not None:
            col_coeffs, row_coeffs = gcp_transformer
            col = col_coeffs[0] * lon + col_coeffs[1] * lat + col_coeffs[2]
            row = row_coeffs[0] * lon + row_coeffs[1] * lat + row_coeffs[2]
            return col, row
        else:
            # Fall back to affine transform (pixel space)
            return vv_src.index(lon, lat)
    
    # Prepare lists to hold sampled values
    vv_values = []
    vh_values = []
    valid_count = 0
    
    # Sample VV band
    with rasterio.open(sentinel_vv_path) as vv_src:
        vv_data = vv_src.read(1)
        for i, geom in enumerate(gdf.geometry):
            try:
                col, row = world_to_pixel(geom.x, geom.y, vv_src)
                # Check bounds
                col_int = int(np.round(col))
                row_int = int(np.round(row))
                if 0 <= col_int < raster_width and 0 <= row_int < raster_height:
                    vv_values.append(vv_data[row_int, col_int])
                    valid_count += 1
                else:
                    print(f"Point {i} out of bounds: pixel ({col_int}, {row_int})")
                    vv_values.append(np.nan)
            except Exception as e:
                print(f"Warning: Could not sample VV at point {i} ({geom.x}, {geom.y}): {e}")
                vv_values.append(np.nan)
    
    # Sample VH band
    with rasterio.open(sentinel_vh_path) as vh_src:
        vh_data = vh_src.read(1)
        for i, geom in enumerate(gdf.geometry):
            try:
                col, row = world_to_pixel(geom.x, geom.y, vh_src)
                col_int = int(np.round(col))
                row_int = int(np.round(row))
                if 0 <= col_int < raster_width and 0 <= row_int < raster_height:
                    vh_values.append(vh_data[row_int, col_int])
                else:
                    vh_values.append(np.nan)
            except Exception as e:
                print(f"Warning: Could not sample VH at point {i} ({geom.x}, {geom.y}): {e}")
                vh_values.append(np.nan)
    
    print(f"Successfully sampled {valid_count}/{len(gdf)} points")
    
    # Create DataFrame with results
    df = pd.DataFrame({
        'ID': range(len(gdf)),
        'LTPC': gdf['LTPC'].values,  # Label column
        'Date': [sentinel_vv_path.split('-')[4]] * len(gdf),  # Extract date from filename
        'VV': vv_values,
        'VH': vh_values
    })
    
    # Don't drop NaNs yet; we want to see what's happening
    print(f"DataFrame before dropping NaNs:\n{df.head()}")
    print(f"VV range: {df['VV'].min()} to {df['VV'].max()}")
    print(f"VH range: {df['VH'].min()} to {df['VH'].max()}")
    
    df = df.dropna().reset_index(drop=True)

    # Print a warning if there are no rows after dropping NaNs
    if df.empty:
        print(f"Warning: No valid samples found for VV: {sentinel_vv_path} and VH: {sentinel_vh_path}.")

    return df

#Shapefile is from another project
points_shapefile = "C:\\Users\\hallerdi\\Documents\\Thesis_Work\\cmse802_project\\data\\Train_Test_Points\\training_points.shp"
#Traverse Sentinel-1 data directories and sample each pair of VV/VH bands
data_root = "D:\\Sentinel1_Data"
all_samples = []
for root, dirs, files in os.walk(data_root):
    vv_band_path = None
    vh_band_path = None

    for file in files:
        if file.endswith('001.tiff'):
            vv_band_path = os.path.join(root, file)
        elif file.endswith('002.tiff'):
            vh_band_path = os.path.join(root, file)

    if vv_band_path and vh_band_path:
        print(f"Sampling data from:\nVV: {vv_band_path}\nVH: {vh_band_path}")
        df_samples = sample_sentinel_data(vv_band_path, vh_band_path, points_shapefile)
        all_samples.append(df_samples)

#Combine all samples into a single DataFrame
final_df = pd.concat(all_samples, ignore_index=True)
#Calculate RVI and add as new column
final_df['RVI'] = (4.0 * final_df['VH']) / (final_df['VV'] + final_df['VH'])

#Save to CSV
output_csv_path = "data\\sentinel1_samples.csv"
final_df.to_csv(output_csv_path, index=False)