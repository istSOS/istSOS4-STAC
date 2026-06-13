"""
STA to DCAT-AP 3.0 transformer.

Consumes a HarvestedCatalog from connector.harvester and builds a complete
rdflib Graph conforming to DCAT-AP 3.0. The graph is serialized to JSON-LD
(application/ld+json) or Turtle by serialize_dcat().
"""