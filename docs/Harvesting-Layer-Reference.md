# Harvesting Layer Reference

**Project:** istSOS Metadata Connector for Data Spaces and STAC
**Author:** Zala Vishmayraj
**Status:** Design, pre-implementation
**Scope:** `connector/harvester.py`, `connector/cache.py`, internal data models consumed by `stac_transformer.py` and `dcat_transformer.py`

---

## Design

This section is a self-contained overview of the harvesting layer. It is intended for quick review.

**What it does.** The harvester reads metadata directly from the istSOS4 Postgres database via a single asyncpg JOIN query, normalizes the flat result rows into typed Python dataclasses, and writes the result to Redis. The STAC and DCAT-AP transformers consumethe cached representation and never touch Postgres directly.

**What it does not do.** The harvester does not compute derived fields. Temporal extents, spatial bounding boxes, keyword sets, observable property deduplication -- none of that happens here. The harvester stores what Postgres returns. All computation belongs in the transformers, which consume the same normalized data but derive different things from it. This boundary is deliberate: the STAC and DCAT-AP transformers need the same raw data but produce structurally different outputs. Computing shared derived fields in the harvester would mean making transformer-level decisions in the wrong layer, and would create hidden coupling between the transformers via harvester side effects.

**Why direct Postgres instead of STA HTTP pagination.** Benchmark tests against a production-scale STA deployment (5,610 Things, 22,941 Datastreams) showed 42.4 seconds fetch time across 57 sequential paginated HTTP requests. The same data via a single Postgres JOIN completes in well under a second. The STA HTTP layer adds no value for a connector that runs inside the same infrastructure as istSOS4 itself.

**The harvest query.** One asyncpg `fetch()` call returns everything both transformers need:

```sql
SELECT
    t.id                            AS thing_id,
    t.name                          AS thing_name,
    t.description                   AS thing_description,
    t.properties                    AS thing_properties,
    ST_AsGeoJSON(l.location)::json  AS location_geometry,
    d.id                            AS ds_id,
    d.name                          AS ds_name,
    d.description                   AS ds_description,
    d."unitOfMeasurement"           AS uom,
    d."observationType"             AS observation_type,
    d."observedArea"                AS observed_area,
    d."phenomenonTime"              AS phenomenon_time,
    d."resultTime"                  AS result_time,
    d.properties                    AS ds_properties,
    op.id                           AS op_id,
    op.name                         AS op_name,
    op.description                  AS op_description,
    op.definition                   AS op_definition,
    op.properties                   AS op_properties,
    s.id                            AS sensor_id,
    s.name                          AS sensor_name,
    s.description                   AS sensor_description,
    s."encodingType"                AS sensor_encoding_type,
    s.metadata                      AS sensor_metadata,
    s.properties                    AS sensor_properties
FROM sensorthings."Thing" t
LEFT JOIN sensorthings."Thing_Location" tl  ON tl.thing_id = t.id
LEFT JOIN sensorthings."Location" l         ON l.id = tl.location_id
LEFT JOIN sensorthings."Datastream" d       ON d.thing_id = t.id
LEFT JOIN sensorthings."ObservedProperty" op ON op.id = d."observedproperty_id"
LEFT JOIN sensorthings."Sensor" s           ON s.id = d.sensor_id
ORDER BY t.id, d.id;
```

`ST_AsGeoJSON(l.location)::json` casts the PostGIS geometry column to a parsed GeoJSON dict rather than raw WKB bytes. The `::json` cast means asyncpg returns it as a Python dict directly, not a string.

**Row grouping.** The query returns one flat row per (Thing, Datastream) pair. A Thing with three Datastreams produces three rows, all with identical Thing columns. `_build_catalog()` groups rows by `thing_id` using a dict keyed on `thing_id`, building up the `locations` and `datastreams` lists incrementally. Things with no Datastreams (all Thing columns present, all Datastream columns NULL) are included with an empty `datastreams` list.

**Cache invalidation.** Four statement-level Postgres triggers on `Thing`, `Datastream`, `Sensor`, and `ObservedProperty` fire `pg_notify('metadata_changed', ...)` on any INSERT, UPDATE, or DELETE. A dedicated asyncpg connection outside the pool listens on the `metadata_changed` channel. On notification, `invalidate()` deletes all three Redis keys (`harvested:raw`, `stac:catalog`, `dcat:catalog`). The next incoming request triggers a full re-harvest. There is no TTL -- cache lifetime is entirely event-driven.

`FOR EACH STATEMENT` triggers are used rather than `FOR EACH ROW`. A bulk Observation insert must not fire thousands of notifications. One notification per DML statement is the correct granularity since the response is always a full re-harvest regardless.

