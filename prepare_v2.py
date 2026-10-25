"""Reproducible acquisition of real reference samples and historical time series.

python prepare_v2.py benchmark --chips-per-event 8
python prepare_v2.py series
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import traceback
import numpy as np
import rasterio
from rasterio.transform import Affine
from shapely.geometry import shape, box
import requests
from satellite_io import read_scene, search, get_json, BANDS

ROOT = Path(__file__).resolve().parent
ART = ROOT / "artifacts"
WORK = ROOT / "data" / "v2"
BUCKET = "https://storage.googleapis.com/sen1floods11/v1.1/"


def seed_for(name):
    return int(hashlib.sha256(name.encode()).hexdigest()[:8], 16)


def prepare_benchmark(chips_per_event):
    ART.mkdir(exist_ok=True); WORK.mkdir(parents=True, exist_ok=True)
    meta = get_json(BUCKET+"Sen1Floods11_Metadata.geojson")
    dates = {f["properties"]["location"]:f["properties"]["s2_date"].replace("/", "-") for f in meta["features"]}
    dates["Mekong"] = dates["Cambodia"]
    names = set()
    for split in ["train", "valid", "test", "bolivia"]:
        r = requests.get(BUCKET+f"splits/flood_handlabeled/flood_{split}_data.csv", timeout=60);r.raise_for_status()
        names.update(line.split(",")[1].strip().removesuffix("_LabelHand.tif") for line in r.text.splitlines() if line.strip())
    selected = []
    for event in sorted(set(n.split("_")[0] for n in names)):
        group = sorted([n for n in names if n.startswith(event+"_")], key=seed_for)
        selected.extend(group[:chips_per_event])
    caches = WORK / "reference_chips";caches.mkdir(exist_ok=True)

    def one(name):
        file = caches/(name+".npz")
        if file.exists():
            return name, "cached"
        event = name.split("_")[0]
        url = BUCKET+f"data/flood_events/HandLabeled/LabelHand/{name}_LabelHand.tif"
        r = requests.get(url, timeout=60);r.raise_for_status()
        with rasterio.MemoryFile(r.content) as mem:
            with mem.open() as ds:
                labels = ds.read(1)
                # Retain only pure 2x2 blocks. Do not train on ambiguous boundary labels.
                blocks = labels.reshape(256,2,256,2).transpose(0,2,1,3).reshape(256,256,4)
                pure = np.all(blocks == blocks[:,:,:1], axis=-1)
                target = np.where(pure, blocks[:,:,0], -1).astype("int8")
                t = ds.transform*Affine.scale(2,2)
                bbox = list(ds.bounds);crs=str(ds.crs)
        items = search(bbox, dates[event])
        if not items:
            raise RuntimeError("No L2A scene on the reference acquisition date")
        center = box(*bbox).centroid
        items.sort(key=lambda f: (not shape(f["geometry"]).covers(center), -shape(f["geometry"]).intersection(box(*bbox)).area))
        data = read_scene(items[0], t, (256,256), crs)
        valid = ~np.isin(data["SCL"], [0,1,3,8,9,10,11]) & (target>=0)
        cube = np.stack([data[b] for b in BANDS], axis=-1)
        valid &= np.isfinite(cube).all(axis=-1) & (cube.min(axis=-1)>-.05) & (cube.max(axis=-1)<1.5)
        idx = np.flatnonzero(valid)
        if len(idx) < 200:
            raise RuntimeError("Fewer than 200 clear independently labelled pixels")
        rng=np.random.default_rng(seed_for(name))
        # Unbiased uniform sample used for calibration/evaluation and weighted fitting.
        idx=rng.choice(idx, min(5000,len(idx)), replace=False)
        metadata={"chip":name,"event":event,"date":dates[event],"label_url":url,"l2a_scene":items[0]["id"],
                  "valid_pixels":int(valid.sum()),"sample_pixels":len(idx),"processing_baseline":items[0]["properties"].get("s2:processing_baseline")}
        np.savez_compressed(file, X=cube.reshape(-1,6)[idx], y=target.ravel()[idx], metadata=json.dumps(metadata))
        return name, f"{len(idx)} points"

    errors=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(one,n):n for n in selected}
        for future in as_completed(futures):
            name=futures[future]
            try: print("REFERENCE", *future.result(), flush=True)
            except Exception as exc:
                errors.append({"chip":name,"error":str(exc)})
                print("REFERENCE SKIP",name,str(exc)[:200],flush=True)
    arrays=[];labels=[];groups=[];chips=[];records=[]
    for name in selected:
        path=caches/(name+".npz")
        if not path.exists():continue
        with np.load(path) as z:
            record=json.loads(str(z["metadata"]));records.append(record)
            arrays.append(z["X"]);labels.append(z["y"])
            groups.extend([record["event"]]*len(z["y"]));chips.extend([name]*len(z["y"]))
    if not arrays:raise RuntimeError("No real reference data downloaded")
    np.savez_compressed(ART/"reference_samples.npz",X=np.concatenate(arrays),y=np.concatenate(labels),event=np.array(groups),chip=np.array(chips))
    report={"source":"Sen1Floods11 hand labels; Sentinel-2 L2A re-acquired from Planetary Computer", "label_caveat":"Expert-edited labels were initialized from an optical index; not independent field measurements.",
            "selection":"Fixed SHA256 ordering, up to requested chip count per event; pure 20m label blocks; uniform pixel samples", "requested_chips":len(selected),"downloaded_chips":len(records),"chips":records,"errors":errors,
            "retrieved_at":datetime.now(timezone.utc).isoformat(),"license":"Publicly downloadable; citation requested. Specific redistribution license not verified.","doi":"10.1109/CVPRW50498.2020.00113"}
    (ART/"reference_manifest.json").write_text(json.dumps(report,indent=2))
    print("Reference samples:",sum(len(y) for y in labels),"from",len(records),"chips",flush=True)


def prepare_series():
    WORK.mkdir(parents=True,exist_ok=True)
    m=json.loads((ROOT/"data/manifest.json").read_text())
    transform=Affine(*m["transform"]);rshape=tuple(m["shape"])
    items=search(m["bbox"],"2023-08-01","2024-06-30")
    # STAC pagination: request each month to stay below 100 scene limit.
    items=[]
    for month in [f"2023-{i:02}" for i in range(1,13)]+[f"2024-{i:02}" for i in range(1,7)]:
        import calendar
        y,mo=map(int,month.split("-"));end=f"{month}-{calendar.monthrange(y,mo)[1]:02}"
        items.extend(search(m["bbox"],month+"-01",end))
    candidates=[f for f in items if "T22JDN" in f["id"]]
    unique={f["properties"]["datetime"][:10]:f for f in candidates if f["properties"].get("eo:cloud_cover",100)<12}
    for role in ["before","event","future"]:
        item=json.loads((ROOT/f"data/stac_{role}.json").read_text());unique[item["properties"]["datetime"][:10]]=item
    # Fixed chronological spacing; no selection using future water outcomes.
    selected=[];last=None
    for date,f in sorted(unique.items()):
        day=datetime.fromisoformat(date)
        if last is None or (day-last).days>=5 or date in ["2024-04-21","2024-05-06","2024-05-21"]:
            selected.append((date,f));last=day
    out=WORK/"series";out.mkdir(exist_ok=True)
    records=[];errors=[]
    def one(pair):
        date,item=pair;p=out/(date+".npz")
        if not p.exists():
            data=read_scene(item,transform,rshape,m["crs"])
            np.savez_compressed(p,**data)
        return {"date":date,"id":item["id"],"datetime":item["properties"]["datetime"],"file":p.name,"cloud_cover_tile":item["properties"].get("eo:cloud_cover")}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures={pool.submit(one,pair):pair[0] for pair in selected}
        for future in as_completed(futures):
            try:
                record=future.result();records.append(record);print("SERIES",record["date"],flush=True)
            except Exception as exc:
                errors.append({"date":futures[future],"error":str(exc)});print("SERIES SKIP",futures[future],str(exc)[:150],flush=True)
    report={"records":sorted(records,key=lambda r:r["date"]),"errors":errors,"selection":"Tile cloud fraction <12%, >=5 days apart; fixed three legacy scenes included", "bands":BANDS,
            "transform":m["transform"],"shape":m["shape"],"crs":m["crs"],"bbox":m["bbox"]}
    (WORK/"series_manifest.json").write_text(json.dumps(report,indent=2))
    print("Downloaded",len(records),"dates",flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("mode",choices=["benchmark","series"]);parser.add_argument("--chips-per-event",type=int,default=8);args=parser.parse_args()
    if args.mode=="benchmark":prepare_benchmark(args.chips_per_event)
    else:prepare_series()
