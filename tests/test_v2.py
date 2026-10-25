"""Model/data checks: spectral correctness, group separation and causal inference."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import joblib
import numpy as np
from sklearn.metrics import f1_score

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from satellite_io import reflectance_params
from features import spectral_features, SPECTRAL_NAMES, TEMPORAL_NAMES, scene_valid
from model_v2 import FloodModel, coherent_water
from temporal import TimeSeries
from train_classifier import calibrated_predict


class FeatureTests(unittest.TestCase):
    def test_processing_baseline_offset(self):
        item={"assets":{"B03":{}},"properties":{"s2:processing_baseline":"02.12"}}
        self.assertEqual(reflectance_params(item,"B03"),(.0001,0))
        item["properties"]["s2:processing_baseline"]="05.10"
        self.assertEqual(reflectance_params(item,"B03"),(.0001,-.1))
        item["assets"]["B03"]["raster:bands"]=[{"scale":.0002,"offset":-.05}]
        self.assertEqual(reflectance_params(item,"B03"),(.0002,-.05))

    def test_indices_and_shapes(self):
        cube=np.array([[.1,.3,.1,.1,.02,.01]],dtype="float32")
        x=spectral_features(cube)
        self.assertEqual(x.shape,(1,len(SPECTRAL_NAMES)))
        self.assertAlmostEqual(float(x[0,SPECTRAL_NAMES.index("MNDWI")]),(.3-.02)/(.3+.02),places=5)
        self.assertTrue(np.isfinite(spectral_features(np.zeros((2,6)))).all())

    def test_unknown_not_implicitly_dry(self):
        data={b:np.ones((5,5),dtype="float32")*.1 for b in ["B02","B03","B04","B08","B11","B12"]}
        data["SCL"]=np.full((5,5),4,dtype="uint8");data["SCL"][2,2]=9
        valid=scene_valid(data)
        self.assertFalse(valid[2,2]);self.assertFalse(valid[2,1]);self.assertTrue(valid[0,0])

    def test_components_require_confident_core(self):
        mask=np.ones((5,5),bool);p=np.full((5,5),.6)
        self.assertEqual(int(coherent_water(mask,p).sum()),0)
        p[2,2]=.95
        self.assertEqual(int(coherent_water(mask,p).sum()),25)


class TrainedModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=FloodModel()
        cls.ts=TimeSeries()

    def test_disjoint_event_partitions(self):
        p=self.model.classifier_report["partitions"]
        keys=["train_events","calibration_events","selection_events","untouched_test_events"]
        for i,k in enumerate(keys):
            for other in keys[i+1:]:self.assertFalse(set(p[k])&set(p[other]))
        self.assertEqual(set(p["untouched_test_events"]),set(self.model.classifier_report["test_by_event"]))

    def test_recorded_test_metric_is_reproducible(self):
        bundle=joblib.load(ROOT/"artifacts/water_classifier.joblib")
        with np.load(ROOT/"artifacts/reference_samples.npz") as z:
            test=np.isin(z["event"],self.model.classifier_report["partitions"]["untouched_test_events"])
            X=spectral_features(z["X"][test]);y=z["y"][test]
        p=calibrated_predict(bundle,X)
        actual=f1_score(y,p>=bundle["threshold"])
        self.assertAlmostEqual(actual,self.model.classifier_report["test"]["learned"]["f1"],places=10)

    def test_temporal_training_precedes_validation_and_test(self):
        r=self.model.forecast_report
        self.assertLess(max(p["target"] for p in r["train_pairs"]),min(p["issue"] for p in r["validation_pairs"]))
        self.assertLess(max(p["target"] for p in r["validation_pairs"]),r["heldout_test"]["issue"])
        for pair in r["train_pairs"]+r["validation_pairs"]:
            self.assertTrue(all(d<pair["issue"] for d in pair["history_dates"]))

    def test_context_never_reads_future(self):
        ts=self.ts;read=[];original=ts.observation
        def guarded(date):
            self.assertLessEqual(date,"2024-05-06");read.append(date);return original(date)
        with patch.object(ts,"observation",side_effect=guarded):
            c=ts.context("2024-05-06",15)
        self.assertTrue(read);self.assertEqual(c["X"].shape[-1],len(TEMPORAL_NAMES))
        self.assertLess(max(c["history_dates"]),"2024-05-06")

    def test_snapshot_matches_causal_features(self):
        c=self.ts.context("2024-05-06",15)
        np.testing.assert_allclose(c["normal"],self.model.snapshot["normal_p"],equal_nan=True)
        np.testing.assert_array_equal(c["count"],self.model.snapshot["history_count"])

    def test_active_forecast_chosen_on_validation(self):
        r=self.model.forecast_report
        winner="learned" if r["validation"]["learned"]["f1"]>r["validation"]["persistence"]["f1"] else "persistence"
        self.assertEqual(winner,r["validation_selected_deployment"])
        if not r["release_gate"]["passed"]:self.assertEqual(r["deployment"],"persistence")

    def test_observation_analysis_works_without_future(self):
        m=self.model;a=m.analyze();future=m.scenes.pop("future")
        try:
            m.analyze.cache_clear();b=m.analyze()
            self.assertEqual(a["summary"],b["summary"])
            self.assertEqual(a["sites"],b["sites"])
        finally:m.scenes["future"]=future

    def test_site_outputs_and_unknown_coverage(self):
        a=self.model.analyze()
        self.assertGreater(a["summary"]["history_scenes"],1)
        for row in a["sites"]:
            for key in ["forecast_fraction","uncertain_fraction"]:
                if row[key] is not None:self.assertTrue(0<=row[key]<=1)
            if row["coverage"]<.8:self.assertIsNone(row["forecast_fraction"])

    def test_probability_cache_provenance(self):
        sha=hashlib.sha256((ROOT/"artifacts/water_classifier.joblib").read_bytes()).hexdigest()
        for date in ["2024-04-21","2024-05-06","2024-05-21"]:
            with np.load(ROOT/f"data/v2/probabilities/{date}.npz") as z:self.assertEqual(str(z["model_sha256"]),sha)

    def test_all_new_layers_are_valid_images(self):
        for kind in ["forecast","probability","uncertainty","legacy","error"]:
            self.assertTrue(self.model.png(kind).startswith(b"\x89PNG"))


if __name__=="__main__":unittest.main()
