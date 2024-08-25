import sys
from datetime import datetime
from typing import Union
import time
from shapely import geometry
import os


def datetimef( date_time: str) -> list:
    """
    convert date-time to the ISO format.

    Args:
    date_time(str) : date-time of entity to convert to ISO format
    """

    try:

        datetime_begin = date_time.split("/")[0]
        datetime_end = date_time.split("/")[1]
        datetime_begin_formatted = datetime.strptime(
            datetime_begin, "%Y-%m-%dT%H:%M:%SZ"
        )
        datetime_end_formatted = datetime.strptime(
            datetime_end, "%Y-%m-%dT%H:%M:%SZ"
        )

        return [datetime_begin_formatted, datetime_end_formatted]
    except Exception as e:

        print(f"Could not convert the date-time to the ISO format due to exception {e}")
        
        return None

def geometryf( bbox: list, geometry_type: str) -> str:
    """
    Convert the bbox to the GeoJSON format.

    Args:
        bbox (str) : bbox of item 
        geometry_type (str) : geometry of item
    """
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

def bbox( bbox: list, geometry: Union[str, list]) -> list:
    """
    Convert the bbox to the GeoJSON format.

    Args:
        bbox (list): A list representing the bounding box. 
        geometry (Union[str, list]): The geometry type(s) associated with the bbox.
           
    Returns:
        list: A modified bounding box in GeoJSON format.

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

def collectiondt( date_times_list: list) -> list:
    """
    Process the items attributes to create the collection temporal extent.

    Args:
        date_times_list (list): A list of `datetime` objects representing the time range of fetched items.
            

    Returns:
        list: A datetime interval in list form containing two `datetime` objects representing the temporal extent of the collection
       
    """

    date_times_list = sorted(date_times_list)
    return [date_times_list[0], date_times_list[-1]]

def item( fetched_vars: dict):
    """
    Process the items attributes to create the item's temporal extent.

    Args:
        fetched_vars (dict): A dictionary containing various attributes of the items

    Returns:
        dict: A dictionary with the updated `item_datetime` and `item_bbox` reflecting the processed temporal and spatial extents.
       

    """
    all_item_datetime = []

    if fetched_vars.get("item_datetime") is not None:
        for item_datetime in fetched_vars["item_datetime"]:
            print(item_datetime)
            if item_datetime is not None:
                list_start_end_datetime = datetimef(item_datetime)
                if list_start_end_datetime is not None:
                    all_item_datetime.extend(list_start_end_datetime)



        all_item_datetime = sorted(all_item_datetime)

        fetched_vars["item_datetime"] = [
            all_item_datetime[0],
            all_item_datetime[-1],
        ]
    if (
        fetched_vars.get("item_bbox") is not None
        and fetched_vars.get("item_geometry") is not None
    ):
        fetched_vars["item_bbox"] = bbox(
            fetched_vars["item_bbox"], fetched_vars["item_geometry"]
        )

    
    return fetched_vars

def check_existance(path_to_check: str) -> bool:
    """
    Check existance of catalog or collection.
    Args:
        path_to_check (str) : path of catalog or collection to check existance
    Returns:
        bool : True or False depending on existance
    """
   
    print(f"checking existance on path {path_to_check}")

    if os.path.exists(path_to_check):
        return True
    else:
        return False



