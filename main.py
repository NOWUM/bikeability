import logging
from typing import List, Tuple

import geopandas as gpd
import networkx as nx
import osmnx as ox
import pandas as pd
from shapely.geometry import Point

import accident_data.accidents_util as acd
import visualisation
import helper
from bikeability_config import CONFIG
from suitability import Suitability

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
        city: str,
        poi_dict: dict,
        network: nx.MultiDiGraph) -> gpd.GeoDataFrame:
    """
    Function for fetching POIs for given group of people.
    """

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
    pois["POI_type"] = pois["amenity"].fillna(pois["shop"])

    # resetting index
    pois.reset_index(inplace=True)

    return pois[["osmid", "geometry", "centroid", "node", "POI_type"]]



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
        network: nx.MultiDiGraph) -> List[pd.DataFrame]:
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

    # empty list to store DFs with distances in
    dist_list = []

    # buffer distance in buildings
    buildings["geometry"] = buildings["geometry"].buffer(CONFIG['max_distance'])

    # iterate over buildings
    for idx, building_data in buildings.iterrows():

        # get POIs within geometry of buildings
        POIs_within = POIs[POIs.within(building_data["geometry"])]

        # calculate distance for this building to each POI
        POIs_within["dist"] = \
            POIs_within["node"].apply(
                helper.calc_shortest_path_length,
                args=(building_data["node"], network, ))
        POIs_within.reset_index(inplace=True)

        # build dataframe from the new information
        route_poi = pd.DataFrame({
            "building_osmid": [building_data["osmid"]] * len(POIs_within),
            "node_1": [building_data["node"]] * len(POIs_within),
            "node_2": POIs_within["node"].copy(),
            "POI_osmid": POIs_within["osmid"].copy(),
            "POI_type": POIs_within["POI_type"].copy(),
            "dist": POIs_within["dist"].copy()})

        dist_list.append(route_poi)

    return dist_list


    
    
def score_routes(
        buildings: gpd.GeoDataFrame,
        dist_list: List[pd.DataFrame],
        group_weight_factor: dict) -> List[pd.DataFrame]:
    """
    Function to calculate walk scores for a list of dataframes.

    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        Dataframe containing a list of buildings.
    dist_list : List[pd.DataFrame]
        List of dataframes containing routes to all relevant POIs for one
        specific building.
    group_weight_factor : dict
        Weight factors for specific POIs.

    Returns
    -------
    score_list : pd.DataFrame
        List of Dataframes mirroring the structure of dist_list but also 
        containing scores for each of the routes.
    """

    score_list = []

    # Iterate over buildings
    for building in dist_list:
        route_scores = pd.DataFrame()
        walk_scores = pd.DataFrame()
        # Calculate a factor for the number of accidents on the route
        accident_modifier = helper.accident_score(building["accident_count"])

        # Iterate over POI types
        for POI_type, weight_factor in group_weight_factor.items():
            score = helper.calc_score(
                route_distance=building[building["POI_type"]
                                        == POI_type]["dist"],
                weight_factor=weight_factor)

            tmp_df = helper.format_score(weight_factor,
                                         score,
                                         building.loc[building["POI_type"] == POI_type].index)

            walk_scores = pd.concat([walk_scores, tmp_df], axis='index')

        # Modify the scores with the accident factors
        walk_scores = walk_scores.multiply(other=accident_modifier,
                                           axis="index")
        # Re-Combine the scores with the building dataframe
        route_scores = pd.concat([building, walk_scores], axis='columns')
        # Remove zero-columns
        route_scores = route_scores.loc[:, (route_scores != 0).any(axis=0)]
        score_list.append(route_scores)

    return score_list


def calc_building_scores(
        buildings: gpd.GeoDataFrame,
        score_list: List[pd.DataFrame],
        group_weight_factor: dict) -> gpd.GeoDataFrame:
    """


    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        Dataframe containing a list of buildings.
    score_list : List[pd.DataFrame]
        List of dataframes containing scored routes to all relevant POIs for 
        one specific building.
    group_weight_factor : dict
        Weight factors for specific POIs.

    Returns
    -------
    buildings : gpd.GeoDataFrame
        Dataframe mirroring buildings but adding scores.
    """

    # Calculate the sum of weight factors to properly scale the scores.
    weight_sum = 0
    for weight in list(group_weight_factor.values()):
        weight_sum = weight_sum + sum(weight)

    building_scores = []
    # Iterate over buildings
    for building in score_list:
        building_score_list = []
        # Filter buildings without street connection.
        if building.size > 1:
            # Iterate over POI types.
            for POI_type, weight_factor in group_weight_factor.items():
                route_scores = building[
                    building["POI_type"] == POI_type]
                # Select only the columns containing the scores.
                route_scores = route_scores[
                    building.columns[building.columns.str.contains(pat='score')]]

                # Iterate over score columns
                for i in range(len(weight_factor)):
                    # Filter unused score columns
                    if weight_factor[i] != 0:
                        if route_scores.size > 0:
                            building_score_list.append(
                                max(route_scores.iloc[:, i]))
                        else:
                            building_score_list.append(0)
            building_scores.append(sum(building_score_list)/weight_sum)
        else:
            building_scores.append(0)

    buildings.loc[:, 'score'] = building_scores

    return buildings



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

if __name__ == "__main__":
    logging.basicConfig(
        filename="bikeability.log",
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
        datefmt="%d-%m-%Y %H:%M:%S")
    
    

    # calculate suitability
    suitability = Suitability()
    edges, network = suitability.eval_suitability(CONFIG)
    
    if CONFIG['visualize']:
        visualisation.create_suitability_visualisation(edges)

    
    # Download OSM buildings chart  
    residential_buildings = fetch_and_filter_residences(city = CONFIG['city'], network = network)
    log.info("Buildings loaded... ")

    POIs = fetch_POIs(city = CONFIG['city'], 
                      poi_dict = CONFIG["pois_model"], 
                      network = network)
    log.info("Points of interest (POIs) loaded... ")

    dist_list = prepare_scoring(residential_buildings, POIs, network)
    log.info("Distances from buildings to POIs calculated... ")

    score_list = score_routes(residential_buildings, dist_list, CONFIG["model_weight_factors"])
    log.info("Scores for routes calculated...")

    buildings = calc_building_scores(residential_buildings, score_list, CONFIG["model_weight_factors"])
    log.info("Building scores assigned!")

    # export_scores(residential_buildings, persona_name, network, EXPORT_PATH)
    # log.info("Building scores saved!")
