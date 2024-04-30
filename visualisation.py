import pandas as pd
import geopandas as gpd
from bikeability_config import USE_ACCIDENTS, EXPORT_PATH

def vis_suitability(edges: pd.DataFrame):
    edges_for_vis = gpd.GeoDataFrame(edges, crs="EPSG:25832")
    edges_for_vis = edges_for_vis[~edges_for_vis.geometry.isna()]

    scores_surface = edges_for_vis.explore(column = "score_surface", 
                                            cmap = "viridis", 
                                            vmin = 0, 
                                            vmax = 5)
    scores_surface.save(f"{EXPORT_PATH}/surface.html")
    
    
    scores_separation = edges_for_vis.explore(column = "score_separation", 
                                              cmap = "viridis", 
                                              vmin = 0, 
                                              vmax = 5)
    scores_separation.save(f"{EXPORT_PATH}/separation.html")

    suitability_modifier = edges_for_vis.explore(column = "suitability_modifier",
                                      cmap = "viridis",
                                      vmin = 1, 
                                      vmax = 2)
    suitability_modifier.save(f"{EXPORT_PATH}/suitability_modifier.html")

    if USE_ACCIDENTS:
        accident_count = edges_for_vis.explore(column = "accident_count",
                                          cmap = "viridis",
                                          vmin = 0,
                                          vmax = 10)
        accident_count.save(f"{EXPORT_PATH}/accidents.html")
    
        score_accident = edges_for_vis.explore(column = "score_accident",
                                          cmap = "viridis",
                                          vmin = 0, 
                                          vmax = 5)
        score_accident.save(f"{EXPORT_PATH}/accidents_score.html")

