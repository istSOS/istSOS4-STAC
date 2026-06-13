"""
STAC Transformation Benchmark

Fetches raw metadata from a live istSOS4 SensorThings API instance,
runs it through the STAC transformer, times the transformation in isolation,
and saves the output to a JSON file.

Network I/O (fetch) and transformation are timed separately so the
benchmark result reflects only transformation cost.

Usage:
    python benchmark_stac.py

Output:
    - JSON file with the full STAC catalog (default: benchmark_output.json)
    - Timing summary printed to stdout
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import aiohttp

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.FileHandler("benchmark.log", mode="w"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("benchmark")


# Minimal config -> will be part of config.py
@dataclass
class BenchmarkConfig:
    sta_base_url: str = "https://airquality-frost.k8s.ilt-dmz.iosb.fraunhofer.de/v1.1"
    stac_root_href: str = "http://localhost:8020/stac"
    page_size: int = 100
    timeout_seconds: float = 30.0
    output_path: str = "benchmark_output.json"


# Inline data models -> will be part of harvester.py
@dataclass
class HarvestedThing:
    id: int
    self_link: str
    name: str
    description: Optional[str]
    properties: Optional[dict]
    locations: list[dict]
    datastreams: list[dict]


@dataclass
class HarvestedCatalog:
    base_url: str
    conformance: list[str]
    things: list[HarvestedThing]
    harvested_at: str
    thing_count: int = field(init=False)

    def __post_init__(self) -> None:
        self.thing_count = len(self.things)


# Fetch helpers -> basic utility functions
async def _fetch_json(session: aiohttp.ClientSession, url: str) -> dict[str, Any]:
    async with session.get(url) as resp:
        resp.raise_for_status()
        return await resp.json(content_type=None)


async def _paginate_things(
    session: aiohttp.ClientSession,
    initial_url: str,
) -> list[dict]:
    raw_things: list[dict] = []
    url: Optional[str] = initial_url
    page = 0

    while url:
        payload = await _fetch_json(session, url)
        items = payload.get("value", [])
        raw_things.extend(items)
        page += 1
        url = payload.get("@iot.nextLink") or None
        logger.info("Fetched page %d -- %d Things so far", page, len(raw_things))

    return raw_things


def _parse_uom(raw: dict) -> dict:
    return {
        "name": raw.get("name"),
        "symbol": raw.get("symbol"),
        "definition": raw.get("definition"),
    }


def _parse_observed_property(raw: dict) -> Optional[dict]:
    if not raw.get("@iot.id"):
        return None
    return {
        "id": raw["@iot.id"],
        "self_link": raw.get("@iot.selfLink", ""),
        "name": raw.get("name", ""),
        "description": raw.get("description"),
        "definition": raw.get("definition"),
        "properties": raw.get("properties") or None,
    }


def _parse_sensor(raw: dict) -> Optional[dict]:
    if not raw.get("@iot.id"):
        return None
    return {
        "id": raw["@iot.id"],
        "self_link": raw.get("@iot.selfLink", ""),
        "name": raw.get("name", ""),
        "description": raw.get("description"),
        "encoding_type": raw.get("encodingType", ""),
        "metadata": raw.get("metadata"),
        "properties": raw.get("properties") or None,
    }


def _parse_datastream(raw: dict, thing_id: int) -> Optional[dict]:
    ds_id = raw.get("@iot.id")
    if ds_id is None:
        return None
    uom_raw = raw.get("unitOfMeasurement")
    return {
        "id": ds_id,
        "self_link": raw.get("@iot.selfLink", ""),
        "name": raw.get("name", ""),
        "description": raw.get("description"),
        "phenomenon_time": raw.get("phenomenonTime"),
        "result_time": raw.get("resultTime"),
        "observed_area": raw.get("observedArea"),
        "observation_type": raw.get("observationType"),
        "unit_of_measurement": _parse_uom(uom_raw) if uom_raw else None,
        "properties": raw.get("properties") or None,
        "observed_property": _parse_observed_property(raw["ObservedProperty"])
            if raw.get("ObservedProperty") else None,
        "sensor": _parse_sensor(raw["Sensor"])
            if raw.get("Sensor") else None,
    }


def _parse_location(raw: dict) -> Optional[dict]:
    if not raw.get("@iot.id"):
        return None
    return {
        "id": raw["@iot.id"],
        "name": raw.get("name", ""),
        "geometry": raw.get("location"),
    }


def _parse_thing(raw: dict) -> Optional[HarvestedThing]:
    thing_id = raw.get("@iot.id")
    if thing_id is None:
        return None

    locations = [
        loc for r in raw.get("Locations", [])
        if (loc := _parse_location(r)) is not None
    ]
    datastreams = [
        ds for r in raw.get("Datastreams", [])
        if (ds := _parse_datastream(r, thing_id)) is not None
    ]

    return HarvestedThing(
        id=thing_id,
        self_link=raw.get("@iot.selfLink", ""),
        name=raw.get("name", ""),
        description=raw.get("description"),
        properties=raw.get("properties") or None,
        locations=locations,
        datastreams=datastreams,
    )


async def fetch_catalog(config: BenchmarkConfig) -> tuple[HarvestedCatalog, float]:
    """Fetch raw STA metadata and normalise into HarvestedCatalog."""
    timeout = aiohttp.ClientTimeout(total=config.timeout_seconds)
    expand = "Locations,Datastreams($expand=ObservedProperty,Sensor)"
    initial_url = (
        f"{config.sta_base_url}/Things"
        f"?$expand={expand}&$top={config.page_size}"
    )

    logger.info("Fetching from %s", config.sta_base_url)
    fetch_start = time.monotonic()

    async with aiohttp.ClientSession(timeout=timeout) as session:
        raw_things = await _paginate_things(session, initial_url)

    fetch_elapsed = time.monotonic() - fetch_start

    things = [t for r in raw_things if (t := _parse_thing(r)) is not None]
    total_ds = sum(len(t.datastreams) for t in things)
    logger.info(
        "Fetch complete: %d Things, %d Datastreams, fetch_time=%.3fs",
        len(things), total_ds, fetch_elapsed,
    )

    catalog = HarvestedCatalog(
        base_url=config.sta_base_url,
        conformance=[],
        things=things,
        harvested_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    return catalog, fetch_elapsed


# STAC transformer -> will be part of stac_transformer.py

# All links are built manually using the stac_root_href so they point at
# real API endpoints instead of static .json file paths.
def _parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _parse_phenomenon_time(pt: str) -> tuple[Optional[datetime], Optional[datetime]]:
    parts = pt.split("/", 1)
    start = _parse_iso(parts[0].strip())
    end_str = parts[1].strip() if len(parts) > 1 else ""
    end = _parse_iso(end_str) if end_str and end_str != ".." else None
    return start, end


def _extract_all_coordinates(geometry: dict) -> list[list[float]]:
    geom_type = geometry.get("type", "")
    coords = geometry.get("coordinates")
    if geom_type == "Point" and coords:
        return [coords[:2]]
    if geom_type in ("MultiPoint", "LineString") and coords:
        return [c[:2] for c in coords]
    if geom_type == "Polygon" and coords:
        return [c[:2] for c in coords[0]]
    if geom_type == "MultiPolygon" and coords:
        result: list[list[float]] = []
        for polygon in coords:
            result.extend(c[:2] for c in polygon[0])
        return result
    if geom_type == "GeometryCollection":
        result = []
        for geom in geometry.get("geometries", []):
            result.extend(_extract_all_coordinates(geom))
        return result
    return []


def _bbox_from_geometry(geometry: Optional[dict]) -> Optional[list[float]]:
    if geometry is None:
        return None
    coords = _extract_all_coordinates(geometry)
    if not coords:
        return None
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return [min(lons), min(lats), max(lons), max(lats)]


def _union_bboxes(bboxes: list[list[float]]) -> list[float]:
    return [
        min(b[0] for b in bboxes), min(b[1] for b in bboxes),
        max(b[2] for b in bboxes), max(b[3] for b in bboxes),
    ]


def _resolve_item_geometry(
    thing: HarvestedThing, ds: dict
) -> tuple[Optional[dict], Optional[list[float]]]:
    observed_area = ds.get("observed_area")
    if observed_area is not None:
        return observed_area, _bbox_from_geometry(observed_area)
    if thing.locations:
        geom = thing.locations[0].get("geometry")
        if geom is not None:
            return geom, _bbox_from_geometry(geom)
    return None, None


def _extract_collection_keywords(thing: HarvestedThing) -> list[str]:
    seen: set[str] = set()
    keywords: list[str] = []

    def _add(kw: str) -> None:
        kw = kw.strip()
        if kw and kw not in seen:
            seen.add(kw)
            keywords.append(kw)

    _add(thing.name)
    for ds in thing.datastreams:
        op = ds.get("observed_property")
        if op and op.get("name"):
            for part in op["name"].split(":"):
                _add(part)
        for kw in (ds.get("properties") or {}).get("keywords", []):
            if isinstance(kw, str):
                _add(kw)
    return keywords


def _compose_item_description(ds: dict, thing: HarvestedThing) -> str:
    parts = []
    if ds.get("description"):
        parts.append(ds["description"])
    op = ds.get("observed_property")
    if op and op.get("description"):
        parts.append(op["description"])
    sensor = ds.get("sensor")
    if sensor and sensor.get("description"):
        parts.append(sensor["description"])
    return " | ".join(p for p in parts if p) or ds.get("name", "")


def _build_item_dict(
    thing: HarvestedThing,
    ds: dict,
    collection_id: str,
    stac_root: str,
) -> Optional[dict]:
    """Build a STAC Item as a plain dict with API hrefs."""
    pt = ds.get("phenomenon_time")
    if not pt:
        logger.warning("Skipping datastream %s -- no phenomenonTime", ds.get("id"))
        return None

    start, end = _parse_phenomenon_time(pt)
    if start is None:
        logger.warning("Skipping datastream %s -- unparseable phenomenonTime", ds.get("id"))
        return None

    item_datetime = end if end is not None else start
    geometry, bbox = _resolve_item_geometry(thing, ds)
    item_id = f"datastream-{ds['id']}"
    item_href = f"{stac_root}/collections/{collection_id}/items/{item_id}"
    collection_href = f"{stac_root}/collections/{collection_id}"

    properties: dict = {
        "datetime": item_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "title": f"{thing.name} - {ds.get('name', '')}",
        "description": _compose_item_description(ds, thing),
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat() if end is not None else None,
        "thing_id": thing.id,
        "thing_name": thing.name,
        "datastream_id": ds.get("id"),
    }

    uom = ds.get("unit_of_measurement")
    if uom:
        properties["unit_of_measurement"] = uom

    obs_type = ds.get("observation_type")
    if obs_type:
        properties["observation_type"] = obs_type

    op = ds.get("observed_property")
    if op:
        if op.get("name"):
            properties["observed_property"] = op["name"]
        if op.get("id") is not None:
            properties["observed_property_id"] = op["id"]
        if op.get("definition") is not None:
            properties["observed_property_definition"] = op["definition"]

    sensor = ds.get("sensor")
    if sensor:
        if sensor.get("name"):
            properties["sensor_name"] = sensor["name"]
        if sensor.get("id") is not None:
            properties["sensor_id"] = sensor["id"]
        if sensor.get("metadata") is not None:
            properties["sensor_metadata"] = sensor["metadata"]

    _RESERVED = frozenset({
        "observedArea", "phenomenonTime", "resultTime",
        "created", "updated", "platform", "resolution",
        "instruments", "keywords", "license", "providers",
    })
    for k, v in (ds.get("properties") or {}).items():
        if k not in _RESERVED and k not in properties:
            properties[k] = v

    base_href = ds.get("self_link", "")
    ds_name = ds.get("name", "")
    assets = {
        "observations_json": {
            "href": f"{base_href}/Observations" if base_href else "",
            "type": "application/json",
            "title": f"{ds_name} -- JSON observations feed",
            "roles": ["data"],
        },
        "observations_csv": {
            "href": f"{base_href}/Observations?$resultFormat=CSV" if base_href else "",
            "type": "text/csv",
            "title": f"{ds_name} -- CSV export",
            "roles": ["data"],
        },
        "datastream": {
            "href": base_href,
            "type": "application/json",
            "title": f"STA Datastream: {ds_name}",
            "roles": ["metadata"],
        },
    }

    links = [
        {"rel": "self", "href": item_href, "type": "application/geo+json"},
        {"rel": "root", "href": stac_root, "type": "application/json"},
        {"rel": "parent", "href": collection_href, "type": "application/json"},
        {"rel": "collection", "href": collection_href, "type": "application/json", "title": thing.name},
    ]
    if base_href:
        links.append({"rel": "sta_datastream", "href": base_href, "type": "application/json"})

    return {
        "type": "Feature",
        "stac_version": "1.0.0",
        "stac_extensions": [],
        "id": item_id,
        "geometry": geometry,
        "bbox": bbox,
        "properties": properties,
        "links": links,
        "assets": assets,
        "collection": collection_id,
    }


def _build_collection_dict(
    thing: HarvestedThing,
    items: list[dict],
    stac_root: str,
) -> dict:
    """Build a STAC Collection as a plain dict with API hrefs."""
    collection_id = f"thing-{thing.id}"
    collection_href = f"{stac_root}/collections/{collection_id}"
    items_href = f"{stac_root}/collections/{collection_id}/items"

    # Spatial extent
    bboxes = [item["bbox"] for item in items if item.get("bbox") is not None]
    if not bboxes:
        for loc in thing.locations:
            geom = loc.get("geometry")
            if geom:
                bbox = _bbox_from_geometry(geom)
                if bbox:
                    bboxes.append(bbox)
    spatial_bbox = _union_bboxes(bboxes) if bboxes else [-180.0, -90.0, 180.0, 90.0]

    # Temporal extent
    starts, ends = [], []
    for item in items:
        s = item["properties"].get("start_datetime")
        e = item["properties"].get("end_datetime")
        if s:
            dt = _parse_iso(s)
            if dt:
                starts.append(dt)
        ends.append(_parse_iso(e) if e else None)

    collection_start = min(starts).isoformat() if starts else None
    collection_end = (
        max(e for e in ends if e is not None).isoformat()
        if ends and all(e is not None for e in ends)
        else None
    )

    # Summaries
    keywords = _extract_collection_keywords(thing)
    op_defs, unit_symbols = [], []
    for ds in thing.datastreams:
        op = ds.get("observed_property")
        if op and op.get("definition") is not None:
            op_defs.append(str(op["definition"]))
        uom = ds.get("unit_of_measurement")
        if uom and uom.get("symbol"):
            unit_symbols.append(uom["symbol"])

    links = [
        {"rel": "self", "href": collection_href, "type": "application/json"},
        {"rel": "root", "href": stac_root, "type": "application/json"},
        {"rel": "parent", "href": stac_root, "type": "application/json"},
        {"rel": "items", "href": items_href, "type": "application/geo+json"},
    ]
    if thing.self_link:
        links.append({"rel": "sta_thing", "href": thing.self_link, "type": "application/json"})

    return {
        "type": "Collection",
        "stac_version": "1.0.0",
        "id": collection_id,
        "title": thing.name or None,
        "description": thing.description or f"STAC Collection for SensorThings Thing: {thing.name}",
        "keywords": keywords,
        "extent": {
            "spatial": {"bbox": [spatial_bbox]},
            "temporal": {"interval": [[collection_start, collection_end]]},
        },
        "links": links,
        "license": "other",
        "thing_id": thing.id,
        "thing_properties": thing.properties,
        "summaries": {
            "observed_property_definitions": list(dict.fromkeys(op_defs)),
            "unit_symbols": list(dict.fromkeys(unit_symbols)),
        },
        # items kept here for internal use only -- stripped before serving /collections
        "_items": items,
    }


def transform_to_stac(
    catalog: HarvestedCatalog,
    stac_root_href: str,
) -> tuple[dict, int]:
    """
    Build a complete STAC catalog as plain dicts with correct API hrefs.
    This is the function being benchmarked -- pure CPU, no I/O.
    """
    stac_root = stac_root_href.rstrip("/")

    catalog_id = (
        "istsos-connector-"
        + catalog.base_url.replace("://", "-").replace("/", "-").strip("-")
    )

    skipped_items = 0
    collections: list[dict] = []

    for thing in catalog.things:
        collection_id = f"thing-{thing.id}"
        items = []
        for ds in thing.datastreams:
            item = _build_item_dict(thing, ds, collection_id, stac_root)
            if item is not None:
                items.append(item)
            else:
                skipped_items += 1
        collections.append(_build_collection_dict(thing, items, stac_root))

    root_catalog = {
        "type": "Catalog",
        "stac_version": "1.0.0",
        "id": catalog_id,
        "description": (
            f"istSOS4 deployment: {catalog.thing_count} Things, "
            f"harvested from {catalog.base_url} at {catalog.harvested_at}."
        ),
        "links": [
            {"rel": "self", "href": stac_root, "type": "application/json"},
            {"rel": "root", "href": stac_root, "type": "application/json"},
        ] + [
            {
                "rel": "child",
                "href": f"{stac_root}/collections/{col['id']}",
                "type": "application/json",
                "title": col.get("title") or col["id"],
            }
            for col in collections
        ],
    }

    return {
        "catalog": root_catalog,
        "collections": collections,
    }, skipped_items


# Main benchmark runner
async def run(config: BenchmarkConfig) -> None:
    catalog, fetch_elapsed = await fetch_catalog(config)
    total_datastreams = sum(len(t.datastreams) for t in catalog.things)

    logger.info("FETCH SUMMARY")
    logger.info("  STA instance   : %s", config.sta_base_url)
    logger.info("  Things         : %d", catalog.thing_count)
    logger.info("  Datastreams    : %d", total_datastreams)
    logger.info("  Fetch time     : %.3fs", fetch_elapsed)

    ITERATIONS = 1
    logger.info("Running transformation x%d iterations for timing accuracy...", ITERATIONS)

    stac_dict: dict = {}
    skipped = 0
    transform_start = time.monotonic()
    for _ in range(ITERATIONS):
        stac_dict, skipped = transform_to_stac(catalog, config.stac_root_href)
    transform_elapsed = time.monotonic() - transform_start

    avg_ms = (transform_elapsed / ITERATIONS) * 1000
    collections_built = len(catalog.things)
    items_built = total_datastreams - skipped

    logger.info("TRANSFORMATION SUMMARY")
    logger.info("  Collections built  : %d", collections_built)
    logger.info("  Items built        : %d", items_built)
    logger.info("  Items skipped      : %d  (no phenomenonTime)", skipped)
    logger.info("  Iterations         : %d", ITERATIONS)
    logger.info("  Avg transform time : %.2fms", avg_ms)
    logger.info("  Total (%dx)        : %.1fms", ITERATIONS, avg_ms * ITERATIONS)
    if items_built > 0:
        logger.info("  Per-item avg       : %.4fms", avg_ms / items_built)

    output = {
        "catalog": stac_dict["catalog"],
        "collections": [
            {k: v for k, v in col.items() if k != "_items"}
            for col in stac_dict["collections"]
        ],
    }
    output_path = Path(config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    logger.info("Output saved to : %s", output_path)
    logger.info("Output size     : %.1f KB", output_path.stat().st_size / 1024)


def main() -> None:
    config = BenchmarkConfig()
    asyncio.run(run(config))


if __name__ == "__main__":
    main()