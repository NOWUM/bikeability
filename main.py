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
import swifter
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



def path_to_projection(
        path: pd.Series,
        network: nx.MultiDiGraph) -> pd.Series:
    """
    Transforms the given paths into areas and encodes them as longitudes and 
    latitudes.

    Parameters
    ----------
    path : pd.Series
        One path between two points in the network.
    network : nx.MultiDiGraph
        Node-Edge-Network of the relevant area.

    Returns
    -------
    projection : pd.Series
        The path as an area, defined by a series of coordinates.
    """

    try:
        # Filter paths with nodes not included in the network
        path_filter = []
        for i in range(len(path)-1):
            if network.has_node(path[i]):
                path_filter.append(path[i])
        path = path_filter

        # Convert route to a Geodataframe
        path_gdf = ox.utils_graph.route_to_gdf(
            G=network,
            route=path,
            weight="length")

        # Convert format of route to latitude and longitude
        projection, crs = ox.projection.project_geometry(
            geometry=path_gdf.unary_union,
            crs="WGS84",
            to_latlong=True)

        # Create an area of 10 meters around the original route
        projection = projection.buffer(10)

        return projection

    except ValueError:
        return None


def prepare_scoring(
        buildings: gpd.GeoDataFrame,
        POIs: gpd.GeoDataFrame,
        network: nx.MultiDiGraph) -> list[pd.DataFrame]:
    """
    Prepares the consecutive scoring of buildings by calculating weighted 
    scores for all routes between the listed buildings and relevant POIs.

    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        Dataframe containing a list of buildings.
    POIs : gpd.GeoDataFrame
        List of points of interest.
    network : nx.MultiDiGraph
        Node-Edge-Network of the relevant area.

    Returns
    -------
    dist_list : List(pd.DataFrame)
        List of distances for each relevant route in the specified buildings
        table.
    """

    # Ranges in which POIs are found
    max_distances = [400, 800, 1200, 2000, 3000]
    # The required number of POIs per category before the range is extended
    required_POIs = 5
    for max_distance in max_distances:
        # buildings.insert(5, f"buffer_{max_distance}", buildings["geometry"].buffer(max_distance))
        POIs.insert(5, f"buffer_{max_distance}", POIs["centroid"].buffer(max_distance))
    

    categories = CONFIG["weight_factors_categories"]
    
    
    for category in categories:
        # buildings.insert(5, f"POIs_{category}", pd.DataFrame())
        POIs_category = POIs[POIs.POI_type.isin(categories[category])]
        # buildings_POIs_category = pd.Series(name = f"POIs_{category}")
        weighted_distances = pd.Series(name = f"weighted_distances_{category}")
        for ids, building in buildings.iterrows():
            for max_distance in max_distances:
                POIs_within = POIs_category[building["centroid"].within(POIs_category[f"buffer_{max_distance}"])]
                if len(POIs_within.index) >= required_POIs:
                    break
            weighted_distances[ids] = POIs_within.node.apply(
                helper.calc_shortest_path_length,
                args=(building["node"], network, ))
            weighted_distances[ids] = weighted_distances[ids].nsmallest(3)
            # buildings_POIs_category[ids] = POIs_within
            del POIs_within
        buildings = buildings.join(weighted_distances)
        
    return buildings
    
