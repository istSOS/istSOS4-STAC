"""
Minimal FastAPI app for STAC browser testing.

Serves the 5 STAC endpoints needed for a STAC browser to fully navigate the
catalog. Backed directly by the transformer in benchmark_stac.py.

No cache, no DCAT, no auth -- dev/benchmark server only.

Run:
    uvicorn api:app --host 0.0.0.0 --port 8020 --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from benchmark_stac import BenchmarkConfig, fetch_catalog, transform_to_stac

# App state -- loaded once at startup
_catalog_data: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = BenchmarkConfig()
    catalog, _ = await fetch_catalog(config)
    stac_dict, _ = transform_to_stac(catalog, config.stac_root_href)

    _catalog_data["catalog"] = stac_dict["catalog"]
    # key by collection id; keep _items for the /items endpoint
    _catalog_data["collections"] = {
        col["id"]: col for col in stac_dict["collections"]
    }
    yield
    _catalog_data.clear()


app = FastAPI(title="istSOS STAC Connector -- dev server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# STAC endpoints
@app.get("/stac")
def get_root_catalog() -> dict:
    return _catalog_data["catalog"]


@app.get("/stac/collections")
def get_collections() -> dict:
    cols = [
        {k: v for k, v in col.items() if k != "_items"}
        for col in _catalog_data["collections"].values()
    ]
    return {"collections": cols}


@app.get("/stac/collections/{collection_id}")
def get_collection(collection_id: str) -> dict:
    col = _catalog_data["collections"].get(collection_id)
    if col is None:
        raise HTTPException(404, f"Collection '{collection_id}' not found")
    return {k: v for k, v in col.items() if k != "_items"}


@app.get("/stac/collections/{collection_id}/items")
def get_items(collection_id: str) -> dict:
    col = _catalog_data["collections"].get(collection_id)
    if col is None:
        raise HTTPException(404, f"Collection '{collection_id}' not found")
    items = col.get("_items", [])
    return {
        "type": "FeatureCollection",
        "features": items,
        "numberMatched": len(items),
        "numberReturned": len(items),
    }


@app.get("/stac/collections/{collection_id}/items/{item_id}")
def get_item(collection_id: str, item_id: str) -> dict:
    col = _catalog_data["collections"].get(collection_id)
    if col is None:
        raise HTTPException(404, f"Collection '{collection_id}' not found")
    for item in col.get("_items", []):
        if item.get("id") == item_id:
            return item
    raise HTTPException(404, f"Item '{item_id}' not found in '{collection_id}'")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "collections_loaded": len(_catalog_data.get("collections", {})),
    }