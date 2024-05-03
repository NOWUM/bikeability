import logging

import geopandas as gpd
import pandas as pd
import networkx as nx
import osmnx as ox

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
        # Default value for cycleways is 5
        cycleways = network_osm["highway"] == "cycleway"
        bicycle_roads = network_osm["bicycle_road"] == "yes"
        scoring.loc[cycleways | bicycle_roads,
                    "score_separation"] = 5
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

        # missing scores for debugging purposes
        # if missing_scores is not empty, there is most likely a difference on how
        # osm data is handled locally
        missing_scores = network_osm[scoring["score_separation"] == -1]
        num_missing = missing_scores["id"].size
        if num_missing > 0:
            log.warning(f"{num_missing} elements couldn't be scored for separation. \
                        \n This is most likely due to an unknown exception in the data structure.")
            scoring.loc[scoring["score_separation"] == -1,
                        "score_separation"] = CONFIG.default_scores['surface']

            log.info(
                f"Replaced missing separation scores with default value {CONFIG['default_scores']['separation']}.")
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

        scoring.loc[network_osm["surface"].isin(["asphalt", "chipseal", "concrete",
                                                 "compacted", "tar", "1"]),
                    "score_surface"] = 5
        scoring.loc[network_osm["surface"].isin(["paved", "paving_stones", "bricks"]),
                    "score_surface"] = 4
        scoring.loc[network_osm["surface"].isin(["sett", "cobblestone", "metal",
                                                 "wood", "fine_gravel", "steel",
                                                 "grass_paver"]),
                    "score_surface"] = 3
        scoring.loc[network_osm["surface"].isin(["rock", "dirt", "ground", "grit",
                                                 "earth", "clay", "unpaved", "mud"]),
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
        unknown_scores = network_osm[unscored & ~missing_data]

        num_unknown = unknown_scores["id"].size
        if num_unknown > 0:
            log.warning(f"{num_unknown} elements couldn't be scored for surface area \
                        \n due to unknown values. The default value {CONFIG['default_scores']['surface']} is used.")

        num_missing = missing_scores["id"].size
        if num_missing > 0:
            log.info(f"{num_missing} elements couldn't be scored for surface area \
                     \n due to insufficient data. The default value {CONFIG['default_scores']['surface']} is used.")

        scoring.loc[scoring["score_surface"] == -1,
                    "score_surface"] = CONFIG['default_scores']['surface']
        return scoring, missing_scores

    def import_network(self, osm: pyrosm.OSM, log: logging.Logger, CONFIG: dict) -> pd.DataFrame():
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

    def score_suitability(self, edges: pd.DataFrame(), network: nx.MultiDiGraph(), scoring: pd.DataFrame(), CONFIG: dict):
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
                transation_factors = CONFIG['translation_factors']
                score_separation = related_scores.score_separation.mean().round()
                score_surface = related_scores.score_surface.mean().round()
                score_accident = edge.score_accident
                # Scale weight factors so they always accord to the same scaling
                factor_separation = factor_weights["separation"]
                factor_surface = factor_weights["surface"]
                factor_sum = 50  # The sum all weight factors for road suitability schould add up to
                # Factorise Scores and combine to edge score
                if CONFIG['use_accidents']:
                    factor_accidents = factor_weights["accidents"]
                    sum_weights = sum(
                        [factor_separation, factor_surface, factor_accidents])
                    factor_separation = factor_separation*factor_sum/sum_weights
                    factor_surface = factor_surface*factor_sum/sum_weights
                    factor_accidents = factor_accidents*factor_sum/sum_weights
                    modifier = 1 + \
                        transation_factors["separation"][score_separation] * score_separation + \
                        transation_factors["surface"][score_surface] * factor_surface + \
                        transation_factors["accidents"][score_accident] * \
                        factor_accidents
                else:
                    modifier = 1 + \
                        transation_factors["separation"][score_separation] * factor_weights["separation"] + \
                        transation_factors["surface"][score_surface] * \
                        factor_weights["surface"]
                modifiers.append(modifier)
                length_modified.append(edge.length * modifier)
                scores_separation.append(score_separation)
                scores_surfaces.append(score_surface)
            else:
                length_modified.append(9999999)
                modifiers.append(9999999)
                scores_separation.append(0)
                scores_surfaces.append(0)

        edges.insert(loc=8, column="length_modified", value=length_modified)
        edges.insert(loc=8, column="score_separation", value=scores_separation)
        edges.insert(loc=8, column="score_surface", value=scores_surfaces)
        edges.insert(loc=8, column="suitability_modifier", value=modifiers)

        edges_import = edges[["source",
                              "target",
                              "length",
                              "length_modified",
                              "score_separation",
                              "score_surface",
                              "accident_count",
                              "suitability_modifier"]]
        edges_import.set_index(["source", "target"], inplace=True)
        edges_import = edges_import.T
        dict4network = edges_import.to_dict()

        if CONFIG['use_accidents']:
            network = nx.from_pandas_edgelist(df=edges,
                                              source="source",
                                              target="target",
                                              edge_attr=["length",
                                                         "length_modified",
                                                         "score_separation",
                                                         "score_surface",
                                                         "accident_count",
                                                         "suitability_modifier"],
                                              create_using=nx.MultiDiGraph())
        else:
            network = nx.from_pandas_edgelist(df=edges,
                                              source="source",
                                              target="target",
                                              edge_attr=["length",
                                                         "length_modified",
                                                         "score_separation",
                                                         "score_surface",
                                                         "suitability_modifier"],
                                              create_using=nx.MultiDiGraph())

        return edges, network

    def fill_geometry(self, edges: gpd.GeoDataFrame(), scoring: gpd.GeoDataFrame()) -> gpd.GeoDataFrame():
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

    def eval_suitability(self, CONFIG: dict):
        """
        

        Parameters
        ----------
        log : logging.logger
            Relevant log file.
        DEFAULT : dict
            Dictionary of default values for scoring.

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
        edges = nx.to_pandas_edgelist(network)

        fp = "C:\\Users\\jk2932e\\Python Projects\\bikeability\\pyrosm\\Aachen.osm.pbf"
        osm = pyrosm.OSM(fp)

        # import OSM network to access metadata
        network_osm = self.import_network(osm, log, CONFIG)

        # initialise scoring dataframe
        scoring = network_osm[["name", "id", "tags", "osm_type", "geometry",
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

        edges, network = self.score_suitability(
            edges, network, scoring, CONFIG)
        edges = self.fill_geometry(edges, scoring)

        return edges, network
