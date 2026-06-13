"""
Harvesting layer for the istSOS Metadata Connector.

Fetches metadata from a live istSOS4 SensorThings API instance, normalises
it into typed internal representations, and returns a HarvestedCatalog
consumed by the STAC and DCAT-AP transformers.
"""