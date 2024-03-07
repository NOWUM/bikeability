import pandas as pd
import geopandas as gpd
import logging
import os
from sqlalchemy import create_engine, text
from contextlib import contextmanager, closing
from credentials import mobilityUsername, mobilityPassword

log = logging.getLogger('Unfaelle')

LAND_ID = 5
REGBEZ_ID = 3
KREIS_ID = 34
GEMEINDE_ID = 2 # Gemeinde-ID für Aachen

DIRECTORY_CSV = "Unfallatlas CSV"

START_YEAR = 2016
END_YEAR = 2022

ID_LIST = []

class BasicDbCrawler:
    """
    class to allow easier crawling of open data
    abstracts the data base accessor creation

    Parameters
    ----------
    database: str
        database connection string or path to sqlite db
    """

    def __init__(self, database):
        # try sqlalchemy connection first
        # fall back to using sqlite3
        try:
            self.engine = create_engine(database)
            @contextmanager
            def access_db():
                """contextmanager to handle opening of db, similar to closing for sqlite3"""
                with self.engine.connect() as conn, conn.begin():
                    yield conn

            self.db_accessor = access_db
        except Exception:
            log.error("Unable to connect to database!")

class unfallatlas_crawler(BasicDbCrawler):
    
    def create_table(self) -> None:
        """
        Creates the timescaledb table necessary to write data from unfallatlas into.

        """
        try:
            with self.db_accessor() as conn:
                conn.execute(text("CREATE TABLE IF NOT EXISTS unfaelle( "
                              "objectid int, "
                              "jahr int, "
                              "rad int, "
                              "fuss int, "
                              "x_wgs84 double precision, "
                              "y_wgs84 double precision, "
                              "PRIMARY KEY (objectid, jahr));"))
            log.info('Created table unfaelle')
        except Exception as e:
            log.error(f'Could not create table unfaelle: {e}')
    
    def read_unfaelle_csv(self) -> pd.DataFrame:
        """
        Reads csv data from the path specified above. The csv files need to 
        accord to the standard unfallatlas format.

        Returns
        -------
        Unfaelle_df : DataFrame
            Dataframe including all relevant incidents concerning the town 
            specified through IDs. (Aachen)

        """
        unfaelle_df = pd.DataFrame()
        
        filenames = os.listdir(DIRECTORY_CSV)
        
        for filename in filenames:
            # url = f"https://www.opengeodata.nrw.de/produkte/transport_verkehr/unfallatlas/Unfallorte{year}_EPSG25832_CSV.zip"
            directory =f"{DIRECTORY_CSV}/{filename}"
            
            data = pd.read_csv(directory, 
                               delimiter = ";", 
                               decimal = ",",
                               usecols = ["OBJECTID", "ULAND", "UREGBEZ", "UKREIS", "UGEMEINDE", "UJAHR", "IstRad", "IstFuss", "XGCSWGS84", "YGCSWGS84"],
                               index_col = "OBJECTID")
            
            unfaelle_df = pd.concat([unfaelle_df, data])
            
        unfaelle_df = unfaelle_df[unfaelle_df.ULAND == LAND_ID]
        unfaelle_df = unfaelle_df[unfaelle_df.UREGBEZ == REGBEZ_ID]
        unfaelle_df = unfaelle_df[unfaelle_df.UKREIS == KREIS_ID]
        unfaelle_df = unfaelle_df[unfaelle_df.UGEMEINDE == GEMEINDE_ID]
        unfaelle_df = unfaelle_df[["UJAHR", "IstRad", "IstFuss", "XGCSWGS84", "YGCSWGS84"]]
        
        unfaelle_df = unfaelle_df.rename(columns={"UJAHR": "jahr", 
                                    "IstRad": "rad", 
                                    "IstFuss": "fuss",
                                    "XGCSWGS84": "x_wgs84",
                                    "YGCSWGS84": "y_wgs84"})
        
        unfaelle_df.index.names = ['objectid']
        return unfaelle_df
    
    def feed_database(self, unfaelle_df) -> None:
        try:
            with self.db_accessor() as conn:
                unfaelle_df.to_sql('unfaelle',  con=conn, if_exists = 'append', index = True, chunksize = 10000)     
        except Exception as e:
            log.info(f'Probably no database connection: {e}')  
    
def main(db_uri: str):
    uc = unfallatlas_crawler(db_uri)
    
    uc.create_table()
    
    unfaelle_df = uc.read_unfaelle_csv()
    
    uc.feed_database(unfaelle_df)
        
    
if __name__ == '__main__':
    logging.basicConfig(
        filename = "unfallatlas.log",
        level=logging.INFO,
        format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
        datefmt='%d-%m-%Y %H:%M:%S',
    )
    db_uri = f'postgresql://{mobilityUsername}:{mobilityPassword}@timescale.nowum.fh-aachen.de:5432/mobilitaet-aachen'
    main(db_uri)