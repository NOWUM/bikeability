import logging

import geopandas as gpd
import pandas as pd
import networkx as nx
import osmnx as ox

import os
import pyrosm
import accident_data.accidents_util as acd
log = logging.getLogger('Bikeability')
# test = pyrosm.get_data("Aachen")
# print(test)W

# Default values for scoring paths. These values are used when no more specific
# value can be determined. Useful defaults very for each city.


class Suitability():
    def fetch_network_edges(self,
                            city: str) -> nx.MultiDiGraph:
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

    def score_route_separation(self, network_osm: pd.DataFrame, scoring: pd.DataFrame, CONFIG: dict):
        '''
        This function scores osm paths for separation of cyclists from other forms
        of traffic. 
    
        Parameters
        ----------
        network_osm : pd.DataFrame
            OSM path network for the relevant area.
        scoring : pd.DataFrame
            Dataframe relating to the path network in which the scores can be 
            inserted.
    
        Returns
        -------
        scoring : pd.DataFrame
            The scoring dataframe including separation scores.
        missing_scores : TYPE
            A Fraction of the network dataframe with any paths that couldn't be 
            scored, so new exceptions in the osm datas structure can be identified. 
    
        '''
        scoring.insert(1, "score_separation", -1)

        
        # Default value for motorways areas is 0
        scoring.loc[network_osm["highway"].isin(["motorway"]),
                    "score_separation"] = 0
        # 2 is the default for unclassified highways
        scoring.loc[network_osm["highway"].isin(["unclassified"]),
                    "score_separation"] = 2

        # Scoring takes place from least specific to most specific

        # A bikeable sidepath is better than the road but worse than a separate cycleway
        scoring.loc[network_osm["bicycle"].isin(["use_sidepath", "optional_sidepath"]),
                    "score_separation"] = 3

        # scoring by "highway", which classifies the kind of way
        scoring.loc[network_osm["highway"].isin(["primary", "secondary", "rest"]),
                    "score_separation"] = 1
        scoring.loc[network_osm["highway"].isin(["tertiary", "trunk", "residential", "road", "bus", "busway", "construction"]),
                    "score_separation"] = 2
        scoring.loc[network_osm["highway"].isin(["living_street", "services", "service",
                                                 "pedestrian", "living", "steps"]),
                    "score_separation"] = 3  # this does not work
        scoring.loc[network_osm["highway"].isin(["track", "bridleway", "footway", "path"]),
                    "score_separation"] = 4

        scoring.loc[network_osm["cycleway"].isin(["no", "shared_lane"]),
                    "score_separation"] = 1
        scoring.loc[network_osm["cycleway"] == "opposite_lane",
                    "score_separation"] = 2
        scoring.loc[network_osm["cycleway"].isin(["lane", "buffer", "opposite", "opposite_share_busway"]),
                    "score_separation"] = 3
        scoring.loc[network_osm["cycleway"].isin(["share_busway", "track", "opposite_track"]),
                    "score_separation"] = 4
                
        cycleways = (network_osm["highway"] == "cycleway") | (network_osm["bicycle_road"] == "yes")
        motor_traffic = network_osm["motor_vehicle"] == "yes"
        scoring.loc[cycleways & motor_traffic,
                    "score_separation"] = 4
        
        scoring.loc[cycleways & ~motor_traffic,
                    "score_separation"] = 5
        
        # missing scores for debugging purposes
        # if missing_scores is not empty, there is most likely a difference on how
        # osm data is handled locally
        missing_scores = network_osm[scoring["score_separation"] == -1]
        num_missing = missing_scores["id"].size
        if num_missing > 0:
            scoring = self.fill_in_scores(scoring, CONFIG, "separation")
        #     log.warning(f"{num_missing} elements couldn't be scored for separation. \
        #                 \n This is most likely due to an unknown exception in the data structure.")
        #     scoring.loc[scoring["score_separation"] == -1,
        #                 "score_separation"] = CONFIG["default_scores"]['separation']

        #     log.info(
        #         f"Replaced missing separation scores with default value {CONFIG['default_scores']['separation']}.")
        return scoring, missing_scores

    def score_route_surfaces(self, network_osm: pd.DataFrame, scoring: gpd.GeoDataFrame, CONFIG: dict) -> tuple():
        '''
        This function scores osm paths for the surface quality of cycling 
        infrastructure.
    
        Parameters
        ----------
        network_osm : pd.DataFrame
            OSM path network for the relevant area.
        scoring : pd.DataFrame
            Dataframe relating to the path network in which the scores can be 
            inserted.
    
        Returns
        -------
        scoring : pd.DataFrame
            The scoring dataframe including surface scores.
        missing_scores : TYPE
            A Fraction of the network dataframe with any paths that couldn't be 
            scored, so new exceptions in the osm datas structure can be identified. 
    
        '''
        scoring.insert(1, "score_surface", -1)

        # network_osm = network_osm[["bicycle", "rightofway", "smoothness", "surface", "tracktype"]]

        network_osm.loc[network_osm["surface"].str.contains("cobblestone", na=False),
                        "surface"] = "cobblestone"
        network_osm.loc[network_osm["surface"].str.contains("asphalt", na=False),
                        "surface"] = "asphalt"
        network_osm.loc[network_osm["surface"].str.contains("concrete", na=False),
                        "surface"] = "concrete"

        # scoring by tracktype
        # it's a common variation in osm to write "1" instead of "grade1", so this
        # exception is recognised here
        scoring.loc[network_osm["tracktype"].isin(["1", "grade1"]),
                    "score_surface"] = 5
        scoring.loc[network_osm["tracktype"].isin(["2", "grade2"]),
                    "score_surface"] = 4
        scoring.loc[network_osm["tracktype"].isin(["3", "grade3"]),
                    "score_surface"] = 3
        scoring.loc[network_osm["tracktype"].isin(["4", "grade4"]),
                    "score_surface"] = 2
        scoring.loc[network_osm["tracktype"].isin(["5", "grade5"]),
                    "score_surface"] = 1

        # scoring by surface type

        # remove unneeded specifications
        generalise = network_osm["surface"].str.split(
            pat=";", n=1, expand=True)
        network_osm.loc[:, "surface"] = generalise[0]
        generalise = network_osm["surface"].str.split(
            pat=":", n=1, expand=True)
        network_osm.loc[:, "surface"] = generalise[0]

        scoring.loc[network_osm["surface"].isin(["asphalt", "concrete",
                                                 "compacted", "tar", "1"]),
                    "score_surface"] = 5
        scoring.loc[network_osm["surface"].isin(["paved", "paving_stones", 
                                                 "bricks"]),
                    "score_surface"] = 4
        scoring.loc[network_osm["surface"].isin(["sett", "metal",
                                                 "wood", "chipseal", 
                                                 "fine_gravel", "steel",
                                                 "grass_paver"]),
                    "score_surface"] = 3
        scoring.loc[network_osm["surface"].isin(["rock", "dirt", "ground", "grit",
                                                 "earth", "clay", "unpaved", "mud", 
                                                 "cobblestone"]),
                    "score_surface"] = 2
        scoring.loc[network_osm["surface"].isin(["gravel", "grass", "metal_grid",
                                                 "mud", "sand", "woodchips",
                                                 "pebblestone"]),
                    "score_surface"] = 1
        scoring.loc[network_osm["surface"].isin(["stepping_stones"]),
                    "score_surface"] = 0

        # scoring by smoothness
        scoring.loc[network_osm["smoothness"].isin(["excellent"]),
                    "score_surface"] = 5
        scoring.loc[network_osm["smoothness"].isin(["good"]),
                    "score_surface"] = 4
        scoring.loc[network_osm["smoothness"].isin(["intermediate"]),
                    "score_surface"] = 3
        scoring.loc[network_osm["smoothness"].isin(["bad", "very_bad"]),
                    "score_surface"] = 2
        scoring.loc[network_osm["smoothness"].isin(["horrible", "very_horrible"]),
                    "score_surface"] = 1

        # if the sidepath isn's documented separately, it's surface is unknown
        scoring.loc[network_osm["bicycle"].isin(["use_sidepath", "optional_sidepath"]),
                    "score_surface"] = 3
        # filter out impassable areas
        scoring.loc[network_osm["smoothness"].isin(["impassable"]),
                    "score_surface"] = 0

        

        missing_data = network_osm.smoothness.isnull(
        ) & network_osm.surface.isnull() & network_osm.tracktype.isnull()
        unscored = scoring["score_surface"] == -1

        missing_scores = network_osm[unscored & missing_data]

        num_missing = missing_scores["id"].size
        if num_missing > 0:
            scoring = self.fill_in_scores(scoring, CONFIG, "surface")
        #     log.warning(f"{num_unknown} elements couldn't be scored for surface area \
        #                 \n due to unknown values. The default value {CONFIG['default_scores']['surface']} is used.")

        # num_missing = missing_scores["id"].size
        # if num_missing > 0:
        #     log.info(f"{num_missing} elements couldn't be scored for surface area \
        #              \n due to insufficient data. The default value {CONFIG['default_scores']['surface']} is used.")

        # scoring.loc[scoring["score_surface"] == -1,
        #             "score_surface"] = CONFIG['default_scores']['surface']
        return scoring, missing_scores
    
    def complete_road_related(self, scoring: pd.DataFrame(), score: pd.Series(), score_type: str(), CONFIG: dict(), type_defaults: pd.DataFrame()) -> pd.Series():
        related_scores = scoring.loc[scoring.name.isin([score["name"]]), f"score_{score_type}"]
        related_scores = related_scores[related_scores!=-1]
        if related_scores.size >= 1:
            score[f"score_{score_type}"] = round(related_scores.mean())
        else:
            score[f"score_{score_type}"] = type_defaults.loc[score["highway"], score_type]
        return  score
    
    def fill_in_scores(self, scoring: pd.DataFrame, CONFIG: dict, score_type: str):
        scoring_full = scoring
        type_defaults = pd.DataFrame()
        highwaytypes = scoring.highway.unique()
        type_defaults.insert(0, score_type, -1)
        for highwaytype in highwaytypes:
            scores_of_type = scoring.loc[scoring.highway.isin([highwaytype]), f"score_{score_type}"]
            highwaytype_set_scores = scores_of_type[scores_of_type != -1]
            if highwaytype_set_scores.size > 0:
                highwaytype_default = round(highwaytype_set_scores.mean())
                type_defaults.loc[highwaytype, score_type] = highwaytype_default
            else:
                type_defaults.loc[highwaytype, score_type] = CONFIG["default_scores"][score_type]
            # type_defaults.loc[highwaytype, score_type] = round(scores_of_type[scores_of_type != -1].mean())

        for index, score in scoring_full.iterrows():
            if score[f"score_{score_type}"] == -1:
                score = self.complete_road_related(scoring, score, score_type, CONFIG, type_defaults)
                scoring_full.loc[index] = score
        return scoring_full


        
        # highwaytypes = scoring.highway.unique()
        # type_defaults = pd.DataFrame()
        # type_defaults.insert(0, "surface", -1)
        # type_defaults.insert(1, "separation", -1)
        # for highwaytype in highwaytypes:
        #     surfaces_of_type = scoring.loc[scoring.highway.isin([highwaytype]), "score_surface"]
        #     separation_of_type = scoring.loc[scoring.highway.isin([highwaytype]), "score_separation"]
        #     type_defaults.loc[highwaytype, "surface"] = round(surfaces_of_type[surfaces_of_type != -1].mean())
        #     type_defaults.loc[highwaytype, "separation"] = round(separation_of_type[surfaces_of_type != -1].mean())
            
        # for index, score in scoring_full.iterrows():
        #     if score.score_surface == -1:
        #         score = self.complete_road_related(scoring, score, "surface", CONFIG, type_defaults)
        #     if score.score_separation == -1:
        #         score = self.complete_road_related(scoring, score, "separation", CONFIG, type_defaults)
            
    def import_network(self, CONFIG: dict) -> pd.DataFrame():
        """
        Imports and filters the road network from osm.
    
        Parameters
        ----------
        osm : pyrosm.OSM
            Pyrosm OSM reference object.
        log : logging.Logger
            Log file.
        CONFIG: dict
            Dictionary of configuration options and static variables for bikeability calculation.
    
        Returns
        -------
        network_osm : pd.DataFrame()
            Dataframe containing OSM map- and metadata that is relevant for calculating bikeability.
            
        """
        city = CONFIG["city"].split(",")[0]
        fp = f"pyrosm/{city}.osm.pbf"
        if not os.path.isfile(fp):
            fp = pyrosm.get_data(city, directory = "pyrosm")
        
        osm = pyrosm.OSM(fp)
        
        network_osm = osm.get_network("cycling")
        log.info("Successfully downloaded osm network data!")

        # Filter out irrelevant values
        network_osm = network_osm[["bicycle", "bicycle_road", "cycleway",
                                   "est_width", "foot", "footway", "highway",
                                   "junction", "lanes", "lit", "maxspeed",
                                   "name", "oneway", "segregated", "sidewalk",
                                   "smoothness", "surface", "tracktype",
                                   "motor_vehicle", "width", "id", "tags",
                                   "osm_type", "geometry", "length"]]

        # Filter out illegal ways not caught by pyrosm
        network_osm = network_osm[~network_osm["highway"].isin(
            CONFIG['ignored_types'])]
        bicycle_forbidden = ["no", "separate", "private"]
        network_osm = network_osm[~network_osm["bicycle"].isin(
            bicycle_forbidden)]

        # these areas can be accessed but are inconvenient to  aren't filtered out,
        # but their legibility for biking is questionable
        # additional options: "delivery", "destination"
        bicycle_restricted = ["limited", "permit", "dismount"]
        # everything else (including none-type values) is bikeable by default
        network_osm.insert(2, "rightofway", "Yes")
        network_osm.loc[network_osm["bicycle"].isin(
            bicycle_restricted), "rightofway"] = "No"
        # bus lanes are only bikeable if explicitly mentioned
        network_osm.loc[network_osm["highway"].isin(["bus", "busway"]) & ~
                        network_osm["bicycle"].isin(["Yes"]),
                        "rightofway"] = "No"
        # Remove links by using them as their parent type
        parents = network_osm["highway"].str.split(pat="_", n=1, expand=True)
        network_osm.loc[:, "highway"] = parents[0]
        log.info("Successfully filtered OSM data for handling!")

        return network_osm

    def suitability_to_network(self, nodes: gpd.GeoDataFrame(), edges: gpd.GeoDataFrame(), network: nx.MultiDiGraph(), scoring: pd.DataFrame(), CONFIG: dict):
        """
        Calculates the bicycle suitability scores of a road network by 
        combining scores for surface quality and separation to an overall score. 
        
        If it is enabled in CONFIG, accident data is evaluated as well.
        
        Parameters
        ----------
        nodes : gpd.GeoDataFrame()
            List of nodes in the network.
        edges : gpd.GeoDataFrame()
            List of edges in the network.
        network : nx.MultiDiGraph()
            Complete osm network.
        scoring : pd.DataFrame()
            Dataframe containing scoring for the relevant roads.
        CONFIG : dict
            Dictionary of configuration options and static variables for bikeability calculation.

        Returns
        -------
        edges : pd.DataFrame()
            List of edges in the network with corresponding suitability scores.
        network : nx.MultiDiGraph()
            Road network with added suitability metadata.

        """
        length_modified = []
        scores_separation = []
        scores_surfaces = []
        geometries = []
        modifiers = []

        if CONFIG['use_accidents']:
            accidents = acd.fetch_accidents(path=CONFIG['accident_path'])
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
                factor_weights = CONFIG['factor_weights']
                translation_factors = CONFIG['translation_factors']
                score_separation = related_scores.score_separation.mean().round()
                score_surface = related_scores.score_surface.mean().round()
                if CONFIG['use_accidents']:
                    score_accident = edge.score_accident
                # Scale weight factors so they always accord to the same scaling
                factor_separation = factor_weights["separation"]
                factor_surface = factor_weights["surface"]
                # Factorise Scores and combine to edge score
                if CONFIG['use_accidents']:
                    factor_accidents = factor_weights["accidents"]
                    modifier = 1 - \
                        translation_factors["separation"][score_separation] * factor_separation - \
                        translation_factors["surface"][score_surface] * factor_surface - \
                        translation_factors["accidents"][score_accident] * factor_accidents
                else:
                    modifier = 1 - \
                        translation_factors["separation"][score_separation] * factor_separation - \
                        translation_factors["surface"][score_surface] * factor_surface
                if modifier < 0.1:
                    modifier = 0.1
                modifiers.append(modifier)
                length_modified.append(edge.length / modifier)
                scores_separation.append(score_separation)
                scores_surfaces.append(score_surface)
            else:
                modifier = 0.01
                length_modified.append(edge.length / modifier)
                modifiers.append(modifier)
                scores_separation.append(0)
                scores_surfaces.append(0)

        edges.insert(loc=8, column="length_modified", value=length_modified)
        edges.insert(loc=8, column="score_separation", value=scores_separation)
        edges.insert(loc=8, column="score_surface", value=scores_surfaces)
        edges.insert(loc=8, column="suitability_modifier", value=modifiers)
        
        network = ox.graph_from_gdfs(nodes, edges)
        network = ox.project_graph(network, to_crs="EPSG:25832")
        
        #remove isolated nodes
        network.remove_nodes_from(list(nx.isolates(network)))
        
        #remove island networks not connected to main network
        network = ox.truncate.largest_component(network)
        return edges, network

    def fill_geometry(self, edges: gpd.GeoDataFrame(), scoring: gpd.GeoDataFrame()) -> gpd.GeoDataFrame():
        
        """
        Fills out missing geometries in the network for later visualisation
        
        Parameters
        ----------
        edges : pd.DataFrame()
            List of edges in the network.
        scoring : pd.DataFrame()
            Dataframe containing scoring for the relevant roads.
            
        Returns
        -------
        edges : pd.DataFrame()
            List of edges in the network with more complete geographic information.
        """
        missing_geoms = edges[edges.geometry.isna()]
        scoring = scoring.to_crs("EPSG:25832")
        new_geoms = pd.merge(left=missing_geoms,
                             right=scoring[["id", "geometry"]],
                             how="left",
                             left_on="osmid",
                             right_on="id")
        new_geoms["geometry"] = new_geoms["geometry_y"]
        new_geoms.drop(columns=["geometry_y", "geometry_x", "id"])
        new_geoms = gpd.GeoDataFrame(new_geoms, crs="EPSG:25832")

        edges = pd.concat([edges[~edges.geometry.isna()], new_geoms])
        edges = gpd.GeoDataFrame(edges, crs="EPSG:25832")

        return edges
    
    def remove_ignored_types(self, nodes: gpd.GeoDataFrame, edges: gpd.GeoDataFrame, CONFIG: dict):
        """
        Removes specified edges from the network and cleans up remaining nodes afterwards

        Parameters
        ----------
        nodes : gpd.GeoDataFrame
            Dataframe of the network nodes.
        edges : gpd.GeoDataFrame
            Dataframe of the network edges.
        CONFIG : dict
            Dictionary of configuration options and static variables for bikeability calculation.

        Returns
        -------
        nodes : gpd.GeoDataFrame
            Dataframe of the network nodes that weren't exclusively connected to ignored roads.
        edges : gpd.GeoDataFrame
            List of edges that don't belong to an ignored road type.

        """
        edges = edges[~edges.highway.isin(CONFIG["ignored_types"])]
        from_nodes = edges.index.get_level_values(0)
        to_nodes = edges.index.get_level_values(1)
        valid_nodes = from_nodes.append(to_nodes)
        valid_nodes = valid_nodes.unique()
        
        nodes = nodes.loc[nodes.index.isin(valid_nodes)]
        return nodes, edges

    def eval_suitability(self, CONFIG: dict):
        """
        Downloads a road network for a specified city and scores it for
        

        Parameters
        ----------
        log : logging.logger
            Relevant log file.
        CONFIG : dict
            Dictionary of configuration options and static variables for bikeability calculation.

        Returns
        -------
        scoring : gpd.GeoDataFrame
            Dataframe with scored edges in the OSM network.
        missing_scores : gpd.GeoDataFrame
            Dataframe with the edges that couldn't be scored.

        """
        log.info("Starting to download osm network data!")

        # Download OSM network for given city
        network = self.fetch_network_edges(CONFIG['city'])
        log.info("Network and it's edges loaded... ")

        # Convert to dataframe for easier data handling
        # network direkt suitability übergeben
        nodes, edges = ox.graph_to_gdfs(network)

        nodes, edges = self.remove_ignored_types(nodes, edges, CONFIG)
    
        # import OSM network to access metadata
        network_osm = self.import_network(CONFIG)

        # initialise scoring dataframe
        scoring = network_osm[["name", "id", "tags", "osm_type", "highway", "geometry",
                               "length"]]

        log.info("Starting to score for separation!")
        scoring, missing_scores = self.score_route_separation(
            network_osm=network_osm,
            scoring=scoring,
            CONFIG=CONFIG)

        log.info(
            "Successfully scored for separation. Starting to score for surface area!")
        scoring, missing_scores = self.score_route_surfaces(
            network_osm=network_osm,
            scoring=scoring,
            CONFIG=CONFIG)
        log.info(
            "Successfully scored for surface area.")
        edges, network = self.suitability_to_network(nodes,
            edges, network, scoring, CONFIG)
        edges.sort_index(inplace = True)
        
        return edges, network
