import io
import os
import pandas as pd
import numpy as np
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from PIL import Image
import json

# Your Sentinel Hub client credentials
CLIENT_ID = '06b04b38-522f-41bd-a399-72ec52eb67a3'
CLIENT_SECRET = 'sp4FNXBnv2k7TxFmYyUw2JH5QBx1BbUf'


def authenticate(client_id, client_secret):
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(
        token_url='https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token',
        client_secret=client_secret,
        include_client_id=True
    )
    return oauth, token


def refresh_token(oauth):
    # Refresh the token by re-authenticating
    global CLIENT_ID, CLIENT_SECRET
    print("Refreshing token...")
    oauth, token = authenticate(CLIENT_ID, CLIENT_SECRET)
    return oauth


def download_image(oauth, bbox, start_date, end_date, save_path, evalscript):
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

    while True:
        try:
            response = oauth.post(
                url_request, headers=headers_request, json=json_request)

            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content))
                img.save(save_path)
                print(f"Image saved as {save_path}")
                return True
            elif response.status_code == 401:  # Token expired
                oauth = refresh_token(oauth)
            else:
                print(
                    f"Failed to fetch image. Status code: {response.status_code}")
                print(f"Response content: {response.content}")
                return False
        except Exception as e:
            print(f"Error during download: {e}")
            time.sleep(5)  # Retry after a short delay


def main(label_file, download_folder="downloads"):
    os.makedirs(download_folder, exist_ok=True)

    # Load the COCO_labels.json file
    with open(label_file, 'r') as f:
        coco_data = json.load(f)

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

    # Iterate through each image entry in the JSON
    for image_info in coco_data['images']:
        # Extract bounding box and file name
        bbox = image_info['bbox']
        file_name = image_info['file_name']
        save_path = os.path.join(download_folder, file_name)

        # Check if the file already exists
        if os.path.exists(save_path):
            print(f"File {file_name} already exists. Skipping download.")
            continue

        # Convert bbox to (min_lon, min_lat, max_lon, max_lat)
        min_lon, min_lat, width, height = bbox
        max_lon = min_lon + width
        max_lat = min_lat + height
        bbox_coordinates = (min_lon, min_lat, max_lon, max_lat)

        # Download the image
        success = download_image(
            oauth, bbox_coordinates, start_date, end_date, save_path, evalscript)
        if not success:
            print(f"Failed to download {file_name}. Moving to next.")


if __name__ == "__main__":
    # Pass the desired download folder when calling main
    main(label_file="COCO_labels.json", download_folder="test_download")
