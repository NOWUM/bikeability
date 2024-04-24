
USE_ACCIDENTS = True
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

pois_model = {
     "amenity": [
         "doctors",
         "cinema",
         "pharmacy",
         "bank",
         "cafe"],
     "shop": [
         "supermarket",
         "bakery"]}

model_weight_factors = {
    "doctors": [5, 1, 0],
    "cinema": [2, 0, 0],
    "pharmacy": [3, 0, 0],
    "bank": [3, 0, 0],
    "cafe": [4, 2, 0],
    "supermarket": [10, 4, 3],
    "bakery": [5, 1, 0]}

family_pois = {
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

senior_pois = {
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

student_pois = {
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
familiy_weight_factors = {
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

senior_weight_factors = {
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

student_weight_factors = {
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

POIS = [family_pois, senior_pois, student_pois]
PERSONA_WEIGHTS = [
    familiy_weight_factors,
    senior_weight_factors,
    student_weight_factors]
PERSONA_NAMES = ["families", "students", "seniors"]

