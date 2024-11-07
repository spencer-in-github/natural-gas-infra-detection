import io
import os
import pandas as pd
import numpy as np
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from PIL import Image

# Your Sentinel Hub client credentials
CLIENT_ID = 'd7f7b946-16c7-4d7b-ac9d-9fa8c5a775e4'
CLIENT_SECRET = 'P75SqYQF0tPvX73O6ocgc4SELvWdLMda'


def authenticate(client_id, client_secret):
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(
        token_url='https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token',
        client_secret=client_secret,
        include_client_id=True
    )
    return oauth, token


def create_bbox_from_center(lon, lat, box_size_m=5000):
    meters_to_deg_lat = box_size_m / 111320.0
    meters_to_deg_lon = box_size_m / (111320.0 * abs(np.cos(np.radians(lat))))

    min_lon = lon - meters_to_deg_lon / 2
    max_lon = lon + meters_to_deg_lon / 2
    min_lat = lat - meters_to_deg_lat / 2
    max_lat = lat + meters_to_deg_lat / 2

    return [min_lon, min_lat, max_lon, max_lat]


#def download_image(oauth, bbox, start_date, end_date, save_path, evalscript):
#    url_request = 'https://services.sentinel-hub.com/api/v1/process'
#    headers_request = {
#        "Authorization": f"Bearer {oauth.token['access_token']}"
#    }

#    json_request = {
#        'input': {
#            'bounds': {
#                'bbox': bbox,
#                'properties': {
#                    'crs': 'http://www.opengis.net/def/crs/OGC/1.3/CRS84'
#                }
#            },
#            'data': [
#                {
#                    'type': 'S2L2A',
#                    'dataFilter': {
#                        'timeRange': {
#                            'from': f'{start_date}T00:00:00Z',
#                            'to': f'{end_date}T23:59:59Z'
#                        },
#                        'mosaickingOrder': 'leastCC',
#                    },
#                }
#            ]
#        },
#        'output': {
#            'width': 1024,
#            'height': 1024,
#            'responses': [
#                {
#                    'identifier': 'default',
#                    'format': {
#                        'type': 'image/png',
#                    }
#                }
#            ]
#        },
#        'evalscript': evalscript
#    }

#    response = oauth.post(
#        url_request, headers=headers_request, json=json_request)

#    if response.status_code == 200:
#        img = Image.open(io.BytesIO(response.content))
#        img.save(save_path)
#        print(f"Image saved as {save_path}")
#    else:
#        print(f"Failed to fetch image. Status code: {response.status_code}")
#        print(f"Response content: {response.content}")

def download_image(oauth, client_id, client_secret, bbox, start_date, end_date, save_path, evalscript):
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
            'width': 1024,
            'height': 1024,
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

    try:
        response = oauth.post(url_request, headers=headers_request, json=json_request)
        
        # If the token is expired (401 Unauthorized), refresh the token and retry
        if response.status_code == 401:
            print("Token expired. Refreshing token...")
            # Refresh the token using the refresh token
            oauth.fetch_token(
                token_url='https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token',
                client_id=client_id,
                client_secret=client_secret,
                include_client_id=True
            )
            headers_request["Authorization"] = f"Bearer {oauth.token['access_token']}"  # Update the header with the new token

            # Retry the request after refreshing the token
            response = oauth.post(url_request, headers=headers_request, json=json_request)
            
            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content))
                img.save(save_path)
                print(f"Image saved as {save_path}")
            else:
                print(f"Failed to fetch image after token refresh. Status code: {response.status_code}")
                print(f"Response content: {response.content}")
        elif response.status_code == 200:
            # If the request is successful, save the image
            img = Image.open(io.BytesIO(response.content))
            img.save(save_path)
            print(f"Image saved as {save_path}")
        else:
            print(f"Failed to fetch image. Status code: {response.status_code}")
            print(f"Response content: {response.content}")
    except Exception as e:
        print(f"An error occurred: {e}")


