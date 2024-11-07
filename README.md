1. Clone this repo to local
2. Download the Well Header csv file from the shared google drive: /data/well/PERMIAN BASIN Well Headers.CSV
3. Move the csv file under the same directory of the get_sentinel_hub.py file
4. Comment out line 161 and uncomment line 160, so that we download for all wells in the PERMIAN BASIN csv files
5. [TODO] create label geojson data
6. [TODO] add places without well (satellite images and labels) into the trainset

***The code can't download images consistently due to the expiration of the token.
