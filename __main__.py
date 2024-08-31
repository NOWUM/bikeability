import logging

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
import numpy as np

import visualisation
import helper
from bikeability_config import CONFIG
from suitability import Suitability
from tqdm import tqdm

import warnings

warnings.filterwarnings("error", message="DeprecationWarning: Passing a BlockManager to GeoDataFrame is deprecated and will raise in a future version. Use public APIs instead.")
# logging
log = logging.getLogger("Bikeability")

def fetch_and_filter_residences(
        city: str,
        network: nx.MultiDiGraph) -> gpd.GeoDataFrame:
    """
    Fetches buildings and calculates nearest node for each building for given city in EPSG:25832.
    """
    # load buildings
    buildings = ox.features_from_place(city, {"building": True})

    # convert to EPSG:25832
    buildings = buildings.to_crs("EPSG:25832")

    # filter out non-polygon geometries
    buildings = buildings[buildings.geometry.type == "Polygon"]
    
    buildings = buildings[buildings.building.isin(CONFIG["residential_building_types"])]

    # calculate centroids for nearest nodes
    buildings["centroid"] = buildings.centroid

    # get nearest nodes
    buildings["node"] = ox.nearest_nodes(
        G=network,
        X=buildings["centroid"].x,
        Y=buildings["centroid"].y)

    # reset index
    buildings.reset_index(inplace=True)

    # filter out everything but geometry, centroid and node
    return buildings[["osmid", "geometry", "centroid", "node", "building"]]


def fetch_POIs(
        CONFIG: dict,
        network: nx.MultiDiGraph) -> gpd.GeoDataFrame:
    """
    Function for fetching POIs for given group of people.
    """
    city = CONFIG['city']
    poi_dict = CONFIG["pois_model"]
    # fetch original POI GDF
    pois = ox.features_from_place(city, poi_dict)

    # convert POIs to EPSG:25832
    pois = pois.to_crs("EPSG:25832")

    # calculate centroid for nearest nodes
    pois["centroid"] = pois.centroid

    # find nearest node
    pois["node"] = ox.nearest_nodes(
        G=network,
        X=pois["centroid"].x,
        Y=pois["centroid"].y)

    # fill missing names
    pois["name"].fillna("No name", inplace=True)

    # POI is mix of amenity and shop
    pois["POI_type"] = pois["amenity"].fillna(pois["shop"].fillna("office"))

    # resetting index
    pois.reset_index(inplace=True)
    
    categories = CONFIG["weight_factors_categories"]
    pois.insert(1, "POI_category", "none")
    for category, content in categories.items():
        pois.POI_category.loc[pois.POI_type.isin(content)] = category

    return pois[["name", "osmid", "geometry", "centroid", "node", "POI_type", "POI_category"]]


def score_building(building: pd.Series,
                   POIs: gpd.GeoDataFrame,
                   network: nx.MultiDiGraph,
                   CONFIG: dict,
                   weight_sum: int):
    """
    Calculate bikeability scores for one building, using a suitability
    network.

    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        Dataframe containing a list of buildings.
    POIs : gpd.GeoDataFrame
        List of points of interest.
    network : nx.MultiDiGraph
        Node-Edge-Network of the relevant area.
    CONFIG : dict
        Bikeability configuration.
    weight_sum: int
        The sum value of all weight factors.

    Returns
    -------
    buildings : gpd.GeoDataFrame
        Buildings dataframe including bikeability scores.

    """
    
    # The required number of POIs per category before the range is extended
    required_POIs = 10
        
    categories = CONFIG["weight_factors_categories"]
    weight_factors = CONFIG["model_weight_factors"]

    building_scores = pd.Series()
    for category in categories:
        POIs_category = POIs[POIs.POI_type.isin(categories[category])]
        
        # Filter the specified number of POIs in the category, using the 
        # shortest linear distances
        shortest_distances = helper.knearest(from_points = building.centroid,
                                      to_points = POIs_category.centroid,
                                      k = required_POIs)
        POIs_within = POIs.loc[shortest_distances.index]
        POIs_within = POIs_within.reset_index(drop=True)
        
        # Find the shortest (weighted) routes from building to POI
        routes = POIs_within["node"].apply(
            helper.calc_shortest_path,
            args = (building.node, network, ))
        
        # Extract lengths and suitability values from routes
        route_values = helper.get_route_values(routes = routes,
                                          edges = edges)
        # transform distances to scores using sigmoid function
        distance_scores = helper.sigmoid(route_values.length)
        route_values.insert(1, "dist_score", distance_scores)
        
        # calculate full route scores
        route_scores = route_values.dist_score - (1-route_values.suitability)
        route_scores[route_scores<0] = 0
        route_values.insert(3, "route_score", route_scores)
        
        weight_factor_POI = weight_factors[category]
        if len(weight_factor_POI) > len(route_values):
            weight_factor_POI = weight_factor_POI[0:len(route_values)]
        relevant_scores = route_values["route_score"].nsmallest(len(weight_factor_POI)).to_list()
        weighted_scores = np.array(weight_factor_POI) * np.array(relevant_scores)
        building_scores[category] = sum(weighted_scores)
    building_score = sum(building_scores)/weight_sum
    return building_score