def read_coordinates_from_csv(file_path):
    df = pd.read_csv(file_path)
    if 'Surface Hole Longitude (WGS84)' not in df.columns or 'Surface Hole Latitude (WGS84)' not in df.columns:
        raise ValueError(
            "CSV must contain 'Surface Hole Longitude (WGS84)' and 'Surface Hole Latitude (WGS84)' columns.")
    return df[['Surface Hole Longitude (WGS84)', 'Surface Hole Latitude (WGS84)']]


def generate_random_coordinates_outside_bbox(n, lon_min, lon_max, lat_min, lat_max):
    # Latitude range for Texas and New Mexico
    texas_nm_lat_range = (25.8371, 36.5007)
    # Longitude range for Texas and New Mexico
    texas_nm_lon_range = (-106.6456, -93.5083)

    random_coords = []
    while len(random_coords) < n:
        lat = np.random.uniform(texas_nm_lat_range[0], texas_nm_lat_range[1])
        lon = np.random.uniform(texas_nm_lon_range[0], texas_nm_lon_range[1])

        # Check that the coordinates are outside the existing bounding box
        if lat < lat_min or lat > lat_max or lon < lon_min or lon > lon_max:
            random_coords.append((lon, lat))

    return random_coords


def main(download_folder="downloads"):
    os.makedirs(download_folder, exist_ok=True)

    # Load well coordinates
    csv_file = "./PERMIAN BASIN Well Headers.CSV"
    coordinates_df = read_coordinates_from_csv(csv_file)

    # Define date range and evalscript
    start_date = "2024-06-01"
    end_date = "2024-08-31"
    evalscript = """
    //VERSION=3
    function setup() {
      return {
        input: ["B02", "B03", "B04"],
        output: {
          bands: 3,
          sampleType: "AUTO"
        }
      }
    }

    function evaluatePixel(sample) {
      return [2.5 * sample.B04, 2.5 * sample.B03, 2.5 * sample.B02]
    }
    """

    # Authenticate
    oauth, token = authenticate(CLIENT_ID, CLIENT_SECRET)

    # Get the min/max lat and lon of the well dataset
    lon_min, lon_max = coordinates_df['Surface Hole Longitude (WGS84)'].min(
    ), coordinates_df['Surface Hole Longitude (WGS84)'].max()
    lat_min, lat_max = coordinates_df['Surface Hole Latitude (WGS84)'].min(
    ), coordinates_df['Surface Hole Latitude (WGS84)'].max()

    # Create label DataFrame
    labels = []

    # Download images for actual well locations
    # TODO: remove .head(10) to download for all wells
    for index, row in coordinates_df.head(2000).iterrows():
        lon, lat = row['Surface Hole Longitude (WGS84)'], row['Surface Hole Latitude (WGS84)']
        save_path = f"{download_folder}/{lon}_{lat}.png"
        bbox = create_bbox_from_center(lon, lat, box_size_m=5000)
        download_image(oauth, CLIENT_ID, CLIENT_SECRET, bbox, start_date,
                       end_date, save_path, evalscript)
        labels.append(
            {'lat': lat, 'lon': lon, 'label': 1, 'file_path': save_path})

    # Generate random coordinates outside the bounding box and download images
    random_coords = generate_random_coordinates_outside_bbox(2000,        # TODO: change here to select the number of non-well train data
                                                             # len(coordinates_df),
                                                             lon_min, lon_max, lat_min, lat_max)
    for lon_i, lat_i in random_coords:
        lon = round(lon_i, 6)
        lat = round(lat_i, 6)
        save_path = f"{download_folder}/{lon}_{lat}.png"
        bbox = create_bbox_from_center(lon, lat, box_size_m=5000)
        download_image(oauth, CLIENT_ID, CLIENT_SECRET, bbox, start_date,
                       end_date, save_path, evalscript)
        labels.append(
            {'lat': lat, 'lon': lon, 'label': 0, 'file_path': save_path})

    # Save label DataFrame
    label_df = pd.DataFrame(labels)
    label_df.to_csv("labels_4K.csv", index=False)
    print("Labels saved to labels_4K.csv")


if __name__ == "__main__":
    # Pass the desired download folder when calling main
    main(download_folder="EXP1_4K_IMAGE")