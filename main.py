from typing import Tuple, List # isort anwenden
import logging
import networkx as nx
import osmnx as ox
import geopandas as gpd
import pandas as pd
import helper
from import_osm import import_osm
from shapely.geometry import Point
from bikeability_config import ACCIDENT_PATH,EXPORT_PATH, CITY, DEFAULT_SCORES, \
    TRANSLATION_FACTORS, POIS, PERSONA_WEIGHTS, PERSONA_NAMES, MAX_DISTANCE, \
    USE_ACCIDENTS, FACTOR_WEIGHTS
import accident_data.accidents_util as acd

# logging
log = logging.getLogger("Bikeability")
logging.basicConfig(
    filename="bikeability.log",
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S")


def fetch_network_edges(
        city: str) -> tuple[nx.MultiDiGraph, gpd.GeoDataFrame]:
    """
    Fetches network and it's edges for given city in EPSG:25832.
    """

    # get original network
    network = ox.graph_from_place(city, network_type="bike")

    # fetch the edges
    # network_edges = ox.graph_to_gdfs(network, nodes=False)

    # convert to EPSG:25832
    network = ox.project_graph(network, to_crs="EPSG:25832")
    # network_edges.to_crs("EPSG:25832", inplace=True)
    return network


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

def score_network(edges: pd.DataFrame(), scoring: pd.DataFrame()):
    length_modified = []
    scores_separation = []
    scores_surfaces = []
    geometries = []
    modifiers = []
    
    if USE_ACCIDENTS:
        accidents = acd.fetch_accidents(path = ACCIDENT_PATH)
        edges = acd.match_accidents_network(edges, accidents)
    
    for index, edge in edges.iterrows():
        # differentiate between single edges and edge lists
        if isinstance(edge.osmid, list):
            edge.osmid = edge.osmid
        else:
            edge.osmid = [edge.osmid]
        
        # find data corresponding to edge
        related_scores = scoring[scoring.id.isin(edge.osmid)]
        geometries.append(scoring["geometry"])
        
        
        
        if related_scores.size > 0:
            # If different scores belong to the same edge, the mean is used
            score_separation = related_scores.score_separation.mean().round()
            score_surface = related_scores.score_surface.mean().round()
            score_accident = edge.score_accident
            # Scale weight factors so they always accord to the same scaling
            factor_separation = FACTOR_WEIGHTS["separation"]
            factor_surface = FACTOR_WEIGHTS["surface"]
            factor_sum = 50 # The sum all weight factors for road suitability schould add up to
            # Factorise Scores and combine to edge score
            if USE_ACCIDENTS:
                factor_accidents = FACTOR_WEIGHTS["accidents"]
                sum_weights = sum([factor_separation, factor_surface,factor_accidents])
                factor_separation = factor_separation*factor_sum/sum_weights
                factor_surface = factor_surface*factor_sum/sum_weights
                factor_accidents = factor_accidents*factor_sum/sum_weights
                modifier = 1 + \
                    TRANSLATION_FACTORS["separation"][score_separation] * score_separation + \
                    TRANSLATION_FACTORS["surface"][score_surface] * factor_surface + \
                    TRANSLATION_FACTORS["accidents"][score_accident] * factor_accidents
            else:
                modifier = 1 + \
                    TRANSLATION_FACTORS["separation"][score_separation] * FACTOR_WEIGHTS["separation"] + \
                    TRANSLATION_FACTORS["surface"][score_surface] * FACTOR_WEIGHTS["surface"]
            modifiers.append(modifier)
            length_modified.append(edge.length * modifier)
            scores_separation.append(score_separation)
            scores_surfaces.append(score_surface)
        else:
            length_modified.append(9999999)
            modifiers.append(9999999)
            scores_separation.append(0)
            scores_surfaces.append(0)
            
    edges.insert(loc = 8, column = "length_modified", value = length_modified)
    edges.insert(loc = 8, column = "score_separation", value = scores_separation)
    edges.insert(loc = 8, column = "score_surface", value = scores_surfaces)
    edges.insert(loc = 8, column = "suitability_modifier", value = modifiers)
    
    if USE_ACCIDENTS:
        network = nx.from_pandas_edgelist(df = edges, 
                                          source = "source", 
                                          target = "target", 
                                          edge_attr = ["length", 
                                                       "length_modified",
                                                       "score_separation",
                                                       "score_surface",
                                                       "accident_count",
                                                       "suitability_modifier"])
    else:
        network = nx.from_pandas_edgelist(df = edges, 
                                          source = "source", 
                                          target = "target", 
                                          edge_attr = ["length", 
                                                       "length_modified",
                                                       "score_separation",
                                                       "score_surface",
                                                       "suitability_modifier"])

    return edges, network
    
    
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

def fill_holes_for_vis(edges: gpd.GeoDataFrame(), scoring: gpd.GeoDataFrame())-> gpd.GeoDataFrame():
    missing_geoms = edges[edges.geometry.isna()]
    scoring = scoring.to_crs("EPSG:25832")
    new_geoms = pd.merge(left = missing_geoms,
                         right = scoring[["id","geometry"]],
                         how = "left",
                         left_on = "osmid",
                         right_on = "id")
    new_geoms["geometry"] = new_geoms["geometry_y"]
    new_geoms.drop(columns = ["geometry_y", "geometry_x", "id"])
    new_geoms = gpd.GeoDataFrame(new_geoms, crs="EPSG:25832")
    
    edges = pd.concat([edges[~edges.geometry.isna()], new_geoms])
    edges = gpd.GeoDataFrame(edges, crs="EPSG:25832")
    edges = edges[~edges.geometry.isna()]
    return edges

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
    # Download OSM network for given city
    network = fetch_network_edges(CITY)
    log.info("Network and it's edges loaded... ")
    
    # Convert to dataframe for easier data handling
    edges = nx.to_pandas_edgelist(network)

    # Import osm metadata
    import_osm = import_osm()
    scoring, missing_scores = import_osm.score_osm(log, DEFAULT_SCORES)

    # match map- and metadata
    edges, network = score_network(edges, scoring)
    
        
    edges_for_vis = gpd.GeoDataFrame(edges, crs="EPSG:25832")
    
    edges_for_vis = fill_holes_for_vis(edges, scoring)
        
    scores_surface = edges_for_vis.explore(column = "score_surface", 
                                           cmap = "viridis", 
                                           vmin = 0, 
                                           vmax = 5)
        
    scores_separation = edges_for_vis.explore(column = "score_separation", 
                                              cmap = "viridis", 
                                              vmin = 0, 
                                              vmax = 5)
    
    accident_count = edges_for_vis.explore(column = "accident_count",
                                      cmap = "viridis",
                                      vmin = 0,
                                      vmax = 10)
    
    score_accident = edges_for_vis.explore(column = "score_accident",
                                      cmap = "viridis",
                                      vmin = 0, 
                                      vmax = 5)
    
    suitability_modifier = edges_for_vis.explore(column = "suitability_modifier",
                                      cmap = "viridis",
                                      vmin = 1, 
                                      vmax = 2)
    
    scores_surface.save(f"{EXPORT_PATH}/surface.html")
    scores_separation.save(f"{EXPORT_PATH}/separation.html")
    accident_count.save(f"{EXPORT_PATH}/accidents.html")
    score_accident.save(f"{EXPORT_PATH}/accidents_score.html")
    suitability_modifier.save(f"{EXPORT_PATH}/suitability_modifier.html")
    
    # Download OSM buildings chart
    buildings = fetch_buildings(CITY, network)
    log.info("Buildings loaded... ")

    # scores_surface = scoring.explore(column = "score_surface", 
    #                                   cmap = "viridis", vmin = 0, 
    #                                   vmax = 5, 
    #                                   tooltip = False, 
    #                                   popup = False)
    
    # scores_separation = scoring.explore(column = "score_separation", 
    #                                     cmap = "viridis", 
    #                                     vmin = 0, 
    #                                     vmax = 5, 
    #                                     tooltip = False, 
    #                                     popup = False)
    


    # for persona_POIs, persona_weight, persona_name in zip(POIS, PERSONA_WEIGHTS, PERSONA_NAMES):
    #     log.info(f"Starting calculations for {persona_name}... ")

    #     POIs = fetch_POIs(CITY, persona_POIs, network)
    #     log.info("Points of interest (POIs) loaded... ")

    #     dist_list = prepare_scoring(buildings, POIs, network, accidents)
    #     log.info("Distances from buildings to POIs calculated... ")

    #     score_list = score_routes(buildings, dist_list, persona_weight)
    #     log.info("Scores for routes calculated...")

    #     buildings = calc_building_scores(
    #         buildings, score_list, persona_weight)
    #     log.info("Building scores assigned!")

    #     export_scores(buildings, persona_name, network, EXPORT_PATH)
    #     log.info("Building scores saved!")
