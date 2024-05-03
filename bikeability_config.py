USE_ACCIDENTS = True
VISUALIZE = True
ACCIDENT_PATH = "accident_data/accidents_bike.h5"
EXPORT_PATH = "results"
CITY = "Aachen, Germany" # Alternative: NUTS Areas



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

factors_separation = {5: 0, # zu enum
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

MAX_DISTANCE = 2000 #multivariate Optimierung anlesen

POIS_MODEL = {
     "amenity": [
         "doctors",
         "cinema",
         "pharmacy",
         "bank",
         "cafe"],
     "shop": [
         "supermarket",
         "bakery"]}

MODEL_WEIGHT_FACTORS = {
    "doctors": [5, 1, 0],
    "cinema": [2, 0, 0],
    "pharmacy": [3, 0, 0],
    "bank": [2, 0, 0],
    "cafe": [4, 2, 0],
    "supermarket": [10, 4, 3],
    "bakery": [5, 1, 0]}

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
    "model_weight_factors": MODEL_WEIGHT_FACTORS,
    "residential_building_types": RESIDENTIAL_BUILDING_TYPES,
    "ignore_building_types": IGNORE_BUILDING_TYPES
    }