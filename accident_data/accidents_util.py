import pandas as pd
import geopandas as gpd
from shapely import Point

def fetch_accidents(
        path: str) -> gpd.GeoDataFrame():
    """
    Fetches traffic accident data from the provided file.
    """

    # read accidents from file
    accidents = pd.read_hdf(path)

    # reduce accident geometry to points
    accidents["geometry"] = accidents.apply(lambda x: Point(x["x_linref"],
                                                            x["y_linref"]),
                                            axis="columns")
    # convert to geodataframe
    accidents = gpd.GeoDataFrame(accidents,
                                 geometry="geometry",
                                 crs="epsg:25832")
    accidents = accidents[["x_linref", "y_linref",
                           "x_wgs84", "y_wgs84", "geometry"]]

    return accidents


def match_accidents_network(edges: pd.DataFrame, accidents: pd.DataFrame):
    edges.insert(10, "accident_count", 0)
    edges_geometry = gpd.GeoSeries(edges.geometry).buffer(5, resolution = 16)
    for accident in accidents.geometry:
        edges.loc[edges_geometry.contains(accident), "accident_count"] = edges.loc[edges_geometry.contains(accident), "accident_count"]+1
    
    return edges