import io
import os
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import box, Point
import json
import time  # Import time module for timing

PATH_WELL = "PERMIAN BASIN Well Headers.CSV"
PATH_TRAIN_IMAGE = "test_download"
N_EXAMPLE = None # None creates labels for all; define dataset size

def main(well_header=PATH_WELL, download_folder=PATH_TRAIN_IMAGE, n_example=100):
    # Start the timer
    start_time = time.time()

    os.makedirs(download_folder, exist_ok=True)

    if n_example is not None:
        wells_df = pd.read_csv(well_header).head(n_example)
    else:
        wells_df = pd.read_csv(well_header)

    # create basin bounding box
    min_lat = wells_df['Surface Hole Latitude (WGS84)'].min()
    max_lat = wells_df['Surface Hole Latitude (WGS84)'].max()
    min_lon = wells_df['Surface Hole Longitude (WGS84)'].min()
    max_lon = wells_df['Surface Hole Longitude (WGS84)'].max()

    # Define step sizes for 5km x 5km grid in degrees (approximation for simplicity)
    lat_step = 0.045  # Roughly 5km in latitude
    lon_step = 0.045  # Roughly 5km in longitude

    # Generate grid cells
    grid_cells = []
    for lat in np.arange(min_lat, max_lat, lat_step):
        for lon in np.arange(min_lon, max_lon, lon_step):
            # Create a 5km x 5km bounding box for each grid cell
            grid_cells.append(box(lon, lat, lon + lon_step, lat + lat_step))

    print(f"---- A total of {len(grid_cells)} grid cells created. ----")

    well_polygons = []
    for _, row in wells_df.iterrows():
        lat, lon = row['Surface Hole Latitude (WGS84)'], row['Surface Hole Longitude (WGS84)']
        # Convert 50m to degrees approximately for both latitude and longitude
        lat_offset = 0.00045  # Approx 50m in latitude
        lon_offset = 0.00045  # Approx 50m in longitude
        well_polygon = box(lon - lon_offset, lat - lat_offset,
                           lon + lon_offset, lat + lat_offset)
        well_polygons.append(well_polygon)

    print(f"---- A total of {len(well_polygons)} well polygons created. ----")

    # Prepare the COCO-style annotation structure
    annotations = []
    images = []
    annotation_id = 0
    category_id = 1  # Category ID for wells

    # Initialize a list to hold DenseNet label data
    densenet_labels = []

    for grid_id, grid_cell in enumerate(grid_cells):
        # Get the top-left corner coordinates of the grid cell for naming
        top_left_lat, top_left_lon = grid_cell.bounds[3], grid_cell.bounds[0]

        # Format the filename using the latitude and longitude of the grid cell's top-left corner
        image_filename = f"{download_folder}/{top_left_lat:.7f}_{top_left_lon:.7f}.jpg"

        # Check if any well polygon is within the grid cell
        wells_in_cell = [
            well for well in well_polygons if well.intersects(grid_cell)]

        # Define the bounding box for the grid cell in COCO format [x_min, y_min, width, height]
        grid_bbox = [grid_cell.bounds[0], grid_cell.bounds[1],
                     grid_cell.bounds[2] - grid_cell.bounds[0],  # width
                     grid_cell.bounds[3] - grid_cell.bounds[1]]  # height

        # Add image information for this grid cell, including the bounding box
        images.append({
            "id": grid_id,
            "file_name": image_filename,
            "width": 1024,  # Example width in pixels
            "height": 1024,  # Example height in pixels
            "bbox": grid_bbox
        })

        # Add annotation for each well in this grid cell
        for well in wells_in_cell:
            x_min, y_min, x_max, y_max = well.bounds
            annotations.append({
                "id": annotation_id,
                "image_id": grid_id,
                "category_id": category_id,
                "bbox": [x_min, y_min, x_max - x_min, y_max - y_min],
                "area": (x_max - x_min) * (y_max - y_min),
                "iscrowd": 0
            })
            annotation_id += 1
        
        # DenseNet label creation: Use top-left corner coordinates, count wells, and label
        well_count = len(wells_in_cell)
        label = 1 if well_count > 0 else 0

        # Print message indicating the number of wells in the grid cell
        if well_count > 1:
            print(
                f"-- Grid cell {grid_id} ({top_left_lat:.7f}, {top_left_lon:.7f}) contains {well_count} wells. --")

        densenet_labels.append({
            "lat": top_left_lat,
            "lon": top_left_lon,
            "label": label,
            "count": well_count,
            "file_path": image_filename
        })

    # Define the COCO-format data structure
    coco_format = {
        "images": images,
        "annotations": annotations,
        "categories": [
            {"id": category_id, "name": "well"}
        ]
    }

    # Save the COCO-format data to a JSON file
    output_path = "COCO_labels.json"
    with open(output_path, "w") as f:
        json.dump(coco_format, f)

    print(f"COCO labels saved to {output_path}")

    # Create and save the DenseNet labels DataFrame
    densenet_df = pd.DataFrame(densenet_labels)
    densenet_output_path = "DenseNet_labels.csv"
    densenet_df.to_csv(densenet_output_path, index=False)
    print(f"DenseNet labels saved to {densenet_output_path}")

    # End the timer and print the elapsed time
    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Program completed in {elapsed_time:.2f} seconds.")


if __name__ == "__main__":
    # Pass the desired download folder when calling main
    main(well_header=PATH_WELL, download_folder=PATH_TRAIN_IMAGE, n_example=N_EXAMPLE)
