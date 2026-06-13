"""
In-memory TTL cache for the harvested catalog.

Stores one HarvestedCatalog per configured STA deployment, keyed by
base URL. The cache is never partially written — a transformer either
reads a complete HarvestedCatalog or the harvest raises and the request
fails.
"""