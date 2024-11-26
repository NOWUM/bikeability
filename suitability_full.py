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

CONFIG["city"] = "nordrhein_westfalen"

logging.basicConfig(
    filename="bikeability.log",
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S")

# calculate suitability
suitability = Suitability()
edges, network = suitability.eval_suitability(CONFIG)
log.info("Suitability network completed. Loading buildings... ")