def score_routes(
        buildings: gpd.GeoDataFrame,
        dist_list: list[pd.DataFrame],
        CONFIG: dict) -> list[pd.DataFrame]:
    """
    Function to calculate walk scores for a list of dataframes.

    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        Dataframe containing a list of buildings.
    dist_list : List[pd.DataFrame]
        List of dataframes containing routes to all relevant POIs for one
        specific building.
    CONFIG : dict
        Bikeability configuration.

    Returns
    -------
    score_list : pd.DataFrame
        List of Dataframes mirroring the structure of dist_list but also 
        containing scores for each of the routes.
    """

    weight_factors = CONFIG["model_weight_factors"]

    for POI_type, weight_factor in weight_factors.items():
        scores = pd.Series(name = f"scores_{POI_type}")
        for building_index, building in dist_list.iterrows():
            weighted_distances = building[f"weighted_distances_{POI_type}"].to_list()
            
            len_distances = len(weighted_distances)
            len_weights = len(weight_factor)
            if len_distances > len_weights:
                weighted_distances = weighted_distances[0:len_weights]
            elif len_weights > len_distances:
                weight_factor = weight_factor[0:len_distances]
            
            score = helper.calc_score(
                route_distance=weighted_distances,
                weight_factor=weight_factor)
            scores[building_index] = score
            
        buildings.insert(5, f"scores_{POI_type}", scores)
        del scores            
    return buildings



def calc_building_scores(
        score_list: pd.DataFrame,
        CONFIG: dict) -> gpd.GeoDataFrame:
    """


    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        Dataframe containing a list of buildings.
    score_list : List[pd.DataFrame]
        List of dataframes containing scored routes to all relevant POIs for 
        one specific building.
    CONFIG : dict
        Bikeability configuration.

    Returns
    -------
    buildings : gpd.GeoDataFrame
        Dataframe mirroring buildings but adding scores.
    """
    
    weight_factors = CONFIG["model_weight_factors"]
    # Calculate the sum of weight factors to properly scale the scores.
    weight_sum = 0
    for weight in list(weight_factors.values()):
        weight_sum = weight_sum + sum(weight)

    building_scores = []
    # Iterate over buildings
    for index, building in score_list.iterrows():
        # Iterate over POI types.
        building_score_full = 0
        for POI_type, weight_factor in weight_factors.items():
            route_scores = building[f"scores_{POI_type}"]
            if not isinstance(route_scores, float):
                building_score_POI = (sum(route_scores)/weight_sum)
            else:
                building_score_POI = 0
            building_score_full = building_score_full + building_score_POI
        building_scores.append(building_score_full)
        
    score_list.insert(5, 'full_score', building_scores)
    return score_list

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
    swifter.set_defaults(progress_bar = False)    
    
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
        
        # Find the shortest (weighted) routes from building to POI
        routes = POIs_within.node.swifter.apply(
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

def export_scores(buildings: gpd.GeoDataFrame,
                  persona_name: str, network: nx.MultiDiGraph,
                  EXPORT_PATH: str):
    """
    Export the results to 

    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        Dataframe containing a list of buildings with corresponding walk scores.
    persona_name : str
        Name of the pedestrian profile in use.
    network : nx.MultiDiGraph
        Node-Edge-Network of the relevant area.
    EXPORT_PATH : str
        Folder to save the export files to.

    Returns
    -------
    None.

    """

    # build path to save the exports
    filepath = f'{EXPORT_PATH}/{persona_name}'
    filename = f'walkscore_{persona_name}'

    # create the directories if they don't already exist
    helper.make_export_dir(filepath)

    # visualize data as leaflet map
    vis = helper.visualize_scores(network, buildings)
    # drop unnecessary centroid column for geojson and shp exports
    buildings_for_shp = buildings.drop(columns = 'centroid')

    # save files
    buildings.to_csv(f'{filepath}/{filename}.csv')
    vis.save(f'{filepath}/{filename}.html')
    buildings_for_shp.to_file(f'{filepath}/{filename}.json')
    buildings_for_shp.to_file(f'{filepath}/shp/Walk_{persona_name}.shp')

def score_buildings(residential_buildings: gpd.GeoDataFrame,
                    POIs: gpd.GeoDataFrame,
                    network: nx.MultiDiGraph,
                    CONFIG: dict) -> gpd.GeoDataFrame:
    
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

    # export_scores(residential_buildings, persona_name, network, EXPORT_PATH)
    # log.info("Building scores saved!")
