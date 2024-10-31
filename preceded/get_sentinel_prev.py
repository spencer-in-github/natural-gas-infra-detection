import os
import numpy as np
import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
from shapely.geometry import Polygon
from datetime import datetime, timedelta
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from shapely.geometry import Polygon

# Copernicus API credentials
copernicus_user = "zhang99@stanford.edu"
copernicus_password = "RT/Qe43%Zkh!6VK"

# Sentinel-2 data collection
data_collection = "SENTINEL-2"

# WKT bounding box (example)
# ft = (
#     "POLYGON ((-100.42712657761632 31.469326431738068, "
#     "-100.4296877813848 31.469326431738068, "
#     "-100.4296877813848 31.466824830802423, "
#     "-100.42712657761632 31.466824830802423, "
#     "-100.42712657761632 31.469326431738068))"
# )


def create_wkt(lon, lat, length=10):
    """Create a n x n WKT polygon centered at the given longitude and latitude."""
    """Default to 10m x 10m."""
    # Approximate conversion: 1 degree latitude ≈ 111,320 meters
    # turn meters in degrees (~0.0000899 degrees)
    meters_to_degree = length / 111320.0

    # Adjust for the current latitude (longitude degrees shrink towards the poles)
    lon_adjusted = meters_to_degree / \
        abs(lat) if lat != 0 else meters_to_degree

    # Calculate the bounding box
    min_lon = lon - lon_adjusted / 2
    max_lon = lon + lon_adjusted / 2
    min_lat = lat - meters_to_degree / 2
    max_lat = lat + meters_to_degree / 2

    # Create a polygon using Shapely
    polygon = Polygon([
        (min_lon, min_lat),  # Bottom-left
        (max_lon, min_lat),  # Bottom-right
        (max_lon, max_lat),  # Top-right
        (min_lon, max_lat),  # Top-left
        (min_lon, min_lat)   # Close the polygon
    ])

    # Return the WKT representation of the polygon
    return polygon.wkt


# Example usage
lon, lat = -100.428, 31.468  # Example coordinates
ft = create_wkt(lon, lat)
print(ft)

# Set dates for query
date_string = "2024-01-02"
today = datetime.strptime(date_string, "%Y-%m-%d")
yesterday = today - timedelta(days=10)
today_string = today.strftime("%Y-%m-%d")
yesterday_string = yesterday.strftime("%Y-%m-%d")


def get_keycloak(username: str, password: str) -> str:
    """Authenticate and get Keycloak token."""
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    response = requests.post(
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data=data,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_tile_center(geometry):
    """Calculate the center (longitude, latitude) of the tile."""
    centroid = geometry.centroid
    return round(centroid.x, 6), round(centroid.y, 6)  # Longitude, Latitude


def download_tile(session, feat, save_dir):
    """Download a single tile and save it as a .npy file."""
    try:
        tile_id = feat["properties"]["Id"]
        geometry = feat["geometry"]
        lon, lat = get_tile_center(shape(geometry))  # Get center coordinates
        name = feat["properties"]["Name"]
        print(f"Downloading {name} (center: {lon}, {lat})...")

        # Construct download URL
        url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({tile_id})/$value"
        response = session.get(url, allow_redirects=False)

        # Handle redirects
        while response.status_code in (301, 302, 303, 307):
            url = response.headers["Location"]
            response = session.get(url, allow_redirects=False)

        # Final download
        file = session.get(url, stream=True)

        # Save the content as a numpy array in-memory
        data = np.frombuffer(BytesIO(file.content).read(), dtype=np.uint8)

        # Use lon_lat as filename
        npy_path = os.path.join(save_dir, f"{lon}_{lat}.npy")

        # Save as .npy file
        np.save(npy_path, data)
        print(f"Saved {name} as {npy_path}")

    except Exception as e:
        print(f"Error downloading tile {name}: {e}")


def download_all_tiles(productDF, save_dir="downloads"):
    """Download all tiles in parallel."""
    os.makedirs(save_dir, exist_ok=True)

    # Initialize session with Keycloak token
    session = requests.Session()
    keycloak_token = get_keycloak(copernicus_user, copernicus_password)
    session.headers.update({"Authorization": f"Bearer {keycloak_token}"})

    # Use ThreadPoolExecutor to parallelize downloads
    with ThreadPoolExecutor(max_workers=5) as executor:
        for feat in productDF.iterfeatures():
            executor.submit(download_tile, session, feat, save_dir)


def fetch_tiles():
    """Fetch available tiles based on the WKT polygon and date range."""
    url = (
        f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?"
        f"$filter=Collection/Name eq '{data_collection}' and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;{ft}') and "
        f"ContentDate/Start gt {yesterday_string}T00:00:00.000Z and "
        f"ContentDate/Start lt {today_string}T00:00:00.000Z&$count=True&$top=1000"
    )

    response = requests.get(url)
    response.raise_for_status()
    json_data = response.json()

    productDF = pd.DataFrame.from_dict(json_data["value"])

    if productDF.empty:
        print("No tiles found for the given query.")
        return None

    # Convert to GeoDataFrame and filter out L1C datasets
    productDF["geometry"] = productDF["GeoFootprint"].apply(shape)
    gdf = gpd.GeoDataFrame(productDF).set_geometry("geometry")
    gdf = gdf[~gdf["Name"].str.contains("L1C")]

    print(f"Total L2A tiles found: {len(gdf)}")
    gdf["identifier"] = gdf["Name"].str.split(".").str[0]
    return gdf


if __name__ == "__main__":
    # Fetch available tiles
    productDF = fetch_tiles()

    # If tiles are available, download them
    if productDF is not None:
        download_all_tiles(productDF)
