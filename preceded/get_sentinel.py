import os
import numpy as np
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

# Your client credentials
client_id = 'd7f7b946-16c7-4d7b-ac9d-9fa8c5a775e4'
client_secret = 'P75SqYQF0tPvX73O6ocgc4SELvWdLMda'

# Sentinel Hub WMS URL for Sentinel-2 imagery
WMS_URL = "https://services.sentinel-hub.com/ogc/wms/{instance_id}"

# Replace with your Sentinel Hub instance ID
INSTANCE_ID = "71e4b63f-d92e-4b76-8b67-0e796e022818"

# Authenticate and create a session


def authenticate(client_id, client_secret):
    """Authenticate with Sentinel Hub and return an OAuth2 session."""
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)
    token = oauth.fetch_token(
        token_url='https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token',
        client_secret=client_secret, include_client_id=True
    )
    return oauth


def create_bbox(lon, lat, size_m=100):
    """Create a bounding box for a patch centered at (lon, lat)."""
    meters_to_deg = size_m / 111320.0  # Approximate conversion to degrees
    min_lon = lon - meters_to_deg / 2
    max_lon = lon + meters_to_deg / 2
    min_lat = lat - meters_to_deg / 2
    max_lat = lat + meters_to_deg / 2
    return f"{min_lon},{min_lat},{max_lon},{max_lat}"


def download_patch_wms(oauth, lon, lat, save_as="patch.png", resolution=100):
    """Download a patch around (lon, lat) and save as PNG."""
    bbox = create_bbox(lon, lat, size_m=resolution)

    today = datetime.utcnow()
    start_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    params = {
        "service": "WMS",
        "request": "GetMap",
        "layers": "TRUE-COLOR-S2L2A",  # Ensure this layer is available in your instance
        "bbox": bbox,
        "width": 256,
        "height": 256,
        "srs": "EPSG:4326",  # Coordinate system WGS84
        "format": "image/png",
        "transparent": "true",
        "time": f"{start_date}/{end_date}",
    }

    url = WMS_URL.format(instance_id=INSTANCE_ID)
    response = oauth.get(url, params=params, stream=True)

    if response.status_code == 200 and len(response.content) > 1000:
        img = Image.open(BytesIO(response.content))

        # Display the image
        img.show()

        # Save the image locally
        img.save(save_as)
        print(f"Saved patch as {save_as}")
    else:
        print(
            f"Failed to download patch: {response.status_code}, {response.text}")


if __name__ == "__main__":
    # Example coordinates for the patch
    lon, lat = -100.428, 31.468

    # Authenticate and create a session
    oauth = authenticate(client_id, client_secret)

    # Download the patch and save it as a PNG
    download_patch_wms(oauth, lon, lat, save_as="patch.png", resolution=500)
