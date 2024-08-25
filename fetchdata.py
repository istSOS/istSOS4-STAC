
from shapely import geometry
from utils import *
from itemretr import *
from helper import *
import json



def fetchitem(sta_link: str,version: str,number_of_thing: int,old_vars : dict, asset_as: str):
    """
        Fetches information about a specific item/thing from a SensorThings API.
        Args:
            sta_link (str): The base URL of the SensorThings API.
            version (str): The version of the SensorThings API.
            number_of_thing (int): The ID of the item/thing to fetch.
            old_vars (dict): A dictionary containing previously fetched variables.
        Returns:
            fetched_vars (dict): A dictionary with updated fetched variables.
        """

    thing_url =f"{sta_link}/{version}/Things({number_of_thing})"

    datastreams_url = f"{thing_url}/Datastreams?$count=true&$top=1000"
    locations_url = f"{thing_url}/Locations?$count=true&$top=1000"
    


    if bool(old_vars) is False: 
        fetched_vars  = {}
    else:
        fetched_vars = old_vars

    fetched_vars["item_thing_url_json"] = thing_url

    
    thing_json = open_sta_entity_links(
        link=thing_url
    )
    datastreams_json = open_sta_entity_links(
        link=datastreams_url
    )
    locations_json = open_sta_entity_links(
        link=locations_url
    )


    if thing_json is not None and thing_json != {}:
        print("thing json not none")
        (fetched_vars["item_id"],
         fetched_vars["item_title"],
         fetched_vars["item_description"],
         ) = replace_item_info(thing_json=thing_json)

    # Fetching the STAC-Item Spatial and Temporal extent
    if locations_json is not None and locations_json != {}:

        if locations_json["@iot.count"] == 0:
            print("No location, looking for location in `observedArea` attribute of `Datastream`, and if it still couldn't find any coordinate, the spatial extent of the item will be None.")


        elif locations_json["@iot.count"] == 1:
            if (
                locations_json.get("value", [])[0]
                .get("location", {})
                .get("type")
                is not None
            ):
                fetched_vars["item_geometry"] = locations_json[
                    "value"
                ][0]["location"]["type"]
            else:
                print("No location, looking for location in `observedArea` attribute of `Datastream`, and if it still couldn't find any coordinate, the spatial extent of the item will be None.")

            if (
                locations_json.get("value", [])[0]
                .get("location", {})
                .get("coordinates")
                is not None
            ):
                fetched_vars["item_bbox"] = [locations_json["value"][0]["location"]["coordinates"]]
                
            else:
                print("No location, looking for location in `observedArea` attribute of `Datastream`, and if it still couldn't find any coordinate, the spatial extent of the item will be None.")


                
        elif locations_json["@iot.count"] > 1:
            geometry_list = []
            bbox_list = []
            locations_number = get_number_of_entities(
                link=thing_url,
                entity="Locations")
            list_of_locations_id = get_list_of_entities_id(
                link=thing_url,
                entity="Locations"
            )
            if locations_number == len(list_of_locations_id):
                for location_index, location_number in enumerate(
                    list_of_locations_id
                ):
                    locations_url_by_number = (
                        f"{thing_url}/Locations({location_number})"
                    )
                    locations_json_by_number = open_sta_entity_links(
                        locations_url_by_number,
                        
                    )
                    if (
                        locations_json_by_number.get(
                            "location", {}
                        ).get("type")
                        is not None
                    ):
                        geometry_list.append(
                            locations_json_by_number["location"][
                                "type"
                            ]
                        )
                    else:
                        print("The Location of the Thing does not have any geometry type in the list of locations, will look for the location in `observedArea` attribute of Datastream, and if it couldn't find any geometry there, the geometry of the item will be None.")
                        
                    if (
                        locations_json_by_number.get(
                            "location", {}
                        ).get("coordinates")
                        is not None
                    ):
                        bbox_list.append(
                            locations_json_by_number["location"][
                                "coordinates"
                            ]
                        )
                    else:
                        print("The Location of the Thing does not have any geometry type in the list of locations. So, it will look for the location in `observedArea` attribute of Datastream, and if it couldn't find any coordinate there, the spatial extent of the item will be None.")
                        
            else:
                print("The number of Locations in the Thing is not equal to the number of Locations in the list of locations. So, it will look for the location in `observedArea` attribute of Datastream, and if it couldn't find any geometry there, the geometry of the item will be None.")
                
            if fetched_vars.get("item_geometry") is None:
                fetched_vars["item_geometry"] = geometry_list
            if fetched_vars.get("item_bbox") is None:
                fetched_vars["item_bbox"] = bbox_list


    if datastreams_json is not None and datastreams_json != {}:
        print("datastream json")
        # fetching the STAC-Item Spatial and Temporal extent, 
        # Variable names, dimensions, description and units. 
        # Dimension names are lat, long and time.
        if datastreams_json["@iot.count"] == 0:
            if fetched_vars["item_bbox"] is None:
                print("The Thing does not have any Datastream. So, there is no temporal and spatial extent for the item.")

                return
            else:
                print("The Thing does not have any Datastream. So, there is no temporal extent for the item.")
                
                return
        elif datastreams_json["@iot.count"] == 1:

            datastreams_json_by_number = datastreams_json["value"][0]

            try:

                datastream_data = []
                datastream_value = datastreams_json_by_number["@iot.id"]
                datastream_data_temp = {}
                asset_fields = {}


                try:
                    datastream_data_temp["datstream_index"] = datastream_index
                except Exception as exc:
                    print("Datastream value")

                if asset_as == "GeoJSON" :
                    try:
                        asset_fields["href"] = str(f"{sta_link}/{version}/Datastreams({datastream_value})/Observations?$select=result,phenomenonTime&$resultFormat=GeoJSON")
                    except Exception as exc:
                            print("Datastream href not found",exc)
                else:
                    try:
                        asset_fields["href"] = str(f"{sta_link}/{version}/Datastreams({datastream_value})/Observations?$select=result,phenomenonTime&$resultFormat=CSV")
                    except Exception as exc:
                            print("Datastream href not found",exc)                            
                        
                try:
                    sensor_url = datastreams_json_by_number["@iot.selfLink"]
                except Exception as exc:
                    print("sensor url not found", exc)
                try:
                    asset_fields["title"] = datastreams_json_by_number["name"]
                except Exception as exc:
                    print("Title not found ",exc)
                try:
                    asset_fields["description"] = datastreams_json_by_number["description"]
                except Exception as exc:
                    print("Description not found",exc)
                try:
                    asset_fields["extra_fields"] = {}
                except Exception as exc:
                    print("Extra fields not found",exc)
                try:
                    asset_fields["extra_fields"]["unitOfMeasurement"] = datastreams_json_by_number["unitOfMeasurement"]
                except Exception as exc:
                    print("Datastream ID not found")
                try:
                    asset_fields["extra_fields"]["properties"] = datastreams_json_by_number["properties"]
                except Exception as exc:
                    print("Datastream ID not found")
                try:
                    sensor_url = datastreams_json_by_number["@iot.selfLink"]
                    sensor_url = sensor_url +"/Sensor"

                
                    sensor_details = open_sta_entity_links(sensor_url)
                    sname = sensor_details["name"]
                
                    asset_fields["extra_fields"]["SensorName"] = sname
                    asset_fields["extra_fields"]["data_csv"] = f"{sta_link}/Datastreams({datastream_value})/Observations?$select=result,phenomenonTime&$resultFormat=csv"
                    asset_fields["extra_fields"]["data_geojson"] = f"{sta_link}/Datastreams({datastream_value})/Observations?$select=result,phenomenonTime&$resultFormat=geojson"

                except Exception as exc:
                    print("Datastream ID not found ", exc)
                    asset_fields = {}

                datastream_data_temp["asset_fields"] = asset_fields


                datastream_data.append(datastream_data_temp)




            except Exception as e:
                print(f"Couldn't fetch datastream properties due to exception {e}")
            


            fetched_vars["assets"] = datastream_data

            if datastreams_json.get("observedArea") is not None:
                if (
                    datastreams_json["observedArea"].get("type")
                    is not None
                    and fetched_vars["item_geometry"] is None
                ):
                    fetched_vars[
                        "item_geometry"
                    ] = datastreams_json["observedArea"]["type"]
                elif (
                    datastreams_json["observedArea"].get("type")
                    is None
                    and fetched_vars["item_geometry"] is None
                ):
                    
                    print("The Datastream does not have any geometry type. It tries to find out the geometry type automatically.")
                    
                if (
                    datastreams_json["observedArea"].get("coordinates")
                    is not None
                    and fetched_vars["item_bbox"] is None
                ):
                    fetched_vars["item_bbox"] = [
                        datastreams_json["observedArea"]["coordinates"]
                    ]



                elif (
                    datastreams_json["observedArea"].get("coordinates")
                    is None
                    and fetched_vars["item_bbox"] is None
                ):
                    print("The Datastream does not have any coordinates. So, the spatial extent of the item will be None.")
                    
                    return
            else:
                print("The Datastream does not have any observedArea. So, the spatial extent of the item will be None.")
                
                return


            if datastreams_json.get("phenomenonTime") is not None:
                fetched_vars[
                    "item_datetime"
                ] = datastreams_json["phenomenonTime"]
                
            else:
                print("The Datastream does not have any phenomenonTime. So, the temporal extent of the item will be None.")
                
                return
        elif datastreams_json["@iot.count"] > 1:
            geometry_list = []
            bbox_list = []
            datetime_list = []
            variable_names_list = []
            variable_descriptions_list = []
            variable_units_list = []
            variable_dimensions_list = []
            dimension_names_list = []
            datastreams_number = get_number_of_entities(
                link=thing_url,
                entity="Datastreams",

            )

            list_of_datastreams_id = get_list_of_entities_id(
                link=thing_url,
                entity="Datastreams",
                
            )
            datastream_data = []
            if datastreams_number == len(list_of_datastreams_id):
                for datastream_index, datastream_number in enumerate(
                    list_of_datastreams_id
                ):
                    datastreams_url_by_number = (
                        f"{thing_url}/Datastreams({datastream_number})"
                    )
                    datastreams_json_by_number = open_sta_entity_links(
                        link=datastreams_url_by_number
                    )


                    try:

                        datastream_value = datastreams_json_by_number["@iot.id"]
                        datastream_data_temp = {}
                        asset_fields = {}

                        try:
                            datastream_data_temp["datstream_index"] = datastream_index
                        except Exception as exc:
                            print("Datastream id not available", exc)
  
                        
                        if asset_as == "GeoJSON" :
                            try:
                                asset_fields["href"] = str(f"{sta_link}/{version}/Datastreams({datastream_value})/Observations?$select=result,phenomenonTime&$resultFormat=GeoJSON")
                            except Exception as exc:
                                print("Datastream href not found",exc)
                        else:
                            try:
                                asset_fields["href"] = str(f"{sta_link}/{version}/Datastreams({datastream_value})/Observations?$select=result,phenomenonTime&$resultFormat=CSV")
                            except Exception as exc:
                                print("Datastream href not found",exc)                            
                        try:
                            sensor_url = datastreams_json_by_number["@iot.selfLink"]
                        except Exception as exc:
                            print("sensor url not found",exc)
                        try:
                            asset_fields["title"] = datastreams_json_by_number["name"]
                        except Exception as exc:
                            print("Datastream title not found",exc)
                        try:
                            asset_fields["description"] = datastreams_json_by_number["description"]
                        except Exception as exc:
                            print("Datastream description not found",exc)
                        try:
                            asset_fields["extra_fields"] = {}
                        except Exception as exc:
                            print("Datastream extra fields not found",exc)
                        try:
                            asset_fields["extra_fields"]["unitOfMeasurement"] = datastreams_json_by_number["unitOfMeasurement"]
                        except Exception as exc:
                            print("Datastream unit of measurment not found",exc)
                        try:
                            asset_fields["extra_fields"]["properties"] = datastreams_json_by_number["properties"]
                        except Exception as exc:
                            print("Datastream properties not found",exc)
                        try:
                            
                            sensor_url = datastreams_json_by_number["@iot.selfLink"]
                            asset_fields["extra_fields"]["datastream_link"] = sensor_url
                            sensor_url = sensor_url +"/Sensor"

                        
                            sensor_details = open_sta_entity_links(sensor_url)
                            sname = sensor_details["name"]
                        
                            asset_fields["extra_fields"]["SensorName"] = sname
                            asset_fields["extra_fields"]["data_csv"] = f"{sta_link}/Datastreams({datastream_value})/Observations?$select=result,phenomenonTime&$resultFormat=csv"
                            asset_fields["extra_fields"]["data_geojson"] = f"{sta_link}/Datastreams({datastream_value})/Observations?$select=result,phenomenonTime&$resultFormat=geojson"

                        except Exception as exc:
                            print("Datastream ID not found", exc)
                            asset_fields = {}
   
                        datastream_data_temp["asset_fields"] = asset_fields
  

                        datastream_data.append(datastream_data_temp)

 

                    except Exception as e:
                        print(f"couldn't fetch datastream properties due to exception {e}")



                    fetched_vars["assets"] = datastream_data


                    if (
                        datastreams_json_by_number.get("observedArea")
                        is not None
                    ):
                        if (
                            datastreams_json_by_number.get(
                                "observedArea", {}
                            ).get("type")
                            is not None
                            and fetched_vars.get(
                                "item_geometry"
                            )
                            is None
                        ):
                            geometry_list.append(
                                datastreams_json_by_number[
                                    "observedArea"
                                ]["type"]
                            )
                        elif (
                            datastreams_json_by_number.get(
                                "observedArea", {}
                            ).get("type")
                            is None
                            and fetched_vars["item_geometry"]
                            is None
                        ):
                            print("The Datastream does not have any geometry type. It tries to find out the geometry type automatically.")
                            
                        if (
                            datastreams_json_by_number.get(
                                "observedArea", {}
                            ).get("coordinates")
                            is not None
                            and fetched_vars.get("item_bbox")
                            is None
                        ):
                            bbox_list.append(
                                datastreams_json_by_number[
                                    "observedArea"
                                ]["coordinates"]
                            )

                        elif (
                            datastreams_json_by_number.get(
                                "observedArea", {}
                            ).get("coordinates")
                            is None
                            and fetched_vars.get("item_bbox")
                            is None
                        ):
                            print("The Datastream does not have any coordinates. So, the spatial extent of the item will be None.")    
                    else:
                        print("The Datastream does not have any observedArea. So, the spatial extent of the item will be None.")
                        

                    
                    
                    if (
                        datastreams_json_by_number.get(
                            "phenomenonTime"
                        )
                        is not None
                        and fetched_vars.get("item_datetime")
                        is None
                    ):
                        datetime_list.append(
                            datastreams_json_by_number[
                                "phenomenonTime"
                            ]
                        )
                    else:
                        datetime_list.append(None)
                        print("The Datastream does not have any phenomenonTime. So, the temporal extent of the item will be None."
                        )


            else:
                print("The number of Locations in the Thing is not equal to the number of Locations in the list of locations. So, it will look for the location in `observedArea` attribute of Datastream, and if it couldn't find any geometry there, the geometry of the item will be None."
                )

                return

            if fetched_vars.get("item_geometry") is None:
                fetched_vars["item_geometry"] = geometry_list
            if fetched_vars.get("item_bbox") is None:
                fetched_vars["item_bbox"] = bbox_list
            if fetched_vars.get("item_datetime") is None:
                fetched_vars["item_datetime"] = datetime_list
            

 
    fetched_vars["properties"] = thing_json.get("properties")

    fetched_vars["item_footprint"] = geometryf(bbox=fetched_vars["item_bbox"],geometry_type=fetched_vars["item_geometry"])


    if fetched_vars.get("collection_footprint") is None:

        fetched_vars[
            "collection_footprint"
        ] = fetched_vars["item_footprint"]

    item(fetched_vars)


    fetched_vars["collection_footprint"] = geometry.shape(
        fetched_vars["item_footprint"]
    ).union(
        geometry.shape(fetched_vars["collection_footprint"])
    )

    fetched_vars["collection_bbox"] = list(
        fetched_vars["collection_footprint"].bounds)


    if fetched_vars.get("collection_datetime") is None:


        fetched_vars["collection_datetime"] = []
    fetched_vars["collection_datetime"].extend(
        fetched_vars["item_datetime"]
    )


    return fetched_vars


