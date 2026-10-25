"""Transparent flood detection, a forward persistence forecast, and site exposure.

No fitted probabilities, invented supplier links, or fabricated investment returns.
"""
from __future__ import annotations
from functools import lru_cache
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image
import rasterio
from rasterio.features import rasterize
from rasterio.transform import Affine
from rasterio.warp import transform as project
from scipy import ndimage
from shapely.geometry import Polygon, LineString, Point, mapping, box
from shapely import transform as shapely_transform

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def transform_geometry(function, geometry):
    return shapely_transform(geometry, lambda coords: np.column_stack(function(coords[:, 0], coords[:, 1])))


def clean_components(mask, minimum=25):
    labels, _ = ndimage.label(mask)
    counts = np.bincount(labels.ravel())
    keep = counts >= minimum
    keep[0] = False
    return keep[labels]


def binary_scores(prediction, target, valid):
    p, t = prediction[valid], target[valid]
    tp, fp, fn, tn = [int(np.count_nonzero(x)) for x in (p&t, p&~t, ~p&t, ~p&~t)]
    ratio = lambda a, b: round(a/b, 4) if b else None
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": ratio(tp, tp+fp), "recall": ratio(tp, tp+fn),
            "f1": ratio(2*tp, 2*tp+fp+fn), "iou": ratio(tp, tp+fp+fn),
            "accuracy": ratio(tp+tn, len(p)), "pixels": len(p)}


