import sys
import pystac
from pystac import (Catalog, CatalogType)
import os
from datetime import datetime
import pystac.collection
from shapely import geometry

from helper import *


def add_assets(item, asset_list) ->None:
    """
    Add assets to a STAC item.

    Args:
        item (pystac.Item): The STAC item to which the assets will be added.
        asset_list (list): A list of dictionaries, where each dictionary contains fields to define an asset.
           
    Returns:
        None: The function modifies the `item` in place by adding assets to it.
    """

    for ds in asset_list:
        asset = pystac.Asset(**ds["asset_fields"])
        asset.set_owner(item)
        item.add_asset(str(ds["datstream_index"]), asset)


def STACCatalog(
    sta_link: str,
    stac_id: str,
    stac_title: str,
    stac_description: str,
    stac_dir: str,
    stac_catalog_exist: bool,
    default_catalog_name: str = "catalog.json",
    
) -> pystac.Catalog:
    """
    Create or load a STAC catalog.

    Args:
        sta_link (str): SensorThings API link or URL
        stac_id (str): The unique identifier for the STAC catalog
        stac_title (str): The title of the STAC catalog
        stac_description (str): A description of the STAC catalog.
        stac_dir (str): The directory path where the STAC catalog is or will be stored.
        stac_catalog_exist (bool): A flag indicating whether the STAC catalog already exists.
            - If `True`, the function attempts to load the existing catalog from the specified directory.
            - If `False`, a new catalog is created.
        default_catalog_name (str, optional): The name of the catalog JSON file.
            - Default is `"catalog.json"`.
            - This name is used when creating or locating the catalog file within the specified directory.

    Returns:
        pystac.Catalog: The created or loaded STAC catalog.

    """
    
    catalog = dict()

    if stac_description is None :
        stac_description = "Description of catalog"
    

    if stac_catalog_exist:
        print(f"stac_catalog_existance {stac_catalog_exist}")
        
        if stac_dir is None:
            print(f"stacdir {stac_dir}")
            print("Catalog already existing, directory not specified")

            return
        
        else:
            print("STAC Catalog exists and stac dir is not None")
            path_to_check = (stac_dir+"\\"+default_catalog_name)
            
            print(f"path to check {path_to_check}")
            res_check= check_existance(path_to_check)
            if res_check is False:
                print("Catalog not exists wrong info given")
                exit()


            if  res_check is True:
                print("Catalog already exists")
                id_catalog = pystac.Catalog.from_file(path_to_check).id
                print(f"Catalog id {id_catalog}")
                catalog[id_catalog] = pystac.Catalog.from_file(path_to_check)
                print(catalog)
                print("using existing catalog")
                
    else:
        path_to_check = (stac_dir+"\\"+default_catalog_name)
        print(f"path tocheck {path_to_check}")
        print("No existing catalog specified, creating a new catalog ")
        print(f"stacid {stac_id}")
        if stac_id is None:
            stac_id = "STACfromSTA"
        id_catalog = stac_id + "-catalog"
        catalog[id_catalog] = pystac.Catalog(
            id=stac_id,
            title=stac_title,
            description="["
            + stac_description
            + "](" + str(sta_link)  +")"
        )

    return catalog[id_catalog]

