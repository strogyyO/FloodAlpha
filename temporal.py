"""Causal historical context. No future frames are interpolated into inputs."""
from __future__ import annotations
from datetime import datetime
import json
import hashlib
from pathlib import Path
import warnings
import joblib
import numpy as np
from features import BANDS, scene_valid, spectral_features, temporal_features
from train_classifier import calibrated_predict

ROOT=Path(__file__).resolve().parent
SERIES=ROOT/"data/v2/series"
PROBS=ROOT/"data/v2/probabilities"


class TimeSeries:
    def __init__(self):
        self.manifest=json.loads((ROOT/"data/v2/series_manifest.json").read_text())
        self.records=self.manifest["records"]
        self.dates=[r["date"] for r in self.records]
        self.water=joblib.load(ROOT/"artifacts/water_classifier.joblib")
        self.classifier_sha256=hashlib.sha256((ROOT/"artifacts/water_classifier.joblib").read_bytes()).hexdigest()
        self.threshold=self.water["threshold"]
        PROBS.mkdir(exist_ok=True)

    def prepare_probabilities(self):
        for date in self.dates:
            path=PROBS/(date+".npz")
            if path.exists():
                with np.load(path) as cached:
                    if "model_sha256" in cached and str(cached["model_sha256"])==self.classifier_sha256:continue
            data=self.raw(date)
            valid=scene_valid(data)
            cube=np.stack([data[b] for b in BANDS],axis=-1)
            p=np.full(valid.shape,np.nan,dtype="float32")
            features=spectral_features(cube[valid])
            p[valid]=calibrated_predict(self.water,features)
            np.savez_compressed(path,p=p,valid=valid,model_sha256=self.classifier_sha256)
            print("PROBABILITY",date,"clear",round(valid.mean(),3),flush=True)

    def raw(self,date):
        with np.load(SERIES/(date+".npz")) as z:return {k:z[k] for k in z.files}

    def observation(self,date):
        with np.load(PROBS/(date+".npz")) as z:return z["p"],z["valid"]

    def context(self, date, lead=15):
        now=datetime.fromisoformat(date)
        # This filter is the data boundary: only dates up to issue time may be read.
        past=[d for d in self.dates if d<=date and (now-datetime.fromisoformat(d)).days<=150]
        if date not in past:raise ValueError("Issue date absent")
        current,valid=self.observation(date)
        historical=[d for d in past if 21<=(now-datetime.fromisoformat(d)).days<=150]
        fallback=not bool(historical)
        if not historical:historical=[d for d in past if d<date][-3:]
        if not historical:
            normal=np.full(current.shape,.5,dtype="float32");frequency=normal.copy();count=np.zeros(current.shape,dtype="uint8")
        else:
            stack=np.stack([self.observation(d)[0] for d in historical])
            count=np.isfinite(stack).sum(axis=0).astype("uint8")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore",RuntimeWarning)
                normal=np.nanmedian(stack,axis=0).astype("float32")
            frequency=np.divide(np.nansum(np.where(np.isfinite(stack),stack>=self.threshold,np.nan),axis=0),count,
                                out=np.full(current.shape,np.nan,dtype="float32"),where=count>0)
        previous_dates=[d for d in past if d<date]
        if previous_dates:
            prevdate=previous_dates[-1];previous=self.observation(prevdate)[0]
            age=(now-datetime.fromisoformat(prevdate)).days
        else:previous=current.copy();age=1
        enough=valid & (count>=2)
        X=temporal_features(current,previous,normal,frequency,enough,lead,age,now.timetuple().tm_yday)
        return {"X":X,"p":current,"valid":enough,"normal":normal,"frequency":frequency,"count":count,
                "history_dates":historical,"previous_date":previous_dates[-1] if previous_dates else None,
                "baseline_fallback":fallback,"latest_input_date":date,"lead_days":lead}
