"""
STA to STAC 1.0 transformer.

Consumes a HarvestedCatalog from connector.harvester and builds a complete
STAC 1.0 Catalog, with one Collection per Thing and one Item per Datastream.
All objects are constructed using pystac and serialized to plain dicts for
the FastAPI layer in api.py.
"""