def STACCollection(
        stac_id, stac_title, stac_description, fetched_vars, stac_collection_exists,stac_dir) -> pystac.Collection:
    """
    Create or retrieve a STAC collection based on the provided parameters.
    Args:
    stac_id (str): The ID of the STAC collection.
    stac_title (str): The title of the STAC collection.
    stac_description (str): The description of the STAC collection.
    fetched_vars (dict): A dictionary containing fetched variables.
    stac_collection_exists (bool): Indicates whether the STAC collection already exists.
    
    Returns:
    tuple: A tuple containing the list of already existing item IDs and the created or retrieved STAC collection.

    """

    collection = pystac.Collection(
        id="STACfromSTA",
        extent=pystac.Extent(spatial=pystac.SpatialExtent(bboxes=[0.0,0.0]),
                                temporal=pystac.TemporalExtent(
                                    intervals=[[datetime.utcnow(),datetime.utcnow()]]
                                ),
                                ),
                                description="stac_description",
    )
    print("Defined basic collection")

    already_existing_items_list = []

    if stac_collection_exists is True:
        print("stac collection exists already")
        exisiting_collection_id_list = []
        exisiting_collection_id_list = [existance_collection.id 
                                        for existance_collection in 
                                        list(fetched_vars["catalog"].get_collections())
                                        ]
        
        if (collection is not None
            and stac_id in exisiting_collection_id_list
        ):
            
            collection = fetched_vars["catalog"].get_child(stac_id)
            print(collection)

            already_existing_items_list = [existed_item.id 
                                           for existed_item in list(collection.get_items())]
            
            
            collection_path = stac_dir + "\\"+ stac_id + "\\collection.json"
            print(collection)
            

            return already_existing_items_list, collection
            
    else:

        
        if stac_id is None:
            stac_id = "STACfromSTA"
        print(f"stacid {stac_id} {stac_title} {stac_description}")
        collection = pystac.Collection(
                id=stac_id,
                title=stac_title,
                extent=pystac.Extent(
                    spatial=pystac.SpatialExtent(bboxes=[0.0, 0.0]),
                    temporal=pystac.TemporalExtent(
                        intervals=[[datetime.utcnow(), datetime.utcnow()]]
                    ),
                ),
                description=stac_description,
            )

        fetched_vars["catalog"].add_child(collection)
        return already_existing_items_list, collection
    
    

def STACItem(
        fetched_vars
) -> pystac.Item:
    """
    Create a STAC item using the provided variables and add it to a STAC collection.

    Args:
        fetched_vars (dict): A dictionary containing all necessary variables for creating a STAC item.
            - `fetched_vars["item_id"]` (str): The unique identifier for the STAC item.
            - `fetched_vars["item_bbox"]` (list): The bounding box of the item in [minX, minY, maxX, maxY] format.
            - `fetched_vars["item_geometry"]` (dict): The geometry of the item, typically a GeoJSON geometry.
            - `fetched_vars["item_footprint"]` (geometry object): The footprint of the item, used for creating the item's geometry.
            - `fetched_vars["item_datetime"]` (list): A list with two `datetime` objects representing the start and end times of the item.
            - `fetched_vars["properties"]` (dict): A dictionary of additional properties for the item.
            - `fetched_vars["assets"]` (list): A list of dictionaries representing the assets to be added to the item.
            - `fetched_vars["collection"]` (pystac.Collection): The STAC collection to which the item will be added.

    Returns:
        None: The function creates a `pystac.Item`, adds assets to it, and then adds the item to the specified STAC collection.

    """


    fetched_vars["item_geometry"] = geometryf(fetched_vars["item_bbox"],fetched_vars["item_geometry"])
    

    
    if (fetched_vars["item_datetime"] is not None and 
        fetched_vars["item_bbox"] is not None 
        and fetched_vars["item_geometry"] is not None):
       
        item = pystac.Item(id=fetched_vars["item_id"],
                            geometry=geometry.mapping(fetched_vars["item_footprint"]),
                            bbox=fetched_vars["item_bbox"][0]+fetched_vars["item_bbox"][0],
                            datetime=fetched_vars["item_datetime"][1],
                            start_datetime=fetched_vars["item_datetime"][0],
                            end_datetime=fetched_vars["item_datetime"][1],
                            properties=fetched_vars["properties"],
                           
                            )

        asset_list = fetched_vars["assets"]
        add_assets(item, asset_list)

        
        fetched_vars["collection"].add_item(item)



def SAVEcatalog(catalog,stac_dir) -> None:
    """
    Save a STAC catalog to the specified directory.

    Args:
        catalog (pystac.Catalog): The STAC catalog to be saved.
            - This is an instance of `pystac.Catalog`, representing the collection of STAC items and their associated metadata.
        stac_dir (str): The directory path where the catalog will be saved.
            - This string specifies the location on the file system where the catalog should be stored.

    Returns:
        None: The function attempts to save the catalog to the specified directory and prints the outcome.

    """
    try:
        print("tryingsave")
        print(stac_dir)
        print(catalog)
       
        catalog.normalize_hrefs(stac_dir)
       
        catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

        print("Catalog saved")
    except Exception as e:
        print(f"Saving failed with exception {e}")
        
                


        
        
