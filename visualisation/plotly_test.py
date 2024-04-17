import plotly.express as px
import geopandas as gpd
import shapely.geometry
import numpy as np
import wget

# download a zipped shapefile
wget.download("https://plotly.github.io/datasets/ne_50m_rivers_lake_centerlines.zip")

# open a zipped shapefile with the zip:// pseudo-protocol
geo_df = gpd.read_file("zip://ne_50m_rivers_lake_centerlines.zip")

lats = []
lons = []
names = []

# apply als Optimierung?






fig = px.line_geo(lat=lats, lon=lons, hover_name=names)
fig.show()

from operator import attrgetter
geoms = scoring.geometry.map(attrgetter("geoms"))
for geom in geoms:
    for linestring in geom:
        x, y = linestring.xy
        lats = np.append(lats, y)
        lons = np.append(lons, x)
        lats = np.append(lats, None)
        lons = np.append(lons, None)



x,y = geoms.map(attrgetter("xy"))

x,y = test.map(attrgetter("xy"))

ag = attrgetter("xy")

