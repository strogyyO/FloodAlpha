"""Shared Sentinel-2 L2A I/O with baseline-aware reflectance correction."""
from __future__ import annotations
import threading
import time
from urllib.parse import urlsplit
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
from rasterio.warp import reproject, transform_bounds
import requests

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
BANDS = ["B02", "B03", "B04", "B08", "B11", "B12"]
_tokens, _lock = {}, threading.Lock()


def get_json(url, **kwargs):
    for attempt in range(6):
        try:
            r = requests.get(url, timeout=100, headers={"User-Agent": "FloodAlphaResearch/2.0"}, **kwargs)
            if r.status_code in [429, 500, 502, 503, 504] and attempt < 5:
                time.sleep(min(2**attempt, 12)); continue
            r.raise_for_status()
            return r.json()
        except requests.ConnectionError:
            if attempt == 5: raise
            time.sleep(2)


def signed(href):
    parts = urlsplit(href)
    key = (parts.hostname.split(".")[0], parts.path.split("/")[1])
    with _lock:
        if key not in _tokens:
            _tokens[key] = get_json(f"https://planetarycomputer.microsoft.com/api/sas/v1/token/{key[0]}/{key[1]}")["token"]
    return href + "?" + _tokens[key]


def reflectance_params(item, band):
    rb = item["assets"][band].get("raster:bands", [{}])[0]
    # Old archive assets often omit raster:bands. Offsets started with PB 04.00.
    pb = float(item["properties"].get("s2:processing_baseline", "0"))
    return rb.get("scale", .0001), rb.get("offset", -.1 if pb >= 4 else 0.)


def read_scene(item, transform, shape, crs, bands=None):
    bands = bands or BANDS + ["SCL"]
    bounds = rasterio.transform.array_bounds(*shape, transform)
    result = {}
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_MAX_RETRY=3, GDAL_HTTP_TIMEOUT=60):
        for b in bands:
            asset = item["assets"][b]
            with rasterio.open(signed(asset["href"])) as src:
                sb = transform_bounds(crs, src.crs, *bounds, densify_pts=21)
                win = from_bounds(*sb, src.transform).round_offsets().round_lengths()
                raw = src.read(1, window=win, boundless=True, fill_value=0)
                out = np.zeros(shape, "float32")
                reproject(raw, out, src_transform=src.window_transform(win), src_crs=src.crs,
                          dst_transform=transform, dst_crs=crs, src_nodata=0, dst_nodata=0,
                          resampling=Resampling.nearest if b == "SCL" else Resampling.bilinear)
            if b == "SCL":
                result[b] = out.astype("uint8")
            else:
                good = out > 0
                scale, offset = reflectance_params(item, b)
                out = out*scale+offset
                out[~good] = np.nan
                result[b] = out.astype("float32")
    return result


def search(bbox, start, end=None):
    end = end or start
    params = {"collections": "sentinel-2-l2a", "bbox": ",".join(map(str, bbox)),
              "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z", "limit": 100}
    data = get_json(STAC + "/search", params=params)
    return data.get("features", [])