class FloodModel:
    def __init__(self):
        if not (DATA / "manifest.json").exists():
            raise FileNotFoundError("Daten fehlen. Zuerst: python fetch_data.py")
        self.manifest = json.loads((DATA / "manifest.json").read_text())
        self.transform = Affine(*self.manifest["transform"])
        self.shape = tuple(self.manifest["shape"])
        self.crs = self.manifest["crs"]
        self.scenes = {}
        for role in ("before", "event", "future"):
            with np.load(DATA / f"{role}.npz") as z:
                bands = {}
                for band in ("B02", "B03", "B04", "B11"):
                    meta = self.manifest["scenes"][role]["bands"][band]
                    bands[band] = z[band].astype("float32")*meta["scale"]+meta["offset"]
                scl = z["SCL"]
                # SCL 2/3 = dark/shadow, 8/9/10 = cloud/cirrus, 11 = snow.
                bad = np.isin(scl, [0, 1, 2, 3, 8, 9, 10, 11])
                valid = ~ndimage.binary_dilation(bad, iterations=2)
                valid &= (z["B03"] > 0) & (z["B11"] > 0)
                denom = bands["B03"]+bands["B11"]
                valid &= (bands["B03"] >= 0) & (bands["B11"] >= 0) & (denom > .001)
                index = np.divide(bands["B03"]-bands["B11"], denom, out=np.zeros(self.shape, dtype="float32"), where=denom>.001)
                self.scenes[role] = {"bands": bands, "valid": valid, "index": index}
        self.sites, self.roads = self.load_osm()

    def load_osm(self):
        osm = json.loads((DATA / "osm.json").read_text())
        left, bottom, right, top = rasterio.transform.array_bounds(*self.shape, self.transform)
        aoi = box(left, bottom, right, top)
        def to_utm(x, y, z=None):
            return project("EPSG:4326", self.crs, x, y)
        sites, roads = [], []
        for e in osm["elements"]:
            tags = e.get("tags", {})
            coords = [(p["lon"], p["lat"]) for p in e.get("geometry", [])]
            if tags.get("highway") and len(coords) >= 2:
                geom = LineString(coords)
                kind = "road"
            elif tags.get("man_made") == "works" or tags.get("landuse") == "industrial":
                kind = "site"
                if len(coords) >= 4 and coords[0] == coords[-1]:
                    geom = Polygon(coords)
                    if not geom.is_valid:
                        geom = geom.buffer(0)
                elif e["type"] == "node":
                    geom = Point(e["lon"], e["lat"])
                else:
                    continue
            else:
                continue
            if geom.is_empty:
                continue
            geom = transform_geometry(to_utm, geom)
            if not geom.intersects(aoi):
                continue
            # Nodes provide only an approximate location, never a factory footprint.
            node = geom.geom_type == "Point"
            if node:
                geom = geom.buffer(60)
            geom = geom.intersection(aoi)
            if geom.is_empty:
                continue
            id_ = f"{e['type']}/{e['id']}"
            record = {"id": id_, "name": tags.get("name") or tags.get("operator") or ("Industriefläche " + str(e["id"])),
                      "kind": kind, "tags": tags, "geometry": geom, "approximate": node,
                      "osm_url": "https://www.openstreetmap.org/"+id_}
            (roads if kind == "road" else sites).append(record)
        # Avoid double counting works inside generic industrial landuse polygons.
        works = [s for s in sites if s["tags"].get("man_made") == "works"]
        sites = [s for s in sites if s in works or not any(s["geometry"].covers(w["geometry"].representative_point()) for w in works)]
        if not sites:
            raise ValueError("No industrial sites within the downloaded AOI")
        return sites, roads

    def geometry_mask(self, geometry):
        return rasterize([(geometry, 1)], out_shape=self.shape, transform=self.transform, fill=0, all_touched=True, dtype="uint8").astype(bool)

    def pixels(self, geom):
        inv = ~self.transform
        def convert(x, y, z=None):
            return inv.a*np.asarray(x)+inv.c, inv.e*np.asarray(y)+inv.f
        return mapping(transform_geometry(convert, geom))

    @lru_cache(maxsize=24)
    def masks(self, threshold=.15, delta=.18):
        b, e = self.scenes["before"], self.scenes["event"]
        valid = b["valid"] & e["valid"]
        permanent = (b["index"] > threshold) & b["valid"]
        change = (e["index"]-b["index"] > delta)
        flood = valid & ~permanent & (e["index"] > threshold) & change
        flood = clean_components(flood)
        return flood, permanent, valid

    @lru_cache(maxsize=24)
    def analyze(self, threshold=.15, delta=.18, radius=500):
        flood, permanent, valid = self.masks(threshold, delta)
        # Forecast at t0: newly flooded cells remain wet at t0+15d (persistence).
        # It is deliberately frozen here; the future scene is not read in this method.
        predictions = flood.copy()
        road_mask = np.zeros(self.shape, dtype=bool)
        road_outputs = []
        for r in self.roads:
            # Bridge decks may remain usable above detected water: do not close them.
            if r["tags"].get("bridge", "no") != "no" or r["tags"].get("tunnel", "no") != "no":
                continue
            mask = self.geometry_mask(r["geometry"].buffer(10))
            road_mask |= mask
            n = int(np.count_nonzero(mask & valid))
            fraction = float(np.count_nonzero(mask & flood)/n) if n else 0
            if fraction > .05:
                road_outputs.append({"id": r["id"], "name": r["tags"].get("name", r["tags"]["highway"]),
                                     "wet_fraction": round(fraction, 3), "geometry": self.pixels(r["geometry"])})
        road_wet = road_mask & flood
        rows = []
        for s in self.sites:
            footprint = self.geometry_mask(s["geometry"])
            near = self.geometry_mask(s["geometry"].buffer(radius))
            n = int(np.count_nonzero(footprint & valid))
            total = int(np.count_nonzero(footprint))
            frac = float(np.count_nonzero(footprint & flood)/n) if n else 0
            near_road = near & road_mask & valid
            rn = int(np.count_nonzero(near_road))
            road_frac = float(np.count_nonzero(near & road_wet)/rn) if rn else None
            coverage = n/max(total, 1)
            enough = coverage >= .8
            # Ranking index only: these coefficients are not calibrated probabilities.
            score = round(100*(.7*frac+.3*(road_frac or 0)), 1) if enough else None
            signal = "Datenlücke" if not enough else ("Prüfen: direkt exponiert" if frac >= .05 else
                     "Prüfen: Umfeld exponiert" if (road_frac or 0) >= .10 else "Kein Bildsignal")
            gx, gy = s["geometry"].representative_point().coords[0]
            inverse = ~self.transform
            cx, cy = inverse.a*gx+inverse.c, inverse.e*gy+inverse.f
            rows.append({"id": s["id"], "name": s["name"], "osm_url": s["osm_url"], "tags": s["tags"],
                "approximate": s["approximate"], "direct_fraction": round(frac, 4) if enough else None,
                "road_fraction": round(road_frac, 4) if road_frac is not None else None,
                "coverage": round(coverage, 4), "score": score, "signal": signal,
                "forecast": "Exposition könnte bis 21. Mai fortbestehen" if enough and (frac >= .05 or (road_frac or 0) >= .10) else "Kein belastbares positives Risikosignal",
                "geometry": self.pixels(s["geometry"]), "center": [cx, cy]})
        rows.sort(key=lambda s: (s["score"] is not None, s["score"] or 0), reverse=True)
        area = lambda mask: round(float(np.count_nonzero(mask))*.0004, 2)
        return {"sites": rows, "roads": road_outputs,
                "summary": {"new_water_km2": area(flood), "valid_percent": round(valid.mean()*100, 1),
                            "sites": len(rows), "direct": sum((r["direct_fraction"] or 0) >= .05 for r in rows),
                            "indirect": sum((r["direct_fraction"] or 0) < .05 and (r["road_fraction"] or 0) >= .10 for r in rows),
                            "road_segments": len(road_outputs), "forecast_km2": area(predictions)},
                "parameters": {"threshold": threshold, "delta": delta, "radius": radius},
                "shape": self.shape, "manifest": self.public_manifest(),
                "forecast_method": "15-Tage-Persistenz: neue Wasserflächen vom 6. Mai bleiben am 21. Mai nass. Keine trainierte Ausfall- oder Kursprognose."}

    def public_manifest(self):
        return {k: self.manifest[k] for k in ["bbox", "crs", "shape", "scenes", "osm", "downloaded_at"]}

    @lru_cache(maxsize=24)
    def evaluate(self, threshold=.15, delta=.18):
        flood, permanent, valid = self.masks(threshold, delta)
        future = self.scenes["future"]
        # Future is accessed ONLY for evaluation; never for current detection or ranking.
        comparison = valid & future["valid"] & ~permanent
        observed = future["index"] > threshold
        wet = clean_components(observed & future["valid"])
        return {"satellite_persistence": binary_scores(flood, wet, comparison),
                "no_new_water_baseline": binary_scores(np.zeros(self.shape, bool), wet, comparison),
                "coverage_percent": round(float(comparison.mean())*100, 1),
                "target": "Wasser am 21. Mai auf am 21. April nicht als Wasser klassifizierten Flächen",
                "limitations": "Gleicher Sensor und gleicher Wasserindex als Ziel: keine unabhängige Ground Truth. Ein Ereignis, keine Aussage über allgemeine Prognosegüte. Kein Vergleich mit einem starken Wetter-/Pegelmodell."}

    @lru_cache(maxsize=40)
    def png(self, kind, threshold=.15, delta=.18):
        if kind in ["before", "event", "future"]:
            scene = self.scenes[kind]
            rgb = np.stack([scene["bands"][b] for b in ["B04", "B03", "B02"]], axis=-1)
            rgb = (np.clip(np.nan_to_num(rgb, nan=0.0)/0.30, 0, 1)**.8*255).astype("uint8")
            rgb[~scene["valid"]] = [48, 53, 64]
            img = Image.fromarray(rgb)
        else:
            flood, permanent, valid = self.masks(threshold, delta)
            arr = np.zeros((*self.shape, 4), dtype="uint8")
            if kind == "flood":
                arr[flood] = [56, 215, 255, 175]
            elif kind == "unknown":
                arr[~valid] = [160, 167, 188, 145]
            elif kind == "error":
                f = self.scenes["future"]
                eligible = valid & f["valid"] & ~permanent
                target = clean_components((f["index"] > threshold) & f["valid"])
                arr[eligible & flood & target] = [49, 225, 158, 170]
                arr[eligible & flood & ~target] = [255, 176, 64, 190]
                arr[eligible & ~flood & target] = [255, 79, 110, 190]
            else:
                raise ValueError("Unknown layer")
            img = Image.fromarray(arr)
        stream = io.BytesIO()
        img.save(stream, format="PNG", optimize=True)
        return stream.getvalue()
