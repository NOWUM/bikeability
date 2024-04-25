import logging

import geopandas as gpd
import pandas as pd

import pyrosm
from bikeability_config import DEFAULT_SCORES, IGNORED_TYPES

log = logging.getLogger('Bikeability')
# test = pyrosm.get_data("Aachen")
# print(test)

# Default values for scoring paths. These values are used when no more specific
# value can be determined. Useful defaults very for each city. 


class import_osm():
    def score_route_separation(self, network_osm: pd.DataFrame, scoring: pd.DataFrame):
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
        cycleways = network_osm["highway"]=="cycleway"
        bicycle_roads = network_osm["bicycle_road"]=="yes"
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
                    "score_separation"] = 3 # this does not work
        scoring.loc[network_osm["highway"].isin(["track", "bridleway", "footway", "path"]), 
                    "score_separation"] = 4
        
        scoring.loc[network_osm["cycleway"].isin(["no", "shared_lane"]), 
                    "score_separation"] = 1
        scoring.loc[network_osm["cycleway"]=="opposite_lane", 
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
                    "score_separation"] = DEFAULT_SCORES['surface']
        
            log.info(f"Replaced missing separation scores with default value {DEFAULT_SCORES['separation']}.")
        return scoring, missing_scores
    
    def score_route_surfaces(self, network_osm: pd.DataFrame, scoring: pd.DataFrame):
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
        
        network_osm.loc[network_osm["surface"].str.contains("cobblestone", na = False),
                        "surface"] = "cobblestone"
        network_osm.loc[network_osm["surface"].str.contains("asphalt", na = False),
                        "surface"] = "asphalt"
        network_osm.loc[network_osm["surface"].str.contains("concrete", na = False),
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
        generalise = network_osm["surface"].str.split(pat = ";", n = 1, expand = True)
        network_osm.loc[:,"surface"] = generalise[0]
        generalise = network_osm["surface"].str.split(pat = ":", n = 1, expand = True)
        network_osm.loc[:,"surface"] = generalise[0]
        
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
        scoring.loc[network_osm["smoothness"].isin(["bad","very_bad"]),
                    "score_surface"] = 2
        scoring.loc[network_osm["smoothness"].isin(["horrible", "very_horrible"]),
                    "score_surface"] = 1
        
        # if the sidepath isn's documented separately, it's surface is unknown
        scoring.loc[network_osm["bicycle"].isin(["use_sidepath", "optional_sidepath"]),
                    "score_surface"] = 3
        # filter out impassable areas
        scoring.loc[network_osm["smoothness"].isin(["impassable"]),
                    "score_surface"] = 0
        
        missing_data = network_osm.smoothness.isnull() & network_osm.surface.isnull() & network_osm.tracktype.isnull()
        unscored = scoring["score_surface"] == -1
        
        missing_scores = network_osm[unscored & missing_data]
        unknown_scores = network_osm[unscored & ~missing_data]
        
        num_unknown = unknown_scores["id"].size
        if num_unknown > 0:
            log.warning(f"{num_unknown} elements couldn't be scored for surface area \
                        \n due to unknown values. The default value {DEFAULT_SCORES['surface']} is used.")
        
        num_missing = missing_scores["id"].size
        if num_missing > 0:
            log.info(f"{num_missing} elements couldn't be scored for surface area \
                     \n due to insufficient data. The default value {DEFAULT_SCORES['surface']} is used.")
        
        scoring.loc[scoring["score_surface"] == -1, 
                        "score_surface"] = DEFAULT_SCORES['surface']
        return scoring, missing_scores
    
    def score_route_traffic(network_osm: pd.DataFrame, scoring: pd.DataFrame):
        scoring.insert(1, "score_surface", -1)
        
    
    def score_osm(self, log, DEFAULT):
        log.info("Starting to download osm network data!")
        fp = "C:\\Users\\jk2932e\\Python Projects\\bikeability\\pyrosm\\Aachen.osm.pbf"
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
        network_osm = network_osm[~network_osm["highway"].isin(IGNORED_TYPES)]
        bicycle_forbidden = ["no", "separate", "private"]
        network_osm = network_osm[~network_osm["bicycle"].isin(bicycle_forbidden)]
        
        # these areas can be accessed but are inconvenient to  aren't filtered out, 
        # but their legibility for biking is questionable
        # additional options: "delivery", "destination"
        bicycle_restricted = ["limited", "permit", "dismount"]
        # everything else (including none-type values) is bikeable by default
        network_osm.insert(2, "rightofway", "Yes")
        network_osm.loc[network_osm["bicycle"].isin(bicycle_restricted), "rightofway"] = "No"
        # bus lanes are only bikeable if explicitly mentioned
        network_osm.loc[network_osm["highway"].isin(["bus", "busway"]) &~ 
                        network_osm["bicycle"].isin(["Yes"]), 
                        "rightofway"] = "No"
        # Remove links by using them as their parent type
        parents = network_osm["highway"].str.split(pat = "_", n = 1, expand = True)
        network_osm.loc[:,"highway"] = parents[0]
        log.info("Successfully filtered OSM data for handling!")
        
        scoring = network_osm[["name", "id", "tags", "osm_type", "geometry",
        "length"]]
    
        log.info("Starting to score for separation!")
        scoring, missing_scores = self.score_route_separation(
                                                    network_osm = network_osm,
                                                    scoring = scoring)
        
        log.info("Successfully scored for separation. Starting to score for surface area!")
        scoring, missing_scores = self.score_route_surfaces(
                                                    network_osm = network_osm,
                                                    scoring = scoring)
        return scoring, missing_scores

logging.basicConfig(
    filename="bikeability.log",
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',
)

#TODO alle Fälle rausarbeiten und scoren.