---

## Internal data model

Two dataclasses: `HarvestedThing` and `HarvestedCatalog`. Everything nested inside a Thing -- Locations, Datastreams, ObservedProperties, Sensors, UnitOfMeasurements -- is stored as normalized dicts.

**Normalization decisions:**
- Postgres column aliases (e.g. `thing_id`, `ds_name`) are mapped to clean field names
- `camelCase` values from JSON columns (e.g. `unitOfMeasurement`) are left as-is inside
  their dicts since they come from Postgres JSON columns, not Python naming
- The Location `location` PostGIS column is aliased to `geometry` to avoid confusion
  with the Location entity itself
- All optional fields become `None` when null rather than being absent from the dict

**HarvestedCatalog (dataclass):**
```
things: list[HarvestedThing]
harvested_at: str               # ISO 8601 UTC, set when query completes
thing_count: int                # always equals len(things), set in __post_init__
```

**HarvestedThing (dataclass):**
```
id: int
name: str
description: str | None
properties: dict | None
locations: list[dict]           # always a list, empty if no Locations
datastreams: list[dict]         # always a list, empty if no Datastreams
```

**Location dict:**
```
id: int
name: str
description: str | None
properties: dict | None

encoding_type: str
geometry: dict | None           # parsed GeoJSON dict from ST_AsGeoJSON, renamed from "location"
```

**Datastream dict:**
```
id: int
name: str
description: str | None
properties: dict | None

phenomenon_time: str | None     # raw interval string "start/end", not parsed
result_time: str | None
observed_area: dict | None      # raw GeoJSON Polygon dict
observation_type: str | None
unit_of_measurement: dict | None
observed_property: dict | None
sensor: dict | None
```

**UnitOfMeasurement dict:**
```
name: str | None
symbol: str | None
definition: str | None
```

**ObservedProperty dict:**
```
id: int
name: str
description: str | None
properties: dict | None

definition: str | None
```

**Sensor dict:**
```
id: int
name: str
description: str | None
properties: dict | None

encoding_type: str
metadata: str | None
```

Note: `self_link` fields are absent from all dicts. The STA HTTP selfLink was only needed for building STA asset URLs in the old HTTP-harvesting architecture. In the integrated architecture, asset URLs pointing back to the STA API are constructed from the istSOS4 `HOSTNAME` and `SUBPATH` settings where needed, not stored in the catalog.

---

## Public interface

```python
async def harvest(pool: asyncpg.Pool) -> HarvestedCatalog:
    ...

async def listen_for_changes(
    pool: asyncpg.Pool,
    on_change: Callable[[], Awaitable[None]],
) -> None:
    ...
```

`harvest()` runs the JOIN query and calls `_build_catalog()`. Never touches cache.

`listen_for_changes()` opens a dedicated asyncpg connection outside the pool, registers a listener on `metadata_changed`, and blocks on `conn.wait_closed()` for the lifetime of the process. If the connection drops, `wait_closed()` returns and the caller's reconnect loop (in `main.py` lifespan) retries with backoff.

`cache.py` exposes `get_or_harvest(redis, pool)` which is what the transformer layer calls -- returns the cached `HarvestedCatalog` if present in Redis, otherwise calls `harvest()` and writes the result.

---

## Transformer contract (what downstream code can rely on)

1. `HarvestedCatalog.things` is always a list. Never `None`. May be empty.
2. `HarvestedThing.locations` is always a list. Never `None`. May be empty.
3. `HarvestedThing.datastreams` is always a list. Never `None`. May be empty.
4. Every `HarvestedThing.id` is unique within a `HarvestedCatalog`.
5. Every Datastream dict `id` is globally unique across all Things in the catalog.
6. `geometry` in a Location dict, if not `None`, is a dict with at minimum a `"type"` key. Not validated as well-formed GeoJSON.
7. `phenomenon_time` in a Datastream dict, if not `None`, is a string in `"start/end"` format where start and end are ISO 8601 instants. Not parsed.
8. `observed_area` in a Datastream dict, if not `None`, is a dict with at minimum a `"type"` key.
9. `name` on `HarvestedThing` is never `None`. Defaults to `""` with a warning if the Postgres row returns null. Same applies to `name` inside Location, Datastream, ObservedProperty, and Sensor dicts.
10. The cache is never partially written.
11. `HarvestedCatalog.harvested_at` is a valid ISO 8601 UTC string.
12. `HarvestedCatalog` and its nested structures must not be mutated by the transformer.