import pandas as pd
import geopandas as gpd
import folium
from bikeability_config import USE_ACCIDENTS, EXPORT_PATH

def create_suitability_visualisation(edges: pd.DataFrame):
    edges_for_vis = gpd.GeoDataFrame(edges, crs="EPSG:25832")
    edges_for_vis = edges_for_vis[~edges_for_vis.geometry.isna()]
    edges_for_vis = edges_for_vis[['osmid', 'name', 'suitability_modifier', 'score_surface', 'score_separation', "accident_count", 'highway', 'geometry']]
    style_kwds = {"weight": 3}

    edges_for_vis.rename(columns={'osmid': "OSM ID",
                                  "name": "Name",
                                  "suitability_modifier": "Tauglichkeits-Modifikator",
                                  "score_surface": "Wertung Oberflächenqualität",
                                  "score_separation": "Wertung Trennung",
                                  "accident_count": "Anzahl Unfälle (3 Jahre)",
                                  "highway": "OSM Highwaytyp"}, 
                         inplace = True)

    scores_surface = folium.Map(tiles = "CartoDB positron")
    scores_surface = edges_for_vis.explore(column = "Wertung Oberflächenqualität", 
                                            cmap = "viridis", 
                                            vmin = 1, 
                                            vmax = 5,
                                            style_kwds = style_kwds,
                                            m = scores_surface)
    scores_surface.save(f"{EXPORT_PATH}/surface.html")
    
    
    scores_separation = folium.Map(tiles = "CartoDB positron")
    scores_separation = edges_for_vis.explore(column = "Wertung Trennung", 
                                              cmap = "viridis", 
                                              vmin = 1, 
                                              vmax = 5,
                                              style_kwds = style_kwds,
                                              m = scores_separation)
    scores_separation.save(f"{EXPORT_PATH}/separation.html")
    
    
    
    suitability_score = folium.Map(tiles = "CartoDB positron")
    suitability_score = edges_for_vis.explore(column = "Tauglichkeits-Modifikator",
                                      cmap = "viridis",
                                      vmin = 0, 
                                      vmax = 1,
                                      style_kwds = style_kwds,
                                      m = suitability_score)
    suitability_score.save(f"{EXPORT_PATH}/suitability.html")

    if USE_ACCIDENTS:
        accident_count = edges_for_vis.explore(column = "Anzahl Unfälle (3 Jahre)",
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
    buildings_for_vis = buildings[["id", "node", "building", "score", "geometry", "centroid"]]
    buildings_for_vis.rename(columns = {"id": "OSM ID",
                                        "node": "Zugehöriger Knoten",
                                        "building": "Gebäudetyp",
                                        "score": "Score"},
                             inplace = True)
    buildings_vis = folium.Map(tiles = "CartoDB positron")
    buildings_vis = buildings_for_vis.explore(column = "Score",
                                      cmap = "viridis",
                                      vmin = 0, 
                                      vmax = 1,
                                      m = buildings_vis)
    buildings_vis.save(f"{EXPORT_PATH}/buildings.html")
    
def create_POI_visualisation(POIs: gpd.GeoDataFrame):
    POIs_for_vis = POIs[["name", "id", "geometry", "node", "POI_category"]]
    POIs_for_vis.rename(columns = {"id": "OSM ID",
                                   "name": "Name",
                                   "node": "Zugehöriger Knoten",
                                   "POI_category": "Kategorie"},
                        inplace = True)
    POIs_for_vis = POIs_for_vis[POIs_for_vis.Kategorie != "none"]
    POIs_vis = folium.Map(tiles = "CartoDB positron")
    POIs_vis = POIs.explore(column = "POI_category", m = POIs_vis)
    POIs_vis.save(f"{EXPORT_PATH}/POIs.html")