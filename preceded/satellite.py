import os
from datetime import date, timedelta
import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape

copernicus_user = "zhang99@stanford.edu"  # copernicus User
copernicus_password = "RT/Qe43%Zkh!6VK"  # copernicus Password

# go to geojson.io 
# select a rectangle, download as wkt 
ft = "POLYGON ((-100.42712657761632 31.469326431738068, -100.4296877813848 31.469326431738068, -100.4296877813848 31.466824830802423, -100.42712657761632 31.466824830802423, -100.42712657761632 31.469326431738068))"  # WKT Representation of BBOX
data_collection = "SENTINEL-2" # Sentinel satellite

from datetime import datetime, timedelta

# Given date string
date_string = "2024-01-02"

# Convert string to datetime object
today = datetime.strptime(date_string, "%Y-%m-%d")

# Calculate yesterday's date
yesterday = today - timedelta(days=10)

# Format the dates as strings
today_string = today.strftime("%Y-%m-%d")
yesterday_string = yesterday.strftime("%Y-%m-%d")

print(f"Today: {today_string}")        # Output: 2024-01-01
print(f"Yesterday: {yesterday_string}")  # Output: 2023-12-31

def get_keycloak(username: str, password: str) -> str:
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    try:
        r = requests.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data=data,
        )
        r.raise_for_status()
    except Exception as e:
        raise Exception(
            f"Keycloak token creation failed. Reponse from the server was: {r.json()}"
        )
    return r.json()["access_token"]


json_ = requests.get(
    f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{data_collection}' and OData.CSC.Intersects(area=geography'SRID=4326;{ft}') and ContentDate/Start gt {yesterday_string}T00:00:00.000Z and ContentDate/Start lt {today_string}T00:00:00.000Z&$count=True&$top=1000"
).json()
p = pd.DataFrame.from_dict(json_["value"])  # Fetch available dataset
if p.shape[0] > 0:
    p["geometry"] = p["GeoFootprint"].apply(shape)
    productDF = gpd.GeoDataFrame(p).set_geometry(
        "geometry")  # Convert PD to GPD
    # Remove L1C dataset
    productDF = productDF[~productDF["Name"].str.contains("L1C")]
    print(f" total L2A tiles found {len(productDF)}")
    productDF["identifier"] = productDF["Name"].str.split(".").str[0]
    allfeat = len(productDF)

    if allfeat == 0:
        print("No tiles found for today")
    else:
        # download all tiles from server
        for index, feat in enumerate(productDF.iterfeatures()):
            try:
                session = requests.Session()
                keycloak_token = get_keycloak(
                    copernicus_user, copernicus_password)
                session.headers.update(
                    {"Authorization": f"Bearer {keycloak_token}"})
                url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({feat['properties']['Id']})/$value"
                response = session.get(url, allow_redirects=False)
                while response.status_code in (301, 302, 303, 307):
                    url = response.headers["Location"]
                    response = session.get(url, allow_redirects=False)
                print(feat["properties"]["Id"])
                file = session.get(url, verify=False, allow_redirects=True)

                with open(
                    # location to save zip from copernicus
                    f"{feat['properties']['identifier']}.zip",
                    "wb",
                ) as p:
                    print(feat["properties"]["Name"])
                    p.write(file.content)
            except:
                print("problem with server")
else:
    print('no data found')

