import pandas as pd
import geopandas as gpd
import folium
from bikeability_config import USE_ACCIDENTS, EXPORT_PATH

def create_suitability_visualisation(edges: pd.DataFrame):
    edges_for_vis = gpd.GeoDataFrame(edges, crs="EPSG:25832")
    edges_for_vis = edges_for_vis[~edges_for_vis.geometry.isna()]
    edges_for_vis = edges_for_vis[['osmid', 'name', 'highway', 'suitability_modifier', 'score_surface', 'score_separation', "accident_count", 'geometry']]
    style_kwds = {"weight": 3}

    scores_surface = folium.Map(tiles = "CartoDB positron")
    scores_surface = edges_for_vis.explore(column = "score_surface", 
                                            cmap = "viridis", 
                                            vmin = 0, 
                                            vmax = 1,
                                            style_kwds = style_kwds,
                                            m = scores_surface)
    scores_surface.save(f"{EXPORT_PATH}/surface.html")
    
    
    scores_separation = folium.Map(tiles = "CartoDB positron")
    scores_separation = edges_for_vis.explore(column = "score_separation", 
                                              cmap = "viridis", 
                                              vmin = 0, 
                                              vmax = 1,
                                              style_kwds = style_kwds,
                                              m = scores_separation)
    scores_separation.save(f"{EXPORT_PATH}/separation.html")
    
    
    
    suitability_score = folium.Map(tiles = "CartoDB positron")
    suitability_score = edges_for_vis.explore(column = "suitability_modifier",
                                      cmap = "viridis",
                                      vmin = 0, 
                                      vmax = 1,
                                      style_kwds = style_kwds,
                                      m = suitability_score)
    suitability_score.save(f"{EXPORT_PATH}/suitability.html")

    if USE_ACCIDENTS:
        accident_count = edges_for_vis.explore(column = "accident_count",
                                          cmap = "viridis",
                                          vmin = 0,
                                          vmax = 10)
        accident_count.save(f"{EXPORT_PATH}/accidents.html")
    
        # score_accident = edges_for_vis.explore(column = "score_accident",
        #                                   cmap = "viridis",
        #                                   vmin = 0, 
        #                                   vmax = 5)
        # score_accident.save(f"{EXPORT_PATH}/accidents_score.html")

def create_building_visualisation(buildings:gpd.GeoDataFrame):
    buildings_for_vis = buildings[["osmid", "geometry", "centroid", "node", "building", "full_score"]]
    buildings_vis = buildings_for_vis.explore(column = "full_score",
                                      cmap = "viridis",
                                      vmin = 0, 
                                      vmax = 1)
    buildings_vis.save(f"{EXPORT_PATH}/buildings.html")
    
def create_POI_visualisation(POIs: gpd.GeoDataFrame):
    POIs_for_vis = POIs[["name", "osmid", "geometry", "node", "POI_category"]]
    POIs_for_vis = POIs_for_vis[POIs_for_vis.POI_category != "none"]
    POIs_vis = POIs.explore(column = "POI_category")
    POIs_vis.save(f"{EXPORT_PATH}/POIs.html")