def score_buildings(residential_buildings: gpd.GeoDataFrame,
                    POIs: gpd.GeoDataFrame,
                    network: nx.MultiDiGraph,
                    CONFIG: dict) -> gpd.GeoDataFrame:
    """
    Calculates scores for all buildings

    Parameters
    ----------
    residential_buildings : gpd.GeoDataFrame
        Dataframe containing a list of buildings.
    POIs : gpd.GeoDataFrame
        List of points of interest.
    network : nx.MultiDiGraph
        Node-Edge-Network of the relevant area.
    CONFIG : dict
        Bikeability configuration.

    Returns
    -------
    buildings_scored : TYPE
        The building dataframe with added scores.

    """
    
    # sum up weights to scale them from 0 to 1
    weight_sum = helper.calc_weight_sum(CONFIG)

    # Create pandas methods with progress bar
    tqdm.pandas()
    
    # score buildings
    scores = residential_buildings.progress_apply(
        func = score_building,
        axis = 1,
        args = (POIs, network, CONFIG, weight_sum))
    
    buildings_scored = residential_buildings.copy()
    buildings_scored.insert(5, "score", scores)
    
    return buildings_scored

def save_results(buildings: gpd.GeoDataFrame,
                 POIs: gpd.GeoDataFrame,
                 CONFIG: dict):
    """
    Export the results as geojson, csv and visualisation

    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        Dataframe containing a list of buildings with scores.
    POIs : gpd.GeoDataFrame
        Dataframe containing a list of POIs.
    CONFIG : dict
        Bikeability configuration.

    Returns
    -------
    None.

    """
    
    # visualise buildings as html file
    visualisation.create_building_visualisation(buildings)
    #visualise POIs as html file
    visualisation.create_POI_visualisation(POIs)
    #export as csv
    export_path = CONFIG["export_path"]
    buildings.to_csv(f"{export_path}/results.csv")
    #export as geojson
    buildings_for_output = buildings.drop(columns=["centroid"])
    buildings_for_output.to_file(f"{export_path}/results.json", driver="GeoJSON")

if __name__ == "__main__":
    logging.basicConfig(
        filename="bikeability.log",
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S")

    # calculate suitability
    suitability = Suitability()
    edges, network = suitability.eval_suitability(CONFIG)
    log.info("Suitability network completed. Loading buildings... ")
    
    if CONFIG['visualize']:
        visualisation.create_suitability_visualisation(edges)

    
    # Download OSM buildings chart
    residential_buildings = fetch_and_filter_residences(city = CONFIG['city'], network = network)
    log.info("Buildings loaded. Loading POIs... ")

    POIs = fetch_POIs(CONFIG = CONFIG,
                      network = network)
    log.info("Points of interest (POIs) loaded. Calculating scores... ")
    
    buildings_scored = score_buildings(residential_buildings, POIs, network, CONFIG)
    
    save_results(buildings = buildings_scored,
                 POIs = POIs,
                 CONFIG = CONFIG)

