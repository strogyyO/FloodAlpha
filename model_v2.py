"""Learned water classification and causal forecasting; model.py is the V1 baseline."""
from functools import lru_cache
import io
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage
from model import FloodModel as LegacyFloodModel, binary_scores, clean_components
from features import BANDS, scene_valid, spectral_features

ROOT=Path(__file__).resolve().parent
ART=ROOT/"artifacts"
try: DEFAULT_THRESHOLD=float(json.loads((ART/"classifier_report.json").read_text())["decision_threshold"])
except FileNotFoundError: DEFAULT_THRESHOLD=.5
DEFAULT_DELTA=.2


def coherent_water(candidate,p,minimum=4,seed=.8):
    labels,_=ndimage.label(candidate)
    sizes=np.bincount(labels.ravel())
    cores=np.bincount(labels.ravel(),weights=(p>=seed).ravel(),minlength=len(sizes))
    keep=(sizes>=minimum)&(cores>0);keep[0]=False
    return keep[labels]


class FloodModel(LegacyFloodModel):
    def __init__(self):
        if not (ART/"forecast_snapshot.npz").exists():
            raise FileNotFoundError("V2-Modelle fehlen. Siehe README_V2.md für Aufbereitung und Training.")
        super().__init__();self.legacy_scenes=self.scenes.copy()
        self.classifier_report=json.loads((ART/"classifier_report.json").read_text())
        self.forecast_report=json.loads((ART/"forecast_report.json").read_text())
        self.reference_manifest=json.loads((ART/"reference_manifest.json").read_text())
        with np.load(ART/"forecast_snapshot.npz") as z:self.snapshot={k:z[k] for k in z.files}
        self.history_dates=self.forecast_report["issue_history_dates"]
        for role,date in [("before","2024-04-21"),("event","2024-05-06"),("future","2024-05-21")]:
            with np.load(ROOT/f"data/v2/series/{date}.npz") as z:data={k:z[k] for k in z.files}
            with np.load(ROOT/f"data/v2/probabilities/{date}.npz") as z:p=z["p"]
            features=spectral_features(np.stack([data[b] for b in BANDS],axis=-1))
            self.scenes[role]={"bands":data,"valid":scene_valid(data),"index":features[:,:,7].copy(),"probability":p}

    @lru_cache(maxsize=16)
    def masks(self,threshold=DEFAULT_THRESHOLD,delta=DEFAULT_DELTA):
        p=self.scenes["event"]["probability"];normal=self.snapshot["normal_p"]
        valid=self.scenes["event"]["valid"]&(self.snapshot["history_count"]>=2)&np.isfinite(normal)
        reference=normal>=DEFAULT_THRESHOLD
        candidate=valid&~reference&(p>=threshold)&((p-normal)>delta)
        return coherent_water(candidate,np.nan_to_num(p),seed=max(.8,threshold)),reference,valid

    def forecast_mask(self,threshold=DEFAULT_THRESHOLD,delta=DEFAULT_DELTA):
        current,reference,valid=self.masks(threshold,delta)
        if self.forecast_report["deployment"]=="persistence":return current
        return valid&~reference&(self.snapshot["forecast_p"]>=self.forecast_report["threshold"])

    @lru_cache(maxsize=16)
    def analyze(self,threshold=DEFAULT_THRESHOLD,delta=DEFAULT_DELTA,radius=500):
        base=super().analyze(threshold,delta,radius)
        result={**base,"sites":[dict(s) for s in base["sites"]],"summary":dict(base["summary"])}
        _,_,valid=self.masks(threshold,delta);forecast=self.forecast_mask(threshold,delta)
        p=self.scenes["event"]["probability"];uncertain=valid&(p>.2)&(p<.8)
        geometries={s["id"]:s["geometry"] for s in self.sites}
        for row in result["sites"]:
            mask=self.geometry_mask(geometries[row["id"]]);den=int((mask&valid).sum())
            f=float((mask&forecast).sum()/den) if den and row["coverage"]>=.8 else None
            u=float((mask&uncertain).sum()/den) if den else None
            row["forecast_fraction"]=round(f,4) if f is not None else None
            row["uncertain_fraction"]=round(u,4) if u is not None else None
            row["forecast"]=(f"Am 21. Mai sind {f*100:.1f} % der auswertbaren Fläche als Wasser prognostiziert" if f is not None else "Zu wenig belastbare Beobachtungen")
        result["summary"].update({"forecast_km2":round(float(forecast.sum())*.0004,2),"uncertain_percent":round(float(uncertain.sum()/max(valid.sum(),1))*100,1),"history_scenes":len(self.history_dates)})
        result["model_version"]="2.0"
        result["forecast_method"]="Gelernte zeitliche Wasserprognose" if self.forecast_report["deployment"]=="learned" else "Persistenz: Zeitkandidat nicht freigegeben"
        result["model_info"]=self.model_info()
        return result

    def model_info(self):
        r=self.classifier_report
        return {"version":"2.0","classifier":r["selected_model"],"reference_chips":self.reference_manifest["downloaded_chips"],
                "reference_pixels":sum(c["sample_pixels"] for c in self.reference_manifest["chips"]),"test_events":r["partitions"]["untouched_test_events"],
                "classifier_test":r["test"],"classifier_test_by_event":r["test_by_event"],"classifier_selective":r["selective_test"],
                "default_threshold":DEFAULT_THRESHOLD,"default_delta":DEFAULT_DELTA,"history_dates":self.history_dates,
                "forecast_deployment":self.forecast_report["deployment"],"forecast_training_pairs":len(self.forecast_report["train_pairs"]),
                "forecast_validation":self.forecast_report["validation"],"forecast_release_gate":self.forecast_report.get("release_gate"),
                "domain_diagnostics":self.forecast_report.get("domain_diagnostics"),"classification_limitations":r["limitations"]}

    @lru_cache(maxsize=16)
    def evaluate(self,threshold=DEFAULT_THRESHOLD,delta=DEFAULT_DELTA):
        current,reference,valid=self.masks(threshold,delta);future=self.scenes["future"]
        comparison=valid&future["valid"]&~reference
        observed=coherent_water(comparison&(future["probability"]>=DEFAULT_THRESHOLD),np.nan_to_num(future["probability"]),seed=max(.8,DEFAULT_THRESHOLD))
        return {"satellite_persistence":binary_scores(current,observed,comparison),"active_forecast":binary_scores(self.forecast_mask(threshold,delta),observed,comparison),
                "rejected_candidate":binary_scores(self.snapshot["learned_p"]>=self.forecast_report["threshold"],observed,comparison),
                "no_new_water_baseline":binary_scores(np.zeros(self.shape,bool),observed,comparison),"coverage_percent":round(float(comparison.mean()*100),1),
                "deployment":self.forecast_report["deployment"],"temporal_holdout_report":self.forecast_report["heldout_test"],
                "additional_temporal_test":self.forecast_report.get("additional_temporal_test"),"release_gate":self.forecast_report.get("release_gate"),
                "target":"Spätere Wasserkarten eines eingefrorenen Klassifikators; Proxy-Referenz",
                "limitations":"Klassifikation: zurückgehaltene Länderereignisse. Zeitliche Prognose: Proxy-Wasserkarten statt Feldmessungen, ein Testereignis. Keine bestätigten Betriebsausfälle oder Tradingvorteile."}

    @lru_cache(maxsize=36)
    def png(self,kind,threshold=DEFAULT_THRESHOLD,delta=DEFAULT_DELTA):
        if kind in ["before","event","future"]:return super().png(kind,threshold,delta)
        current,reference,valid=self.masks(threshold,delta);p=self.scenes["event"]["probability"]
        arr=np.zeros((*self.shape,4),dtype="uint8")
        if kind=="flood":arr[current]=[56,215,255,175]
        elif kind=="unknown":arr[~valid]=[160,167,188,145]
        elif kind=="uncertainty":arr[valid&(p>.2)&(p<.8)]=[255,190,65,155]
        elif kind=="probability":
            arr[:,:,0]=(255*(1-np.nan_to_num(p))).astype("uint8");arr[:,:,1]=(200*np.nan_to_num(p)).astype("uint8")
            arr[:,:,2]=(255*np.nan_to_num(p)).astype("uint8");arr[:,:,3]=np.where(valid,160,0)
        elif kind=="forecast":arr[self.forecast_mask(threshold,delta)]=[180,128,255,175]
        elif kind=="error":
            f=self.scenes["future"];ok=valid&f["valid"]&~reference
            target=coherent_water(ok&(f["probability"]>=DEFAULT_THRESHOLD),np.nan_to_num(f["probability"]),seed=max(.8,DEFAULT_THRESHOLD))
            pred=self.forecast_mask(threshold,delta)
            arr[ok&pred&target]=[49,225,158,170];arr[ok&pred&~target]=[255,176,64,190];arr[ok&~pred&target]=[255,79,110,190]
        elif kind=="legacy":
            b,e=self.legacy_scenes["before"],self.legacy_scenes["event"]
            old=clean_components(b["valid"]&e["valid"]&(b["index"]<=.15)&(e["index"]>.15)&(e["index"]-b["index"]>.18))
            arr[old]=[255,150,85,170]
        else:raise ValueError("Unknown layer")
        s=io.BytesIO();Image.fromarray(arr).save(s,format="PNG",optimize=True);return s.getvalue()
