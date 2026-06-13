"""
REST API layer for the istSOS Metadata Connector.

This module is the HTTP boundary of the connector. It does three things:
  1. Receives an HTTP request.
  2. Calls get_catalog(config, cache) to obtain the current HarvestedCatalog
     (from the TTL cache or from a fresh harvest if the cache is cold).
  3. Passes the catalog to the appropriate transformer and returns the result.

No transformation logic, no caching logic, and no harvesting logic lives here.
Those are the transformers', cache's, and harvester's concerns respectively.

Endpoints:
  STAC
    GET /stac                                              -> root Catalog
    GET /stac/collections                                  -> all Collections
    GET /stac/collections/{collection_id}                  -> single Collection
    GET /stac/collections/{collection_id}/items            -> Items in Collection
    GET /stac/collections/{collection_id}/items/{item_id}  -> single Item

  DCAT
    GET /dcat/catalog      -> DCAT-AP 3.0 JSON-LD (application/ld+json)
    GET /dcat/catalog.ttl  -> DCAT-AP 3.0 Turtle  (text/turtle)

  Utility
    GET    /health         -> liveness probe
    GET    /cache/status   -> cache introspection
    DELETE /cache          -> manual cache flush

See API-Layer-Reference.md for full design rationale.
"""