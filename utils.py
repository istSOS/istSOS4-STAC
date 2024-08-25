
import json
import sys
import os
from datetime import datetime
from typing import Union
import time
from shapely import geometry

import requests
import urllib3
#for supressing warning of SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
"""
    Utility functions, like to check the given STA link is valid or not and handling JSON file
    finding

"""
def validate_sta_link(
    link: str,
    version: str,

) -> bool:
    """
    Validate the STA link.
    Args:
        link (str) : STA project link or URL
        version (str) : STA version 
    Returns:
        bool : True if validation success else False

    """
    try:

        print(link + "/" + version)
        response = requests.get(
            link + "/" + version, verify=False
        )

        if response.status_code == 200:
            return True
        else:
            print(f"Invalid response from given url with HTTP response as {response} and code as {response.status_code}")
            return False
    except Exception as e:
        print(f"Url not accessible or wrong url {e}")
        return False

def get_number_of_entities(
    link : str,
    entity : str) -> int:
    
    """
    Get the number of entities in the SensorThings API.

    Args:
        link (str): link or URL of  SensorThings API.
        entity (str): The type of entity to count can be datastreams,things
            

    Returns:
        int: The number of entities found in the SensorThings API.
            - Returns the count of the specified entity type. If an error occurs, returns 0.

    """
  
    url = f"{link}/{entity}?$count=true"
    try:
        
        response = requests.get(
            url,verify=False
        )

        if response.status_code == 200:
            res =response.json()["@iot.count"]
            return response.json()["@iot.count"]
        else:
            if response.json()["@iot.count"] != 0:
                
                return response.json()["@iot.count"]
            else:
                print("Error getting count from the entity")

                return 0
    except Exception as e:
        
            print(f"Could not get the number of entity in {link}.")
        
            return 0

def get_list_of_entities_id(
    link:str,
    entity:str
) -> list:
    """
    Get list of Things in the SensorThings API all available in the entity.
    Args:
        link (str): link or URL of SensorThings API.
        entity (str): type of entity to get IDs for

    Returns:
        list: list of entity IDs
            

    """
    final_list = []
    for i in range(
        0,
        get_number_of_entities(
            link=link,
            entity=entity
        ),
        100,
    ):
        url = f"{link}/{entity}?$count=true&$top=100&$skip={i}&$select=%40iot.id&$orderby=%40iot.id+asc"
        try:
        
            response = requests.get(
                url,verify=False
            )
            if response.status_code == 200:
                iot_ids = [
                    item["@iot.id"] for item in response.json()["value"]
                ]
                final_list.extend(iot_ids)
            else:
                print("Unable to access url")
                

        except Exception as e:
            print(f"Exception {e}")

    return final_list

