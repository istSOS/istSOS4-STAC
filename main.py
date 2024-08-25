"""The purpose of this class is to fetch data from Sensor Things API (STA) and generate STAC metadata.
For our case we consider each STA project as one Collection, and the things are considered as Items.
The Datastreams are considered as Assets of the Item.  """
import os
import glob
from tqdm import tqdm
import sys
import shutil
import pystac
import urllib3
from rescreator import *
from fetchdata import *
from utils import *
from helper import *



class stac_from_sta:
    """The purpose of this class is to fetch data from Sensor Things API (STA) and generate STAC metadata.
    For our case we consider each STA project as one Collection, and the things are considered as Items.
    The Datastreams are considered as Assets of the Item.  """


   
    

    def __init__(self,sta_link:str,stac_dir:str,id:str,title:str,description:str,catalog_name:str,asset_as: str,specific_thing_start:int,specific_thing_end:int,stac_catalog_exists:bool,stac_collection_exists:bool):
        
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
        
        Returns:
            None, generates the STAC metadata for each of the thing, also generate the collection and catalog JSONs
    

        
        """
            

        #STA- version 
        version = "v1.1"
        
        print("Initialzing")
        
        fetched_vars = {}

        print("Starting Fetching of data....")
        validator_value = validate_sta_link(link=sta_link,version=version)
        
        if validator_value is False:
            return 
        elif validator_value:
            
            fetched_vars["catalog"] = STACCatalog(sta_link=sta_link,stac_id=id,stac_title=title,stac_description=description,stac_dir=stac_dir,default_catalog_name=catalog_name,stac_catalog_exist=stac_catalog_exist)
            
            fetched_vars["already_existing_items_list"],fetched_vars["collection"] = STACCollection(stac_id=id,
                stac_title=title,
                stac_description=description,
                fetched_vars=fetched_vars,
                stac_collection_exists=stac_collection_exists,
                stac_dir=stac_dir)

        

        if specific_thing_end is not None and isinstance(specific_thing_end,int):
            print("Running for specific start and end")
            list_of_things=[]
            for j in range(specific_thing_start,specific_thing_end,1):
                list_of_things.append(j)
            print("list end ")
            print(list_of_things)

        else:
            list_of_things = get_list_of_entities_id(link=sta_link+"/"+version,entity="Things")
            things_number = get_number_of_entities(link=sta_link+"/"+version,entity="Things")
        

            if things_number == 0:
                SAVEcatalog(catalog=fetched_vars["catalog"],stac_dir=stac_dir)
                print("No things found")
            elif things_number > 0 and things_number == len(list_of_things):
                print(f"Things found")


            
        for thing_index, thing_id_number in enumerate(tqdm(list_of_things)):

            print(f"Thing number{thing_id_number}")
            if thing_index==2:
                break
            
            

            fetched_vars["item_datetime"] = None
            fetched_vars["item_datetime_str"] = []
            fetched_vars["item_bbox"] = []
            fetched_vars["item_footprint"] = None
            fetched_vars["item_geometry"] = ""
            fetched_vars["item_variable_names"] = []
            fetched_vars["item_variable_units"] = []
            fetched_vars["item_variable_dimensions"] = []
            fetched_vars["item_variable_descriptions"] = []
            fetched_vars["item_variable_ids"] = []
            fetched_vars["item_dimension_names"] = []
            for key in fetched_vars.keys():
                if "sta2stac_thing_variable_" in key:
                    fetched_vars[key] = None

            print("Starting Fetching...")
            try:
                fetched_vars_temp = fetchitem(sta_link=sta_link,version=version,number_of_thing=thing_id_number,old_vars=fetched_vars,asset_as=asset_as)
            except Exception as exp:
                print(f"Fetching failed due to {exp}")
            print(f"Fetching complete for thing {thing_id_number}")
           
            if fetched_vars_temp is None:
                print(f"Fetched None for thing {thing_id_number}")
            else:    
                fetched_vars.update(fetched_vars_temp)
            
            

            print("Starting Item creation...")
            STACItem(fetched_vars=fetched_vars)
        
        print("Complete data fetching complete")

        
        fetched_vars["collection_datetime"] = collectiondt(fetched_vars["collection_datetime"])
        # path_to_check = (stac_dir+"\\"+default_catalog_name)
            
        # print(f"path to check {path_to_check}")

        if stac_catalog_exists is True:
            try:
                collection_e = fetched_vars["collection"]
                fetched_vars["collection_bbox_existing"]=(collection_e.extent.spatial.bboxes)[0]
                fetched_vars["collection_datetime_existing"]=(collection_e.extent.temporal.intervals)[0]
                
                dt = fetched_vars["collection_datetime"]
                dt_exist = fetched_vars["collection_datetime_existing"]
                dt_exist_mod = [dt.replace(tzinfo=None) for dt in dt_exist]

                
                new_datetime_range = [
                    min(dt[0], dt_exist_mod[0]),  
                    max(dt[1], dt_exist_mod[1])  
                ]
                print(new_datetime_range)

                cbox = fetched_vars["collection_bbox"]
                cbox_exist = fetched_vars["collection_bbox_existing"]
                
                new_bbox = [
                    min(cbox[0], cbox_exist[0]),  
                    min(cbox[1], cbox_exist[1]),  
                    max(cbox[2], cbox_exist[2]),  
                    max(cbox[3], cbox_exist[3]),  
                ]

                spatial_extent = pystac.SpatialExtent(bboxes=[new_bbox])

                temporal_extent = pystac.TemporalExtent(intervals=[new_datetime_range])

                fetched_vars["collection"].extent = pystac.Extent(spatial=spatial_extent,
                                                                        temporal=temporal_extent
                                                                        )
            except Exception as exc:
                print("No existing collection exists error in getting extent of collection",exc)


        else:
            
            spatial_extent = pystac.SpatialExtent(bboxes=[fetched_vars["collection_bbox"]])

            temporal_extent = pystac.TemporalExtent(intervals=[fetched_vars["collection_datetime"]])
            
            
            fetched_vars["collection"].extent = pystac.Extent(spatial=spatial_extent,
                                                                        temporal=temporal_extent
                                                                        ) 

        try:

            SAVEcatalog(catalog=fetched_vars["catalog"],stac_dir=stac_dir)
        except Exception as exc:
            print(f"SAVE failed to directory {stac_dir}")
            print("tryiing")
            stac_dir = os.getcwd()
            SAVEcatalog(catalog=fetched_vars["catalog"],stac_dir=stac_dir)  
        print("STAC metadata generation finished")
        coll_path = stac_dir +"/"+id+"/collection.json"
        new_coll_path = stac_dir +"/collection.json"
        
        shutil.copy(coll_path,new_coll_path)
        
        print(coll_path)
        print("Copied collection json")

        
        try:
            pathdir="/app/"+stac_dir+"/"
            print(os.listdir(pathdir))
            if os.path.exists("/app/data/catalog.json"):
                print("catalog creation success")
                catalog = pystac.Catalog.from_file("/app/data/catalog.json")
            else:
                print("failed catalog")
            pathc = "/app/"+stac_dir+"/"+id+"/collection.json"
            if os.path.exists(pathc):
                print("collection creation success")
            else:
                print("failed collection")
        except Exception as exc:
            print("Docker path exception ignore for local",exc)
            pathdir=stac_dir
            if os.path.exists(pathdir+"/"+"catalog.json"):
                print("catalog creation success")
                catalog = pystac.Catalog.from_file(pathdir+"/"+"catalog.json")
            else:
                print("failed catalog")
            pathc = pathdir+"/"+id+"/collection.json"
            if os.path.exists(pathdir+"/"+id+"/collection.json"):
                print("collection creation success")
            else:
                print("failed collection")

            
        print(catalog)
        collections = list(catalog.get_collections())
        if len(collections) != 1:
            print("Catalog has multiple collections")


        print("Creating newline delimited JSON file of items...")
        collection = collections[0]
        with open(f"{collection.id}_items.json", "w") as f:
            for item in collection.get_all_items():
                item_dict = item.make_asset_hrefs_absolute().to_dict()
                item_str = json.dumps(item_dict)
                f.write(item_str + "\n")
        init_name = f"{collection.id}_items.json"
        final_name = stac_dir +"/items.json"
        if os.path.isfile(final_name):
            os.replace(init_name,final_name)
        else:
            os.rename(init_name,final_name)
        print("creation of newline delimited JSON success")
        print("Ready for data ingestion")


            
        




if __name__ == "__main__":
    sta_link = sys.argv[1]
    print(sta_link)
    try:
        stac_dir = sys.argv[2]
    except Exception as exc:
        print("Specific directory not specified. Using present directory")
        stac_dir = os.getcwd()
    try:
        id = sys.argv[3]
        if id == "None":
            id="STACfromSTA"
    except Exception as exc:
        print("ID not given, defaulting to STACfromSTA")
        id="STACfromSTA" 
    try:
        title = sys.argv[4]
    except Exception as exc:
        title="STACfromSTA"
        print("Title not given, defaulting to STACfromSTA")
    try:
        description = sys.argv[5]
        if description == "None":
            description="STACfromSTA-description"
    except Exception as exc:
        description="STACfromSTA-description"
        print("Description not given, defaulting to STACfromSTA description")
    try:  
        catalog_name = sys.argv[6]
        if catalog_name == "None":
            catalog_name ="catalog.json" 
    except Exception as exc:
        print("Catalog name not given, defaulting to catalog.json")
        catalog_name="catalog.json"
    try:
        asset_as = sys.argv[7]
    except Exception as exc:
        asset_as="CSV"    
    try:
        specific_thing_start = int(sys.argv[8])
    except Exception as exc:
        print("No specific start given, defaulting to 0")
        specific_thing_start=0
    try:    
        specific_thing_end = int(sys.argv[9])    
    except Exception as exc:
        print("No specific end given, defaulting to None")
        specific_thing_end = None
    try:
        stac_catalog_exist=eval(sys.argv[10])
    except Exception as exc:
        print("stac catalog existance not given default to False")
        stac_catalog_exist= False
    try:
        stac_collection_exists=eval(sys.argv[11])
    except Exception as exc:
        stac_collection_exists = False
        print("stac collection not given defaults to False")


    stac_from_sta(sta_link=sta_link,stac_dir=stac_dir,title=title,description=description,catalog_name=catalog_name,id=id,asset_as=asset_as,specific_thing_start=specific_thing_start,specific_thing_end=specific_thing_end,stac_catalog_exists=stac_catalog_exist,stac_collection_exists=stac_collection_exists)

