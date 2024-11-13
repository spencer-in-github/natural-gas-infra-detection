import os
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import box
import json
import time

PATH_WELL = "PERMIAN BASIN Well Headers.CSV"
PATH_TRAIN_IMAGE = "test_download"
N_EXAMPLE = None  # None creates labels for all; define dataset size

# Define conversion constants (approximate)
KM_TO_DEG_LAT = 1 / 111  # 1 degree latitude ≈ 111 km
# 1 degree longitude ≈ 111 km at the equator (adjusted by latitude)
KM_TO_DEG_LON = 1 / 111


def main(well_header=PATH_WELL, download_folder=PATH_TRAIN_IMAGE, n_example=100, image_length_km=5):
    # Start the timer
    start_time = time.time()

    os.makedirs(download_folder, exist_ok=True)

    # Load wells data and limit rows if n_example is specified
    wells_df = pd.read_csv(well_header)
    if n_example is not None:
        wells_df = wells_df.head(n_example)

    # Create a GeoDataFrame with well locations as 50m x 50m boxes
    wells_gdf = gpd.GeoDataFrame(
        wells_df,
        geometry=[
            box(lon - 0.00045, lat - 0.00045, lon + 0.00045, lat + 0.00045)
            for lat, lon in zip(
                wells_df['Surface Hole Latitude (WGS84)'],
                wells_df['Surface Hole Longitude (WGS84)']
            )
        ],
        crs="EPSG:4326"
    )

    # Create basin bounding box
    min_lat = wells_df['Surface Hole Latitude (WGS84)'].min()
    max_lat = wells_df['Surface Hole Latitude (WGS84)'].max()
    min_lon = wells_df['Surface Hole Longitude (WGS84)'].min()
    max_lon = wells_df['Surface Hole Longitude (WGS84)'].max()

    # Calculate step sizes based on image length in kilometers
    lat_step = image_length_km * KM_TO_DEG_LAT
    lon_step = image_length_km * KM_TO_DEG_LON

    # Generate grid cells and their GeoDataFrame
    grid_cells = []
    grid_ids = []
    lat_lons = []
    for lat in np.arange(min_lat, max_lat, lat_step):
        for lon in np.arange(min_lon, max_lon, lon_step):
            grid_cells.append(box(lon, lat, lon + lon_step, lat + lat_step))
            grid_ids.append(f"{lat:.7f}_{lon:.7f}")
            lat_lons.append((lat, lon))

    grid_gdf = gpd.GeoDataFrame(
        {"grid_id": grid_ids, "geometry": grid_cells, "lat_lon": lat_lons},
        crs="EPSG:4326"
    )

    print(
        f"---- A total of {len(grid_gdf)} grid cells created with a box size of {image_length_km} km ----")

    # Spatial join to find wells in each grid cell
    wells_in_cells = gpd.sjoin(
        wells_gdf, grid_gdf, how="left", predicate="intersects")

    wells_in_cells.to_csv("wells_in_cells.csv")

    # Prepare data structures for COCO and DenseNet labels
    annotations = []
    images = []
    densenet_labels = []
    annotation_id = 0
    category_id = 1

    # Iterate over grid cells and assign wells to COCO/DenseNet
    for grid_id, grid_row in grid_gdf.iterrows():
        # Get top-left corner lat/lon for filename
        lat, lon = grid_row["lat_lon"]
        file_name = f"{download_folder}/{lat:.7f}_{lon:.7f}.jpg"

        # Find wells in the current grid cell
        cell_wells = wells_in_cells[wells_in_cells["grid_id"]
                                    == grid_row["grid_id"]]
        well_count = len(cell_wells)
        label = 1 if well_count > 0 else 0  # Set label to 0 if no wells are found

        # Print the well count if there are wells in the grid cell
        if well_count > 1:
            print(f"-- {well_count} wells in grid {lat:.7f} {lon:.7f} --")
        elif well_count == 0:
            print(f"------- No wells in grid {lat:.7f} {lon:.7f} ------")

        # Append image information for COCO
        images.append({
            "id": grid_id,
            "file_name": file_name,
            "width": 1024,
            "height": 1024,
            "bbox": [grid_row.geometry.bounds[0], grid_row.geometry.bounds[1],
                     grid_row.geometry.bounds[2] - grid_row.geometry.bounds[0],
                     grid_row.geometry.bounds[3] - grid_row.geometry.bounds[1]]
        })

        # Append well annotations for COCO if there are wells in the grid cell
        if well_count > 0:
            for _, well_row in cell_wells.iterrows():
                x_min, y_min, x_max, y_max = well_row.geometry.bounds
                annotations.append({
                    "id": annotation_id,
                    "image_id": grid_id,
                    "category_id": category_id,
                    "bbox": [x_min, y_min, x_max - x_min, y_max - y_min],
                    "area": (x_max - x_min) * (y_max - y_min),
                    "iscrowd": 0
                })
                annotation_id += 1

        # Append DenseNet label with label = 0 for grid cells without wells
        densenet_labels.append({
            "lat": lat,
            "lon": lon,
            "label": label,
            "count": well_count,
            "file_path": file_name
        })

    # Save COCO format
    coco_format = {
        "images": images,
        "annotations": annotations,
        "categories": [{"id": category_id, "name": "well"}]
    }
    with open("COCO_labels.json", "w") as f:
        json.dump(coco_format, f)
    print("COCO labels saved to COCO_labels.json")

    # Save DenseNet labels to CSV
    densenet_df = pd.DataFrame(densenet_labels)
    densenet_df.to_csv("DenseNet_labels.csv", index=False)
    print("DenseNet labels saved to DenseNet_labels.csv")

    # Print the elapsed time
    elapsed_time = time.time() - start_time
    # Calculate elapsed time in minutes and seconds
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)

    # Print the elapsed time in "X minutes and Y seconds" format
    print(f"Program completed in {minutes} minutes {seconds} seconds.")


if __name__ == "__main__":
    main(well_header=PATH_WELL, download_folder=PATH_TRAIN_IMAGE,
         n_example=N_EXAMPLE, image_length_km=5)
