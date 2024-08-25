# istsos-miu-stac
STAC metadata generation and search support for istsos-miu

## Steps to follow to generate the STAC metadata:
 ### Clone the repository
```
 git clone https://github.com/cOsprey/istsos-miu-stac
```
 
### Module details
```python
    #The script takes different parameters:
"""
    Args:
            sta_link (str): The link to the SensorThings project.
            stac_dir (str, optional): The directory where the STAC metadata will be saved or already exists.
                If not specified defaults to present directory, required if need to update existing catalog.
            id (str): The ID of the STAC catalog and collection. This is also used for collection id.
            title (str): The title of the STAC catalog and collection. 
            description (str, optional): The description of the STAC catalog and collection.
                Defaults to STACfromSTA desciption, needed if updating existing catalog.
            catalog_name (str, optional): The name of the STAC catalog.
                Defaults to catalog.json, needed if update existing catalog.
            asset_as (str, optional): To generate the link for the datastream observations in form of CSV or GeoJSON
                Defaults to CSV, other possible value GeoJSON.
            specific_thing_start (int, optional): The starting index of the specific things to fetch.
                Defaults to 0, if not specified.  
            specific_thing_end (int, optional): The ending index of the specific things to fetch.
                Defaults to None if not specified.
            stac_catalog_exists (bool,optional): Indicates whether the STAC catalog already exists.
                Defaults to False if not given, needed for updating existing meta data
            stac_collection_exists (bool, optional): Indicates whether the STAC collection already exists.
                Defaults to False if not given, needed for updating existing meta data
"""
```

  ### Start the docker environment     
  
  with default parameters:
  
 ```bash
# default parameters are sta_link: https://airquality-frost.k8s.ilt-dmz.iosb.fraunhofer.de,
# stac_dir : data, id: STACfromSTA, title: STACfromSTA, Description: STACfromSTA description,
# catalog_name: catalog.json, asset_as : "CSV", specific_start: 1, specific_end : 5,
# stac_catalog_exists: False, stac_collection_exists: False

docker-compose up

```
 with custom parameters:
```bash
docker-compose run stacsta https://airquality-frost.k8s.ilt-dmz.iosb.fraunhofer.de data "STACdemo" "stactitle" "description-STAC" "catalog.json" "CSV" "1" "5" False False
```

  
  After running the script will generate the metadata and store in the folder “data” or the ```stac_dir``` specified while execution

  ## Steps for ingesting the data into postgres and search and visualize:

  ### To query and visualize the data using STAC Browser and stac-fastapi, we utilize eoAPI:

```python
# Installing requirements
python -m pip install pypgstac==0.8.1 psycopg[pool]
```

```bash
cd eoAPI
docker compose up
```
(If fetting any error in above command try docker system prune and retry)
Start a new terminal window and navigate to the folder “data” or the ```stac_dir``` specified while execution
The contents of the directory will have folder named with ```id```, which we gave previously (or “STACfromSTA” if default). There must exist catalog.json, collection.json and items.json
```bash
# Check the database connection
pypgstac pgready --dsn postgresql://username:password@0.0.0.0:5439/postgis

#To ingest the data into the postgres database, run :
# Ingesting collection
pypgstac load collections collection.json --dsn postgresql://username:password@localhost:5439/postgis --method upsert
# Ingesting items
pypgstac load items items.json --dsn postgresql://username:password@localhost:5439/postgis --method upsert
```
## start exploring your dataset with:
  ### STAC Metadata service: http://localhost:8081
  ### Browser UI: http://localhost:8085