def open_sta_entity_links(
    link:str
) -> dict:
    """
    To open the SensorThings API entity.
    Args:
        link (str): link or URL of the SensorThings API 
        
    Returns:
        dict: The JSON response of the entity data.
    """

    try:
        response = requests.get(
            link,verify=False
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Could not open {link}. {response.status_code} : {response.reason}")
            
            return {}
    except Exception as e:
        print(f"Could not open {link}.")
        print(f"Exception occured {e}")
        
        return {}

def name_sanitize(string: str) -> str:
    """
    Creating the STAC ID using hyphens.
    Args:
        string (str): name string to be sanitized.
            
    Returns:
        str: sanitized name string.
       
    """
    return (
        string.replace(" ", "-")
        .replace("/", "-")
        .replace("\\", "-")
        .replace(":", "-")
        .replace("*", "-")
        .replace("?", "-")
        .replace('"', "-")
        .replace("<", "-")
        .replace(">", "-")
        .replace("|", "-")
    )

def open_json_file(file_path: str) -> dict:
    """
    Opening the JSON file given the file path
    Args:
        file_path (str): The path to the JSON file.


    Returns:
        dict: The contents of the JSON file.
    """
    try:
        loaded_json = json.load(open(file_path))
        return loaded_json

    except Exception as e:
        print(f"Exception occured {e}")
    
        print(f"Could not open {file_path}.")
        
        return {}
    

# def datetimef( date_time: str):
    """
    convert date-time to the ISO format.
    """

    try:

        datetime_begin = date_time.split("/")[0]
        datetime_end = date_time.split("/")[1]
        try:
            datetime_begin_formatted = datetime.strptime(
            datetime_begin, "%Y-%m-%dT%H:%M:%SZ"
        )

            datetime_end_formatted = datetime.strptime(
                datetime_end, "%Y-%m-%dT%H:%M:%SZ"
            )

        except Exception as exc:
            datetime_begin_formatted = datetime.strptime(
            datetime_begin, '%Y-%m-%dT%H:%M:%S.%fZ'
        )

            datetime_end_formatted = datetime.strptime(
                datetime_end, '%Y-%m-%dT%H:%M:%S.%fZ'
            ) 

        return [datetime_begin_formatted, datetime_end_formatted]
    except Exception as e:

        print(f"Could not convert the date-time to the ISO format due to exception {e}")
        
        return None

# def geometryf( bbox: list, geometry_type: str):
    """
    Convert the bbox to the GeoJSON format.
    """
    # print("Waitingforgeom")

    if geometry_type is not None and bbox is not None:
        if isinstance(geometry_type, str):
            if geometry_type == "Point":
                try:
                    return geometry.Point(bbox[0][0], bbox[0][1])
                except Exception as e:
                    print(f"Could not convert the bbox to the GeoJSON format. {e}")
                    
                    return None
            elif geometry_type == "Polygon":
                try:
                    return geometry.Polygon(bbox)
                except Exception as e:
                    print(f"Could not convert the bbox to the GeoJSON format. {e}")
                    
                    return None
            elif geometry_type == "LineString":
                try:
                    return geometry.LineString(bbox)
                except Exception as e:
                    print(f"Could not convert the bbox to the GeoJSON format. {e}")
                    
                    return None
            elif geometry_type == "MultiPoint":
                bbox = [[point[0], point[1]] for point in bbox]
                try:
                    return geometry.MultiPoint(bbox)
                except Exception as e:
                    print(f"Could not convert the bbox to the GeoJSON format. {e}")
                    
                    return None
            elif geometry_type == "MultiPolygon":
                try:
                    return geometry.MultiPolygon(bbox)
                except Exception as e:
                    print(f"Could not convert the bbox to the GeoJSON format. {e}")
                    
                    return None
            elif geometry_type == "MultiLineString":
                try:
                    return geometry.MultiLineString(bbox)
                except Exception as e:
                    print(f"Could not convert the bbox to the GeoJSON format. {e}")
                    
                    return None
            else:
                print("Could not convert the bbox to the GeoJSON format. The geometry type is not valid.")
                
                return None
        elif isinstance(geometry_type, list):
            if all(geometry == "Point" for geometry in geometry_type):
                bbox = [[point[0], point[1]] for point in bbox]
                try:
                    return geometry.MultiPoint(bbox)
                except Exception as e:
                    print(f"Could not convert the bbox to the GeoJSON format. {e}")
                    
                    return None
            elif all(geometry == "Polygon" for geometry in geometry_type):
                try:
                    return geometry.MultiPolygon(bbox)
                except Exception as e:
                    print(f"Could not convert the bbox to the GeoJSON format. {e}")
                    
                    return None
            if all(geometry == "LineString" for geometry in geometry_type):
                try:
                    return geometry.MultiLineString(bbox)
                except Exception as e:
                    print(f"Could not convert the bbox to the GeoJSON format. {e}")
                    
                    return None
            else:
                print("Could not convert the bbox to the GeoJSON format. The geometry type is not valid.")
                
                return None
            try:
                return geometry.MultiPolygon(bbox(bbox))
            except Exception as e:
                print(f"Could not convert the bbox to the GeoJSON format. {e}")
                
                return None
        else:
            print("This is not a format to convert the bbox to the GeoJSON format.")
            
            return None
    elif geometry_type is None and bbox is not None:
        try:
            point = geometry.Point(bbox)
            return point
        except Exception:
            try:
                polygon = geometry.Polygon(bbox)
                return polygon
            except Exception:
                try:
                    linestring = geometry.LineString(bbox)
                    return linestring
                except Exception as e:
                    print(f"Could not convert the bbox to the GeoJSON format. {e}")
                    
                    return None

# def bbox( bbox: list, geometry: Union[str, list]):
    """
    Convert the bbox to the GeoJSON format.
    """

    if geometry is not None and bbox is not None:
        if isinstance(geometry, str):
            if geometry == "Point":
                bbox = [[bbox[0][0], bbox[0][1]]]
                return bbox
            else:
                return bbox
        elif isinstance(geometry, list):
            if all(geometry == "Point" for geometry in geometry):
                bbox = [[point[0], point[1]] for point in bbox]
            else:
                return bbox
    elif geometry is None and bbox is not None:
        return bbox
    else:
        print("Could not convert the bbox to the GeoJSON format. The geometry type is not valid.")
        
        return None

# def collectiondt( date_times_list: list):
    """
    Process the items attributes to create the collection temporal extent.
    """

    date_times_list = sorted(date_times_list)
    return [date_times_list[0], date_times_list[-1]]

# def item( harvesting_vars: dict):
    """
    Process the items attributes to create the item temporal extent.
    """
    all_item_datetime = []
    if harvesting_vars.get("item_datetime") is not None:
        for item_datetime in harvesting_vars["item_datetime"]:
            if item_datetime is not None:
                list_start_end_datetime = datetimef(item_datetime)
                if list_start_end_datetime is not None:
                    all_item_datetime.extend(list_start_end_datetime)

        all_item_datetime = sorted(all_item_datetime)
        harvesting_vars["item_datetime"] = [
            all_item_datetime[0],
            all_item_datetime[-1],
        ]
    if (
        harvesting_vars.get("item_bbox") is not None
        and harvesting_vars.get("item_geometry") is not None
    ):
        harvesting_vars["item_bbox"] = bbox(
            harvesting_vars["item_bbox"], harvesting_vars["item_geometry"]
        )

    
    return harvesting_vars

# def check_existance(path_to_check):
    
    print("checking path")
    
    print(path_to_check)
    if os.path.exists(path_to_check):
        return True
    else:
        return False


