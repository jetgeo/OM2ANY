import duckdb
import pandas as pd
from datetime import datetime
import requests
import geojson
from shapely.geometry import shape

def get_bbox(geometry):
    polygon = shape(geometry)
    return polygon.bounds

# setting up in memory duckdb + extensions
db = duckdb.connect()
db.execute("INSTALL spatial")
db.execute("INSTALL httpfs")
db.execute("""LOAD spatial;
LOAD httpfs;
SET s3_region='us-west-2';""")

# Raleigh bound box from ESRI API
# ral_esri = "https://maps.wakegov.com/arcgis/rest/services/Jurisdictions/Jurisdictions/MapServer/1/query?where=JURISDICTION+IN+%28%27RALEIGH%27%29&returnExtentOnly=true&outSR=4326&f=json"
# bbox = requests.get(ral_esri).json()['extent']
# check out https://overturemaps.org/download/ for new releases
# places_url = "s3://overturemaps-us-west-2/release/2023-07-26-alpha.0/theme=places/type=*/*"

# Bounding box
with open('C:\\Data\\GitHub\\jetgeo\\OM2UML\\Script\\hamar.geojson') as f:
    gj = geojson.load(f)
    features = gj['features'][0]  # Assuming you want the first feature

bbox = get_bbox(features['geometry'])
print("Bounding Box (minx, miny, maxx, maxy):", bbox)

places_url = "s3://overturemaps-us-west-2/release/2024-02-15-alpha.0/theme=places/type=*/*"
query = f"""
SELECT
  *
FROM read_parquet('{places_url}')
WHERE
  bbox.minx > {bbox[0]}
  AND bbox.maxx < {bbox[2]} 
  AND bbox.miny > {bbox[1]} 
  AND bbox.maxy < {bbox[3]}
"""

# Took me around 25 minutes
print(datetime.now())
res = pd.read_sql(query,db)
print(datetime.now())

