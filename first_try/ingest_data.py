import os
import argparse
import pandas as pd
from sqlalchemy import create_engine
from time import time


def main(params):
    user = params.user
    password = params.password
    host = params.host
    port = params.port
    db = params.db
    table_name = params.table_name
    url = params.url
    csv_name = "output.csv"

    # Creates command to get the file
    os.system(f"wget {url} -O {csv_name}")

    # Creates an engine to get it into postgres
    engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")

    # Read the csv per 100k lines and make it an iterator.
    df_iter = pd.read_csv(csv_name, iterator=True, chunksize=100000, compression="gzip")

    # Read first 100k lines
    df = next(df_iter)

    # Adds column headers to Postgres
    df.head(n=0).to_sql(name=table_name, con=engine, if_exists="replace")

    # Keep repeating adding 100k lines till its empty
    while True:
        t_start = time()

        # Transform a string to datetime
        df.tpep_pickup_datetime = pd.to_datetime(df.tpep_pickup_datetime)
        df.tpep_dropoff_datetime = pd.to_datetime(df.tpep_dropoff_datetime)

        # Keep repeating adding 100k lines till its empty
        df.to_sql(name=table_name, con=engine, if_exists="append")

        # Iterate through next chunck
        df = next(df_iter)

        t_end = time()
        print("inserted another chuck, took %.3f seconds" % (t_end - t_start))


if __name__ == "__main__":
    # To get args from the command line
    parser = argparse.ArgumentParser(description="Ingest CSV data to Postgres")

    parser.add_argument("--user", help="username for postgres")
    parser.add_argument("--password", help="password for postgres")
    parser.add_argument("--host", help="host for postgres")
    parser.add_argument("--port", help="port for postgres")
    parser.add_argument("--db", help="database name for postgres")
    parser.add_argument("--table_name", help="name of the table")
    parser.add_argument("--url", help="url of the csv file")

    args = parser.parse_args()

    main(args)
