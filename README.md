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
