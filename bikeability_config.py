USE_ACCIDENTS = False
VISUALIZE = False
ACCIDENT_PATH = "accident_data/accidents_bike.h5"
PBF_PATH = ".\\pyrosm\\Duisburg.osm.pbf"
EXPORT_PATH = "results"
CITY = "Duisburg, Germany"



DEFAULT_SCORES = {'separation': 2,
                  'surface': 2,
                  'traffic': 3}

# translation scores to mathematical modifiers for route score

# Weighting different factors for bikeability against each other
FACTOR_WEIGHTS = {"separation": 2,
                  "surface": 1,
                  "traffic": 1,
                  "accidents": 0.5}

# mathematical impact of different levels of service
# The numbers from 5 to 1 are representative of a decreasing level of quality.

factors_separation = {5: 0, 
                      4: 0.02,
                      3: 0.04,
                      2: 0.06,
                      1: 0.1,
                      0: 1}

factors_surface =    {5: 0,
                      4: 0.02,
                      3: 0.04,
                      2: 0.06,
                      1: 0.1,
                      0: 1}

factors_traffic =    {5: 0,
                      4: 0.02,
                      3: 0.04,
                      2: 0.06,
                      1: 0.1,
                      0: 1}

factors_accidents =  {5: 0,
                      4: 0.02,
                      3: 0.04,
                      2: 0.06,
                      1: 0.1,
                      0: 1}

TRANSLATION_FACTORS = {"separation": factors_separation,
                       "surface": factors_surface,
                       "traffic": factors_traffic,
                       "accidents": factors_accidents}

# The road types that aren't evaluated
IGNORED_TYPES =["motorway", "service"]

# Maximum distance for bike travel. POIs outside this distance aren't considered for calculation.
MAX_DISTANCE = 3000 


WEIGHT_FACTORS_CATEGORIES = {
    "education": ["university", "school"],
    "doctors": ["doctors", "dentist", "clinic"],
    "entertainment": ["cinema", "music_venue", "stage", "nightclub", "theatre"],
    "pharmacy": ["pharmacy"],
    "financial": ["bank", "atm"],
    "sustenance": ["cafe", "bar", "restaurant"],
    "supermarket": ["supermarket"],
    "food_shop": ["bakery", "butcher", "cheese", "greengrocer", "deli"],
    "office": ["office"]}

MODEL_WEIGHT_FACTORS = {
    "education": [6, 0, 0],
    "doctors": [5, 1, 0],
    "entertainment": [2, 0, 0],
    "pharmacy": [2, 0, 0],
    "financial": [2, 0, 0],
    "sustenance": [4, 2, 0],
    "supermarket": [8, 4, 1],
    "food_shop": [5, 1, 0],
    "office": [8, 4, 1]}

POIS_MODEL = {
    "amenity": 
        WEIGHT_FACTORS_CATEGORIES["education"] +
        WEIGHT_FACTORS_CATEGORIES["doctors"] +
        WEIGHT_FACTORS_CATEGORIES["entertainment"] +
        WEIGHT_FACTORS_CATEGORIES["pharmacy"] +
        WEIGHT_FACTORS_CATEGORIES["financial"] +
        WEIGHT_FACTORS_CATEGORIES["sustenance"],
    "shop":
        WEIGHT_FACTORS_CATEGORIES["supermarket"] +
        WEIGHT_FACTORS_CATEGORIES["food_shop"],
    "office": True}

RESIDENTIAL_BUILDING_TYPES = [
    "yes",
    "apartments",
    "tower",
    "dormitory",
    "residential",
    "detached",
    "house",
    "semidetached house",
    "hotel",
    "farm",
    "monastery",
    "bungalow",
    "cabin",
    "static_caravan",
    "barrack",
    "ger",
    "houseboat",
    "stilt_house",
    "terrace",
    "tree_house",
    "trullo"]

IGNORE_BUILDING_TYPES = [
    "bunker",
    "garage",
    "hut",
    "university",
    "construction",
    "commercial",
    "government",
    "retail",
    "parking",
    "church",
    "grandstand",
    "farm_auxiliary",
    "sports_centre",
    "sports_hall",
    "school",
    "office",
    "industrial",
    "cathedral",
    "hospital",
    "kindergarden",
    "roof",
    "kiosk",
    "garages",
    "fire_station",
    "service",
    "warehouse",
    "chapel",
    "public",
    "bridge",
    "shed",
    "carport",
    "civic",
    "manufacture",
    "mosque",
    "synagogue",
    "train_station",
    "college",
    "greenhouse",
    "farmyard",
    "cowshed",
    "digester",
    "stable",
    "ruins",
    "transportation",
    "community_centre",
    "barn",
    "silo",
    "allotment_house",
    "shop",
    "elevator",
    "church_tower",
    "container",
    "gatehouse",
    "tent",
    "storage_tank",
    "shelter",
    "wall",
    "conservatory",
    "stadium"]


CONFIG = {
    "use_accidents": USE_ACCIDENTS,
    "visualize": VISUALIZE,
    "accident_path": ACCIDENT_PATH,
    "export_path": EXPORT_PATH,
    "city": CITY,
    "default_scores": DEFAULT_SCORES,
    "factor_weights": FACTOR_WEIGHTS,
    "translation_factors": TRANSLATION_FACTORS,
    "ignored_types": IGNORED_TYPES,
    "max_distance": MAX_DISTANCE,
    "pois_model": POIS_MODEL,
    "weight_factors_categories": WEIGHT_FACTORS_CATEGORIES,
    "model_weight_factors": MODEL_WEIGHT_FACTORS,
    "residential_building_types": RESIDENTIAL_BUILDING_TYPES,
    "ignore_building_types": IGNORE_BUILDING_TYPES
    }