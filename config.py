ACCIDENT_PATH = "accident_data/accidents_bike.h5"
EXPORT_PATH = "results"
CITY = "Aachen, Germany"

DEFAULT_SCORES = {'separation': 2,
                  'surface': 2,
                  'traffic': 3}

# translation scores to factors

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

TRANSLATION_FACTORS = {"separation": factors_separation,
                       "surface": factors_surface,
                       "traffic": factors_traffic}