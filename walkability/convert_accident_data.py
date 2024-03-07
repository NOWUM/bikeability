import pandas as pd
import logging
import os

log = logging.getLogger('Unfaelle')

# IDs relating to Aachen
LAND_ID = 5
REGBEZ_ID = 3
KREIS_ID = 34
GEMEINDE_ID = 2

# Folder containing the CSV exports
DIRECTORY_CSV = "Unfallatlas CSV"

START_YEAR = 2016
END_YEAR = 2022

ID_LIST = []

def read_unfaelle_csv() -> pd.DataFrame:
    """
    Reads csv data from the path specified above. The csv files need to 
    accord to the standard unfallatlas format.

    Returns
    -------
    Unfaelle_df : DataFrame
        Dataframe including all relevant incidents concerning the town 
        specified through IDs. (Aachen)

    """
    accidents_df = pd.DataFrame()
    
    filenames = os.listdir(DIRECTORY_CSV)
    
    for filename in filenames:
        directory =f"{DIRECTORY_CSV}/{filename}"
        
        data = pd.read_csv(directory, 
                           delimiter = ";", 
                           decimal = ",",
                           usecols = ["OBJECTID", "ULAND", 
                                      "UREGBEZ", "UKREIS",
                                      "UGEMEINDE", "UJAHR", 
                                      "IstRad", "IstFuss", 
                                      "LINREFX", "LINREFY", 
                                      "XGCSWGS84", "YGCSWGS84"],
                           index_col = "OBJECTID")
        
        accidents_df = pd.concat([accidents_df, data])
        
    accidents_df = accidents_df[accidents_df.ULAND == LAND_ID]
    accidents_df = accidents_df[accidents_df.UREGBEZ == REGBEZ_ID]
    accidents_df = accidents_df[accidents_df.UKREIS == KREIS_ID]
    accidents_df = accidents_df[accidents_df.UGEMEINDE == GEMEINDE_ID]
    accidents_df = accidents_df[["UJAHR", "IstRad", "IstFuss", 
                                 "LINREFX", "LINREFY", 
                                 "XGCSWGS84", "YGCSWGS84"]]
    
    accidents_df = accidents_df.rename(columns={"UJAHR": "jahr", 
                                "IstRad": "rad", 
                                "IstFuss": "fuss",
                                "XGCSWGS84": "x_wgs84",
                                "YGCSWGS84": "y_wgs84",
                                "LINREFX": "x_linref",
                                "LINREFY": "y_linref"})
    
    accidents_df.index.names = ['objectid']
    return accidents_df

def accidents_to_hdf(accidents_df: pd.DataFrame):
    """
    Writes the accident data as h5-files.

    Parameters
    ----------
    accidents_df : pd.DataFrame
        List of accidents as read from the given csv-files.

    Returns
    -------
    None.

    """
    accidents_foot = accidents_df[accidents_df["fuss"] == 1]
    accidents_foot.to_hdf("accident_data/accidents_foot.h5", complevel=9, key = "fixed")
    accidents_bike = accidents_df[accidents_df["rad"] == 1]
    accidents_bike.to_hdf("accident_data/accidents_bike.h5", complevel=9, key = "fixed")
    
def main(db_uri: str):
    accidents_df = read_unfaelle_csv()
    
    accidents_to_hdf(accidents_df)
        
    
if __name__ == '__main__':
    logging.basicConfig(
        filename = "unfallatlas.log",
        level=logging.INFO,
        format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
        datefmt='%d-%m-%Y %H:%M:%S',
    )
    main()