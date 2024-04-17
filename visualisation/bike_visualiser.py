import plotly.express as px
import geopandas as gpd
import shapely.geometry
import numpy as np

def plot_road_scores(scoring: gpd.GeoDataFrame()):
    lats = []
    lons = []
    names = []
    
    for feature, name in zip(scoring.geometry, scoring.name):
        if isinstance(feature, shapely.geometry.linestring.LineString):
            linestrings = [feature]
        elif isinstance(feature, shapely.geometry.multilinestring.MultiLineString):
            linestrings = feature.geoms
        else:
            continue
        
        for linestring in linestrings:
            x, y = linestring.xy
            lats = np.append(lats, y)
            lons = np.append(lons, x)
            names = np.append(names, [name]*len(y))
            lats = np.append(lats, None)
            lons = np.append(lons, None)
            names = np.append(names, None)
            
    fig = px.line_geo(lat=lats, lon=lons, hover_name=names)
    fig.show()
    return fig