import io
import os
import pandas as pd  # Import pandas to read the CSV
import numpy as np
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from PIL import Image

# Your Sentinel Hub client credentials
CLIENT_ID = 'd7f7b946-16c7-4d7b-ac9d-9fa8c5a775e4'
CLIENT_SECRET = 'P75SqYQF0tPvX73O6ocgc4SELvWdLMda'


def authenticate(client_id, client_secret):
    """
    Authenticate with Sentinel Hub and return an OAuth2 session.
    """
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(
        token_url='https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token',
        client_secret=client_secret,
        include_client_id=True
    )
    return oauth, token


def create_bbox_from_center(lon, lat, box_size_m=5000):
    """
    Create a bounding box (bbox) given the center coordinates.
    
    Parameters:
        lon (float): Longitude of the center point.
        lat (float): Latitude of the center point.
        box_size_m (int): Size of the box in meters (default: 5000 meters).
    
    Returns:
        list: BBox in the format [min_lon, min_lat, max_lon, max_lat]
    """
    meters_to_deg_lat = box_size_m / 111320.0  # 1 degree latitude ~ 111.32 km
    meters_to_deg_lon = box_size_m / (111320.0 * abs(np.cos(np.radians(lat))))

    min_lon = lon - meters_to_deg_lon / 2
    max_lon = lon + meters_to_deg_lon / 2
    min_lat = lat - meters_to_deg_lat / 2
    max_lat = lat + meters_to_deg_lat / 2

    return [min_lon, min_lat, max_lon, max_lat]


def download_image(oauth, bbox, start_date, end_date, save_path, evalscript):
    """
    Download a satellite image and save it as a PNG.
    """
    url_request = 'https://services.sentinel-hub.com/api/v1/process'
    headers_request = {
        "Authorization": f"Bearer {oauth.token['access_token']}"
    }

    json_request = {
        'input': {
            'bounds': {
                'bbox': bbox,
                'properties': {
                    'crs': 'http://www.opengis.net/def/crs/OGC/1.3/CRS84'
                }
            },
            'data': [
                {
                    'type': 'S2L2A',
                    'dataFilter': {
                        'timeRange': {
                            'from': f'{start_date}T00:00:00Z',
                            'to': f'{end_date}T23:59:59Z'
                        },
                        'mosaickingOrder': 'leastCC',
                    },
                }
            ]
        },
        'output': {
            'width': 1024, # Increase width for higher resolution 1024, 2048
            'height': 1024, # Increase width for higher resolution
            'responses': [
                {
                    'identifier': 'default',
                    'format': {
                        'type': 'image/png',
                    }
                }
            ]
        },
        'evalscript': evalscript
    }

    response = oauth.post(
        url_request, headers=headers_request, json=json_request)

    if response.status_code == 200:
        img = Image.open(io.BytesIO(response.content))
        img.save(save_path)
        print(f"Image saved as {save_path}")
    else:
        print(f"Failed to fetch image. Status code: {response.status_code}")
        print(f"Response content: {response.content}")


def read_coordinates_from_csv(file_path):
    """
    Read the coordinates from the provided CSV file.
    
    Parameters:
        file_path (str): Path to the CSV file.

    Returns:
        DataFrame: Pandas DataFrame with 'surface lon' and 'surface lat' columns.
    """
    df = pd.read_csv(file_path)
    if 'Surface Hole Longitude (WGS84)' not in df.columns or 'Surface Hole Latitude (WGS84)' not in df.columns:
        raise ValueError(
            "CSV must contain 'Surface Hole Longitude (WGS84)' and 'Surface Hole Latitude (WGS84)' columns.")
    return df[['Surface Hole Longitude (WGS84)', 'Surface Hole Latitude (WGS84)']]


def main():
    # Ensure the downloads directory exists
    os.makedirs("downloads", exist_ok=True)

    # Read the CSV file with coordinates
    # Path to the uploaded CSV file
    csv_file = "PERMIAN BASIN Well Headers.CSV"
    coordinates_df = read_coordinates_from_csv(csv_file)

    # Define the date range
    start_date = "2024-06-01"
    end_date = "2024-08-31"

    # Sentinel Hub Evalscript to define the bands
    evalscript = """
    //VERSION=3
    function setup() {
      return {
        input: ["B02", "B03", "B04"],
        output: {
          bands: 3,
          sampleType: "AUTO" // default value - scales the output values from [0,1] to [0,255].
        }
      }
    }

    function evaluatePixel(sample) {
      return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02]
    }
    """

    # Authenticate and get OAuth session
    oauth, token = authenticate(CLIENT_ID, CLIENT_SECRET)

    # Loop through each coordinate in the CSV and download the image
    #for index, row in coordinates_df.iterrows():
    for index, row in coordinates_df.head(10).iterrows(): # test - run only 10 examples

        lon, lat = row['Surface Hole Longitude (WGS84)'], row['Surface Hole Latitude (WGS84)']
        save_path = f"downloads/{lon}_{lat}.png"

        # Create the bounding box
        bbox = create_bbox_from_center(lon, lat, box_size_m=5000)

        # Download and save the image
        download_image(oauth, bbox, start_date,
                       end_date, save_path, evalscript)


if __name__ == "__main__":
    main()
