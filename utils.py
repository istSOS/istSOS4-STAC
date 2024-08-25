
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
    
