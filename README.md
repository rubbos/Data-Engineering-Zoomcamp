# Notes

## 1. Docker

In WSL make sure the Docker Desktop app is running, or docker wont work.

`docker run hello-world` to test.
`docker run -it ubuntu bash` to test more. `exit` to exit
`docker run -it python:3.12` to test python. `cntr + d` to exit
add `entrypoint=bash` to start in bash

### Dockerfile

A Dockerfile is a text document that contains all the commands a user could
call on the command line to assemble an image.

Example to add pandas and run the file from local machine:

```python
#Dockerfile
FROM python:3.12
RUN pip install pandas
WORKDIR /app
COPY pipeline.py pipeline.py
ENTRYPOINT [ "bash" ]
#ENTRYPOINT [ "python3", "pipeline.py" ]
```

WORKDIR = inside the container where you want the file.
COPY = copy a file from the local machine
and give it the same name as local machine in the container.
ENTRYPOINT = Where the container is gonna start.

When editing the Dockerfile, first build, then run.
`docker build -t namedocker:pandas .`
`docker run -it namedocker:pandas`

## 2. Postgres in docker

Make a folder with the name of the data folder: ny_taxi_postgres_data

```bash
docker run -it \
  -e POSTGRES_USER="root" \
  -e POSTGRES_PASSWORD="root" \
  -e POSTGRES_DB="ny_taxi" \
  -v /$(pwd)/ny_taxi_postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  --network=pg-network \
  --name pg-database \
  postgres:13
```

Use sudo ls ny_taxi_postgres_data in a new terminal to see the files made in the new folder when its running.

Install pgcli and jupyter notebook locally if needed.

Then run `pgcli -h localhost -p 5432 -u root -d ny_taxi` to run the server.
And run `jupyter notebook`

Now we can download the data file to the folder with `wget data-link.csv`. Dont forget to unzip the file if its needed.

To check this data quickly, use `less data-file.csv` or `HEAD -n 100` for first 100 rows

To check the amount of lines in a file: `wc -l data-file.csv`

### pandas

```python
# get the data into pandas
df = pd.read_csv("data-file.csv", nrows=100)

#change a string to a datetime and return it to the data.
df.tpep_pickup_datetime = pd.to_datetime(df.tpep_pickup_datetime)
df.tpep_dropoff_datetime = pd.to_datetime(df.tpep_dropoff_datetime)

# gets the schema of the data with a custom name. This is DDL, describes how the table should look like in SQL.
print(pd.io.sql.get_schema(df, name='yellow_taxi_data'))
```

Now we also need SQLalchemy

````python
from sqlalchemy import create_engine

engine = create_engine('postgresql://root:root@localhost:5432/ny_taxi')

engine.connect()
# returns <sqlalchemy.engine.base.Connection at 0x7fe844739630> which is good

#returns table in postgres language.
print(pd.io.sql.get_schema(df, name='yellow_taxi_data', con=engine))```
````

To only add the column names to the database first:

```python
#head shows only the first x rows.
df.head(n=0).to_sql(name='yellow_taxi_data', con=engine, if_exists='replace')
```

Because data files can be big(+1M lines) we have to chuck them into smaller pieces.
We can do this with iterator.

```python
# to measure how long it takes.
from time import time

#read the .csv per 100k lines and make it an iterator.
df_iter = pd.read_csv('yellow_tripdata_2021-01.csv', iterator=True, chunksize=100000)

#keep trying to read the df_iter till it wont return anything.
while True:
    t_start  = time()

    #iterate through the chucks
    df = next(df_iter)

    #parse the data clean aka from a string to datetime
    df.tpep_pickup_datetime = pd.to_datetime(df.tpep_pickup_datetime)
    df.tpep_dropoff_datetime = pd.to_datetime(df.tpep_dropoff_datetime)

    #append the data to the table
    df.to_sql(name='yellow_taxi_data', con=engine, if_exists='append')

    t_end = time()

    #took around 8 sec for each 100k chuck.
    print('inserted another chuck, took %.3f scond' % (t_end - t_start))
```

while you are in pgcli terminal, you can checkout the saved data.
`\dt` = to show the available data tables
`\d yellow_taxi_data` = shows the information schema of the table.
`select COUNT from yellow_taxi_data` return count of lines in table.

## pgAdmin

Instead of using pgcli pgAdmin is more convinient. We can pull this from a docker image.

```python
docker run -it \
  -e PGADMIN_DEFAULT_EMAIL="admin@admin.com" \
  -e PGADMIN_DEFAULT_PASSWORD="root" \
  -p 8080:80 \
  --network=pg-network \
  --name pgadmin-2 \
  dpage/pgadmin4
```

Login with the info up above. Right click Servers -> Register -> Server.
Give it a name, and add as connection hostname: localhost.
Add username and pass from the postgres server.
Now we gotta link both docker containers with a docker network create.

`docker network create pg-network`

now run the other containers with 2 extra paramiters:

```python
  --network=pg-network \
  --name pgadmin-2 \
```

Postgres should still have the data if its mounted on that folder. Both containers are now connected.

In pgAdmin we use as hostname the new network name for postgres.
`pg-database` in this case. Under tools -> query tool to do any SQL command.

To convert the jupyter to a script:
`jupyter nbconvert --to=script upload-data.ipyn`

argparse = library to parse command line commands

The complete script to read the csv and get it into postgres:

```python
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
```

The command for this script:

```bash
URL="https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2021-01.csv.gz"

python ingest_data.py \
  --user=root \
  --password=root \
  --host=localhost \
  --port=5432 \
  --db=ny_taxi \
  --table_name=yellow_taxi_trips \
  --url=${URL}
```

To make this automatic in a Dockerfile make sure you add those libraries and remove the python3 command from the script command:

```Dockerfile
FROM python:3.12

RUN apt-get install wget
RUN pip install pandas sqlalchemy psycopg2

WORKDIR /app
COPY ingest_data.py ingest_data.py
ENTRYPOINT [ "python3", "ingest_data.py" ]
```

Build the docker image:
`docker build -t taxi_ingest:v001 .`

Then we gotta edit the command for the docker file so the container knows its gotta use the network and the taxi_ingest container.

```bash
URL="https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_2021-01.csv.gz"

docker run -it \
  --network=pg-network \
  taxi_ingest:v001 \
    --user=root \
    --password=root \
    --host=pg-database \
    --port=5432 \
    --db=ny_taxi \
    --table_name=yellow_taxi_trips \
    --url=${URL}
```

This made a python container that gets the CSV file, parses it, and adds it to postgres container.

## Docker compose

```docker-compose
services:
  pgdatabase:
    image: postgres:13
    environment:
      - POSTGRES_USER=root
      - POSTGRES_PASSWORD=root
      - POSTGRES_DB=ny_taxi
    volumes:
      - "./ny_taxi_postgres_data:/var/lib/postgresql/data:rw"
    ports:
      - "5432:5432"
  pgadmin:
    image: dpage/pgadmin4
    environment:
      - PGADMIN_DEFAULT_EMAIL=admin@admin.com
      - PGADMIN_DEFAULT_PASSWORD=root
    volumes:
      - "pgadmin_conn_data:/var/lib/pgadmin:rw"
    ports:
      - "8080:80"

volumes:
  pgadmin_conn_data:
```

`docker-compose up -d`: to start the docker compose file detached.
`docker-compose down` to remove the container.
