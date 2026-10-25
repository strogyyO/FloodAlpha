"""Download real, spatially aligned Sentinel-2 crops and historical OSM data.

Only the AOI windows of the cloud-optimized GeoTIFFs are transferred.
No API key is required. Run: python fetch_data.py
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlsplit

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds
import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
BBOX = [-51.30, -29.91, -51.07, -29.74]
CRS = "EPSG:32722"
DATES = {"before": "2024-04-21", "event": "2024-05-06", "future": "2024-05-21"}
BANDS = ["B02", "B03", "B04", "B11", "SCL"]
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


def get_json(url, **kwargs):
    for attempt in range(5):
        r = requests.get(url, timeout=120, headers={"User-Agent": "FloodAlphaHackathon/1.0"}, **kwargs)
        if r.status_code in [429, 500, 502, 503, 504] and attempt < 4:
            time.sleep(min(2**attempt * 2, 15))
            continue
        r.raise_for_status()
        return r.json()


def grid():
    west, south, east, north = transform_bounds("EPSG:4326", CRS, *BBOX)
    west, south = np.floor([west / 20, south / 20]) * 20
    east, north = np.ceil([east / 20, north / 20]) * 20
    return from_origin(west, north, 20, 20), (round((north-south)/20), round((east-west)/20))


def read_band(item, band, transform, shape, token):
    asset = item["assets"][band]
    href = asset["href"] + "?" + token
    out = np.zeros(shape, dtype="uint16")
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_MAX_RETRY=3):
        with rasterio.open(href) as src:
            bounds = rasterio.transform.array_bounds(*shape, transform)
            bounds = transform_bounds(CRS, src.crs, *bounds)
            window = from_bounds(*bounds, src.transform).round_offsets().round_lengths()
            crop = src.read(1, window=window, boundless=True, fill_value=0)
            reproject(crop, out, src_transform=src.window_transform(window), src_crs=src.crs,
                      dst_transform=transform, dst_crs=CRS, src_nodata=0, dst_nodata=0,
                      resampling=Resampling.nearest if band == "SCL" else Resampling.bilinear)
    print(f"  {band}: {out.shape}", flush=True)
    # S2 L2A processing baseline >=04.00 uses additive offsets. Use STAC metadata.
    info = asset.get("raster:bands", [{}])[0]
    return band, out, {"scale": info.get("scale", .0001), "offset": info.get("offset", -.1)}


def fetch_osm():
    west, south, east, north = BBOX
    bbox = f"({south},{west},{north},{east})"
    query = ('[out:json][timeout:100][date:"2024-04-24T00:00:00Z"];('
             f'way["landuse"="industrial"]{bbox};'
             f'nwr["man_made"="works"]{bbox};'
             f'way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]{bbox};'
             ');out geom;')
    errors = []
    for endpoint in ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter"]:
        try:
            d = get_json(endpoint, params={"data": query})
            if not d.get("elements"):
                raise ValueError("No historical OSM objects returned")
            (DATA / "osm.json").write_text(json.dumps(d), encoding="utf-8")
            return {"url": endpoint, "query": query, "snapshot": "2024-04-24T00:00:00Z", "elements": len(d["elements"])}
        except Exception as exc:
            errors.append(str(exc))
    raise RuntimeError("Historical OSM download failed: " + "; ".join(errors))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    DATA.mkdir(exist_ok=True)
    if (DATA / "manifest.json").exists() and not args.force:
        print("Bundled data already present. Use --force to download again.")
        return
    transform, shape = grid()
    manifest = {"bbox": BBOX, "crs": CRS, "transform": list(transform)[:6], "shape": shape,
                "downloaded_at": datetime.now(timezone.utc).isoformat(), "scenes": {}}
    token_cache = {}
    for role, date in DATES.items():
        print(f"Sentinel-2 {role}: {date}", flush=True)
        result = get_json(STAC + "/search", params={"collections": "sentinel-2-l2a", "bbox": ",".join(map(str, BBOX)),
                          "datetime": f"{date}T00:00:00Z/{date}T23:59:59Z", "limit": 100})
        candidates = [x for x in result["features"] if "T22JDN" in x["id"]]
        if not candidates:
            raise RuntimeError(f"No scene for {date}; never substitute synthetic data")
        item = min(candidates, key=lambda x: x["properties"].get("eo:cloud_cover", 100))
        (DATA / f"stac_{role}.json").write_text(json.dumps(item, indent=2), encoding="utf-8")
        if (DATA / f"{role}.npz").exists() and not args.force:
            values = [(b, None, {"scale": item["assets"][b].get("raster:bands", [{}])[0].get("scale", .0001),
                                "offset": item["assets"][b].get("raster:bands", [{}])[0].get("offset", -.1)}) for b in BANDS]
            print("  Reusing downloaded crop.", flush=True)
        else:
            parts = urlsplit(item["assets"]["B03"]["href"])
            account = parts.hostname.split(".")[0]
            container = parts.path.split("/")[1]
            key = (account, container)
            if key not in token_cache:
                token_cache[key] = get_json(f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{account}/{container}")["token"]
            with ThreadPoolExecutor(max_workers=3) as pool:
                values = list(pool.map(lambda b: read_band(item, b, transform, shape, token_cache[key]), BANDS))
            np.savez_compressed(DATA / f"{role}.npz", **{b: a for b, a, _ in values})
        manifest["scenes"][role] = {"id": item["id"], "datetime": item["properties"]["datetime"],
            "created": item["properties"].get("created"), "updated": item["properties"].get("updated"),
            "cloud_cover_tile_percent": item["properties"].get("eo:cloud_cover"),
            "url": f"{STAC}/collections/sentinel-2-l2a/items/{item['id']}",
            "bands": {b: meta for b, _, meta in values}}
    print("Downloading historical OpenStreetMap geometry …", flush=True)
    manifest["osm"] = fetch_osm()
    from market import fetch_market
    print("Downloading real AGCO/SPY market data …", flush=True)
    fetch_market()
    manifest["checksums_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.iterdir() if p.suffix in [".npz", ".json"] and p.name != "manifest.json"}
    (DATA / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("All real data downloaded and checksummed.", flush=True)


if __name__ == "__main__":
    main()
