# -*- coding: utf-8 -*-
"""
Created on Wed Nov 15 12:25:41 2023

@author: jk2932e
"""

import networkx as nx
import numpy as np
import pandas as pd
import osmnx as ox
import geopandas as gpd
import os
from typing import List


def calc_shortest_path_length(
        end_node: int,
        start_node: int,
        network: nx.MultiDiGraph) -> float:
    """
    Calculates the length in metres of the shortest path between two points in the
    network.
    """
    return nx.shortest_path_length(
        G=network,
        source=start_node,
        target=end_node,
        weight="length")


def calc_shortest_path(
        end_node: int,
        start_node: int,
        network: nx.MultiDiGraph) -> float:
    """
    Calculates the shortest path between two points in the network as a series
    of nodes.
    """
    return nx.shortest_path(
        G=network,
        source=start_node,
        target=end_node,
        weight="length")


def sigmoid(x: np.array) -> np.array:
    """
    Function for transforming values using a distance decay function.

    Parameters
    ----------
    x : np.array
        Array of values to apply the sigmoid function to.

    Returns
    -------
    result : np.array
        Array of values according to distance decay.

    """
    x = 0.000621371*x  # Umrechnung in Meilen
    result = -1.80644093e+02 * x**5 + 5.91165958e+02 * x**4 - 5.33162397e+02 * \
        x**3 + 3.33386213e+0 * x**2 - 9.41291973e-02 * x + 1.02061531e+02
    result[result > 100] = 100
    result[result < 0] = 0
    return result


def calc_score(
        route_distance: List[float],
        weight_factor: List[int]) -> np.array:
    """
    Function to calculate a walk score using a distance decay function and 
    weight factors.

    Parameters
    ----------
    route_distance : List[float]
        List of distances.
    weight_factor : List[int]
        List of weight factors.

    Returns
    -------
    score: np.array
        Array of scores.

    """

    route_distance = np.array(route_distance)
    weight_factor = np.array(weight_factor)

    score = np.outer(sigmoid(route_distance), weight_factor)
    return score


def format_score(weight_factor: List[int],
                 score: np.array,
                 ind: List[int]) -> pd.DataFrame:
    """
    Function to format the walk score values

    Parameters
    ----------
    weight_factor : List[int]
        list of weight factors.
    score : np.array
        array of scores.
    ind : List[int]
        indices for building table.

    Returns
    -------
    POI_scores : pd.DataFrame
        dataframe containing scores for the specified array.

    """
    col = []
    for i in range(len(weight_factor)):
        col.append(f"score_{str(i+1)}")

    POI_scores = pd.DataFrame(
        data=score,
        index=ind,
        columns=col)

    return POI_scores


def accident_score(accident_count: pd.Series) -> pd.Series:
    """
    Function to convert the numbers of accidents on a route to factors between
    0 and 1 to modify distance-dependant walkability scores.

    Parameters
    ----------
    accident_count : pd.Series
        Series of the numbers of accidents on specific routes.

    Returns
    -------
    accident_scores : pd.Series
        Series of score modifiers relating to the specified accident counts.

    """
    accident_scores = pd.to_numeric(arg=accident_count, downcast="float")
    accident_scores = accident_scores * 0.0
    accident_scores[accident_count == 0] = 1
    accident_scores[accident_count == 1] = 0.98
    accident_scores[accident_count == 2] = 0.97
    accident_scores[accident_count > 2] = 0.95

    return accident_scores

def make_export_dir(path: str):
    """
    Creates the export dictionary.

    """
    # check if directory exists
    dir_exist = os.path.exists(path)
    # create directory if it doesn't exist
    if not dir_exist:
        os.makedirs(path)

    shp_exist = os.path.exists(f'{path}/shp')

    if not shp_exist:
        os.makedirs(f'{path}/shp')


def visualize_scores(network: nx.MultiDiGraph,
                     buildings: gpd.GeoDataFrame) -> nx.MultiDiGraph:
    """
    Converts street network and building list into leaflet map.

    Parameters
    ----------
    network : nx.MultiDiGraph
        Node-Edge-Network of the relevant area.
    buildings : gpd.GeoDataFrame
        Dataframe containing a list of buildings with corresponding walk scores.

    Returns
    -------
    vis : TYPE
        Map of buildings and street network with color-coded walk scores.

    """
    # convert node-edge-model to multidigraph
    network_gdfs = ox.graph_to_gdfs(network)
    # project multidigraph as interactive leaflet map
    network_map = network_gdfs[1].explore(tooltip = False, highligh = False)
    vis = buildings.explore(m = network_map,
                            column = 'score',
                            cmap = 'viridis',
                            vmin = 0,
                            vmax = 100)
    return vis
