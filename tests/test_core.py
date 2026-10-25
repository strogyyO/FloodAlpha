"""Tests against bundled real data plus focused numerical correctness checks."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import FloodModel, binary_scores, clean_components
from app import parameters
import market


class NumericalTests(unittest.TestCase):
    def test_confusion_and_undefined_precision(self):
        a = np.array([[True, True], [False, False]])
        b = np.array([[True, False], [True, False]])
        scores = binary_scores(a, b, np.ones((2, 2), bool))
        self.assertEqual([scores[k] for k in ["tp", "fp", "fn", "tn"]], [1,1,1,1])
        self.assertEqual(scores["f1"], .5)
        self.assertIsNone(binary_scores(a*False, b, np.ones((2,2), bool))["precision"])

    def test_components_do_not_retain_background(self):
        a = np.zeros((20,20), bool)
        a[2:7,2:7] = True
        a[15,15] = True
        self.assertEqual(int(clean_components(a).sum()), 25)

    def test_reject_invalid_parameters(self):
        for q in ["threshold=nan", "radius=0", "delta=hello", "radius=inf"]:
            with self.assertRaises(ValueError):
                parameters(q)


class RealDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = FloodModel()

    def test_integrity(self):
        root = Path(__file__).resolve().parents[1]/"data"
        for name, digest in self.model.manifest["checksums_sha256"].items():
            self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(), digest, name)

    def test_historical_inputs_and_valid_coverage(self):
        m = self.model
        self.assertLess(m.manifest["osm"]["snapshot"], m.manifest["scenes"]["event"]["datetime"])
        self.assertEqual(m.shape, (945,1114))
        self.assertGreater(m.scenes["event"]["valid"].mean(), .8)
        for s in m.sites:
            self.assertTrue(s["geometry"].is_valid)

    def test_event_result_does_not_use_future_scene(self):
        m = self.model
        a = m.analyze()
        future = m.scenes.pop("future")
        try:
            m.analyze.cache_clear()
            b = m.analyze()
            self.assertEqual(a["sites"], b["sites"])
            self.assertEqual(a["summary"], b["summary"])
        finally:
            m.scenes["future"] = future

    def test_real_spatial_analysis_and_holdout(self):
        m = self.model
        a = m.analyze()
        self.assertGreater(a["summary"]["new_water_km2"], 10)
        self.assertGreater(a["summary"]["direct"], 0)
        self.assertTrue(any(s["id"] == market.SITE_ID for s in a["sites"]))
        v = m.evaluate()["satellite_persistence"]
        self.assertGreater(v["pixels"], 10000)
        self.assertGreater(v["fp"], 0)  # The demo must expose real forecast errors.
        self.assertGreater(v["fn"], 0)
        self.assertGreaterEqual(v["f1"], 0)
        self.assertLessEqual(v["f1"], 1)

    def test_no_position_when_signal_not_triggered(self):
        with patch("market.market_rows", return_value=([
            {"date":"2024-05-07","open":100.,"close":101.},
            {"date":"2024-05-21","open":110.,"close":110.}], {})):
            e = market.event_study({"sites": []})
        self.assertEqual(e["net_pnl_usd_per_2usd"], 0)
        self.assertEqual(e["costs"]["transaction_usd"], 0)

    def test_market_prices_and_cost_accounting(self):
        e = market.event_study(self.model.analyze())
        self.assertTrue(e["plan"]["triggered"])
        for ticker in ["AGCO", "SPY"]:
            self.assertEqual(e["prices"][ticker]["rows"][0]["date"], "2024-05-07")
            self.assertGreater(e["prices"][ticker]["entry_open"], 0)
        self.assertAlmostEqual(e["gross_pnl_usd_per_2usd"]-e["net_pnl_usd_per_2usd"],
            e["costs"]["transaction_usd"]+e["costs"]["borrow_usd"])

    def test_pngs(self):
        for kind in ["before", "event", "future", "flood", "unknown", "error"]:
            self.assertTrue(self.model.png(kind).startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
