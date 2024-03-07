from typing import Tuple, List
import logging
import networkx as nx
import osmnx as ox
import geopandas as gpd
import pandas as pd
import helper
from shapely.geometry import Point

ACCIDENT_PATH = "accident_data/accidents_foot.h5"
EXPORT_PATH = "results"

# Points of interest (POIs)
FAMILY_POIS = {
    "amenity": [
        "kindergarten",
        "school",
        "bus_station",
        "car_sharing",
        "pharmacy",
        "doctors",
        "cinema"],
    "shop": [
        "bakery",
        "supermarket",
        "greengrocer"]}

SENIOR_POIS = {
    "amenity": [
        "cafe",
        "bus_station",
        "bank",
        "pharmacy",
        "place_of_worship",
        "doctors",
        "theatre"],
    "shop": [
        "bakery",
        "supermarket",
        "butcher"]}

STUDENT_POIS = {
    "amenity": [
        "bar",
        "cafe",
        "library",
        "university",
        "bus_station",
        "parcel_locker",
        "pharmacy",
        "doctors"],
    "shop": [
        "hairdresser",
        "supermarket"]}

# Weight factors
FAMILY_WEIGHT_FACTORS = {
    "kindergarten": [9, 0, 0],
    "school": [8, 0, 0],
    "bus_station": [4, 0, 0],
    "car_sharing": [5, 0, 0],
    "pharmacy": [6, 0, 0],
    "doctors": [7, 0, 0],
    "cinema": [1, 0, 0],
    "bakery": [3, 0, 0],
    "supermarket": [10, 0, 0],
    "greengrocer": [2, 0, 0]}

SENIOR_WEIGHT_FACTORS = {
    "cafe": [5, 0, 0],
    "bus_station": [2, 0, 0],
    "bank": [3, 0, 0],
    "pharmacy": [8, 0, 0],
    "place_of_worship": [6, 0, 0],
    "doctors": [10, 0, 0],
    "theatre": [1, 0, 0],
    "bakery": [7, 0, 0],
    "supermarket": [9, 0, 0],
    "butcher": [4, 0, 0]}

STUDENT_WEIGHT_FACTORS = {
    "bar": [4, 0, 0],
    "cafe": [3, 0, 0],
    "library": [9, 0, 0],
    "university": [10, 0, 0],
    "bus_station": [4, 0, 0],
    "parcel_locker": [1, 0, 0],
    "pharmacy": [5, 0, 0],
    "doctors": [6, 0, 0],
    "hairdresser": [2, 0, 0],
    "supermarket": [7, 0, 0]}

MAX_DISTANCE = 800

# logging
log = logging.getLogger("Walkability")
logging.basicConfig(
    filename="walkability.log",
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S")


def fetch_network_edges(
        city: str) -> Tuple[nx.MultiDiGraph, gpd.GeoDataFrame]:
    """
    Fetches network and it's edges for given city in EPSG:25832.
    """

    # get original network
    network = ox.graph_from_place(city, network_type="walk")

    # fetch the edges
    network_edges = ox.graph_to_gdfs(network, nodes=False)

    # convert to EPSG:25832
    network = ox.project_graph(network, to_crs="EPSG:25832")
    network_edges.to_crs("EPSG:25832", inplace=True)

    return network, network_edges


def fetch_buildings(
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
    return buildings[["osmid", "geometry", "centroid", "node"]]


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
        network: nx.MultiDiGraph,
        accidents: pd.DataFrame) -> List[pd.DataFrame]:
    """
    Prepares the consecutive scoring of buildings by calculating weighted 
    scores for all routes between the listed buildings and relevant POIs and 
    counting the number of accidents in each given path.

    Parameters
    ----------
    buildings : gpd.GeoDataFrame
        Dataframe containing a list of buildings.
    POIs : gpd.GeoDataFrame
        List of points of interest.
    network : nx.MultiDiGraph
        Node-Edge-Network of the relevant area.
    accidents : pd.DataFrame
        List of geocoded accidents concerning pedestrians in the relevant area.

    Returns
    -------
    dist_list : List(pd.DataFrame)
        List of distances for each relevant route in the specified buildings
        table. Also includes the number of accidents on each route.
    """

    # empty list to store DFs with distances in
    dist_list = []

    # buffer distance in buildings
    buildings["geometry"] = buildings["geometry"].buffer(MAX_DISTANCE)

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

        # calculate accidents on the paths to each POI
        paths = \
            POIs_within["node"].apply(
                helper.calc_shortest_path,
                args=(building_data["node"], network, ))

        # empty list of numbers of accidents on each route for this building
        accident_counts = []

        # iterate over routes for this building
        for path in paths:
            # re-project the geometry of paths to an area
            projection = path_to_projection(path, network)
            if projection:
                # find accidents within the area of the path
                intersections = accidents["geometry"].apply(
                    lambda x: x.intersects(projection))
                # count accidents in the path and append it to distant list
                accident_counts.append(
                    len(intersections[intersections == True]))
            else:
                # if no path exists, zero accidents are appended
                accident_counts.append(0)

        # build dataframe from the new information
        route_poi = pd.DataFrame({
            "building_osmid": [building_data["osmid"]] * len(POIs_within),
            "node_1": [building_data["node"]] * len(POIs_within),
            "node_2": POIs_within["node"].copy(),
            "POI_osmid": POIs_within["osmid"].copy(),
            "POI_type": POIs_within["POI_type"].copy(),
            "dist": POIs_within["dist"].copy(),
            "accident_count": accident_counts})

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

    POIs = [FAMILY_POIS, STUDENT_POIS, SENIOR_POIS]
    persona_weights = [
        FAMILY_WEIGHT_FACTORS,
        STUDENT_WEIGHT_FACTORS,
        SENIOR_WEIGHT_FACTORS]
    persona_names = ["families", "students", "seniors"]

    network, edges = fetch_network_edges("Aachen, Germany")
    log.info("Network and it's edges loaded... ")

    buildings = fetch_buildings("Aachen, Germany", network)
    log.info("Buildings loaded... ")

    accidents = fetch_accidents(path = ACCIDENT_PATH)

    for persona_POIs, persona_weight, persona_name in zip(POIs, persona_weights, persona_names):
        log.info(f"Starting calculations for {persona_name}... ")

        POIs = fetch_POIs("Aachen, Germany", persona_POIs, network)
        log.info("Points of interest (POIs) loaded... ")

        dist_list = prepare_scoring(buildings, POIs, network, accidents)
        log.info("Distances from buildings to POIs calculated... ")

        score_list = score_routes(buildings, dist_list, persona_weight)
        log.info("Scores for routes calculated...")

        buildings = calc_building_scores(
            buildings, score_list, persona_weight)
        log.info("Building scores assigned!")

        export_scores(buildings, persona_name, network, EXPORT_PATH)
        log.info("Building scores saved!")
