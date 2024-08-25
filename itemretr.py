
from utils import *

def get_entity_tuples_info(sta_link: str, sta_version: str, entity: str) -> list:
    """
    Retrieves information about entities from a STAC API.
    Args:
        sta_link (str): The base URL of the STAC API.
        sta_version (str): The version of the STAC API.
        entity (str): The name of the entity to retrieve information about.
    Returns:
        list: A list of tuples containing the entity ID, title, and description.

    """
   
   

    fetched_vars: dict = dict()
    list_of_entity_tuples: list = []
    entity_url = f"{sta_link}/{sta_version}/{entity}?$count=true"
  
    validator_value = validate_sta_link(
        link=sta_link,
        version=sta_version

    )
    if validator_value is False:
        return
    else:
        entity_json = open_sta_entity_links(
            link=entity_url
        )
    if entity_json is not None:
        if entity_json["@iot.count"] == 0:
            print(f"Entity {entity} is empty.")
            
            return None
        elif entity_json["@iot.count"] > 0:
            sta_link_version = f"{sta_link}/{sta_version}"
            entity_count_number = get_number_of_entities(
                link=sta_link_version,
                entity=entity
                
            )
            list_of_entities_id = get_list_of_entities_id(
                link=sta_link_version,
                entity=entity
            )
            if entity_count_number == len(list_of_entities_id):
                for entity_index, entity_number in enumerate(
                    list_of_entities_id
                ):
                    entity_url_by_number = (
                        f"{sta_link_version}/{entity}({entity_number})"
                    )
                    entity_json_by_number = open_sta_entity_links(
                        entity_url_by_number
                       
                    )
                    fetched_vars["entity_id"] = name_sanitize(str(entity_json_by_number["name"]))
                    fetched_vars[
                        "entity_title"
                    ] = entity_json_by_number["name"]
                    if entity_json_by_number.get("description") is None:
                        fetched_vars[
                            "entity_description"
                        ] = "This is a STAC item."
                    else:
                        fetched_vars[
                            "entity_description"
                        ] = entity_json_by_number["description"]
                    list_of_entity_tuples.append(
                        (
                            fetched_vars["entity_id"],
                            fetched_vars["entity_title"],
                            fetched_vars["entity_description"],
                        )
                    )
            else:
                print("Error in getting info")
               
                return None
            return list_of_entity_tuples

def get_thing_info( thing_json: dict) -> tuple:
    """
    A function to get the automatically generated ID,
    title, description and properties of a specific Thing.
    Args:
        things_json (dict) : JSON response of request for a thing/item
    
    Return:
        Item-ID (str): id of item, title(str): title of item, description(str): description of item, and properties(dict):associated properties of each thing/item

    """
    fetched_vars = dict()
    fetched_vars["item_id"] = name_sanitize(str(thing_json["name"]))
    fetched_vars["item_title"] = thing_json["name"]
    

    if (
        thing_json.get("description") is None
        and thing_json.get("properties", {}).get("description") is None
    ):
        fetched_vars[
            "item_description"
        ] = "This is a STAC item."
    elif (
        thing_json.get("description") is not None
        and thing_json.get("properties", {}).get("description") is None
    ):
        fetched_vars["item_description"] = thing_json["description"]
    elif (
        thing_json.get("description") is None
        and thing_json.get("properties", {}).get("description") is not None
    ):
        fetched_vars["item_description"] = thing_json["properties"][
            "description"
        ]
    if thing_json.get("properties") is not None:
        fetched_vars["properties"] = thing_json.get("properties")

    return (
        fetched_vars["item_id"],
        fetched_vars["item_title"],
        fetched_vars["item_description"],
        fetched_vars["properties"]
    )

def replace_item_info( thing_json: dict):
    """
    to change auto generated ID, title with other

    Args:
        thing_json (dict): JSON response of a Thing or item.

    Returns:
        tuple: A tuple containing the following elements:
            - item_id (str): Unique identifier for the item.
            - item_title (str): Title of the item.
            - item_description (str): Description of the item.

    """
    fetched_vars = dict()
    (
        fetched_vars["item_id"],
        fetched_vars["item_title"],
        fetched_vars["item_description"],
        fetched_vars["properties"]
    ) = get_thing_info(thing_json=thing_json)
 

    return (
        fetched_vars["item_id"],
        fetched_vars["item_title"],
        fetched_vars["item_description"],
    )
