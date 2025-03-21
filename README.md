
# Bikeability
Repository for Bikeability calculations according to the 2024 Paper "Bikeability Scoring auf Basis von Open Data – Ein Open-Source Modell" that will be published in the conference magazine for Wissenschaftsforum Mobilität.

# Installation

Clone this repository:

```bash
git clone https://github.com/NOWUM/bikeability.git
cd bikeability
```

Install requirements:

```bash
conda env create -f environment.yml
```

# Model
The program calculates 2 layers of scores.
- Bicycle suitability of road segments calculated from surface quality and separation of bicycle infrastructure
- Bikeability of residential buildings calculated from scores for POI types. These are navigated to over the suitability map and scored separately. The resulting scores are weighted against each other to calculate bikeability.

```mermaid

flowchart TD
    classDef OSM fill:#ffffcc,stroke:#333,stroke-width:2px
    classDef Fahrradtauglichkeit fill:#cce6ff,stroke:#333,stroke-width:2px
    classDef Bikeability fill:#b3ffb3,stroke:#333,stroke-width:2px
    classDef Utility fill:#F8F8FF,stroke:#333,stroke-width:2px
    GP([building-specific POI-scores]):::Bikeability
    GB([building-specific Bikeability]):::Bikeability
    ST([road-segment-specific bicycle suitability]):::Fahrradtauglichkeit
    RT{ROUTING}:::Utility
    PO[POI-spread]:::OSM
    RB[building-spread]:::OSM
    SU[surface quality]:::OSM
    SP[separation]:::OSM
    UF[accidents]:::OSM
    PW[POI-weights]:::Utility
    ST --> RT
    PO --> RT
    RB --> RT
    RT --> GP
    SU --> ST
    SP --> ST
    UF --> ST
    GP --> PW
    PW --> GB
```
# Results
Examplary results of the model can be found under https://acdatep.nowum.fh-aachen.de/bikeability/

# Usage
The following section explains how a bikeability assessment can be carried out using the model developed and the program code provided.

## Input data
Before performing the bikeability calculation, the input data must be checked.
These can be found in the attached file "bikeability_config.py".

The most important input value is the selected city. This can be entered under CITY in the format "[city]/[country]". If a protobuff file for the city in question already exists locally on the device, this can be specified as "PBF_PATH", otherwise it will be downloaded during the program run.

At this point, the "USE_ACCIDENTS" parameter must also be used to specify whether accident data should be used. This is only possible for non-German cities if an h5 file containing accident data for the selected city is stored under "ACCIDENT\_PATH".

## Profiles
If a user profile that differs from the default with an individual evaluation of the importance of POIs is to be used for the bikeability calculation, this can also be specified in the config file. The format is to be understood as follows:
POIs are divided into 9 categories. These each symbolize a series of OSM tags that are assigned to the respective category in the program run.
Each category can be assigned weighting factors that represent the priority with which the next, second next, etc. instance of a POI in the respective category is assigned. Instance of a POI of the respective category is included in the bikeability score of residential buildings. The number of these weighting factors can be arbitrarily large, but has a direct effect on the runtime of the program. The numerical values of the weights can be as large as desired, as they are only considered in relation to other weight factors in the same table. This means that the accessibility of a POI with a weight factor of 8 has eight times as much influence on the score of buildings as a POI with a weight factor of 1.