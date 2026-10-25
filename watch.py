"""Archived, dated weather alerts and news reports that would have flagged this area for
satellite tasking before any image confirmed flooding.

This is a fixed historical record (data/watch_feed.json), not a live news or weather feed:
no API key, no network call, each entry cites its own public source. It demonstrates the
"use news and weather to predict where to look" idea on one historical event, in the same
offline, reproducible spirit as the rest of this app.
"""
from __future__ import annotations
from datetime import date
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
LEVEL_RANK = {"advisory": 1, "watch": 2, "warning": 3, "emergency": 4}
SATELLITE_SIGNAL_DATE = "2024-05-06"


def load():
    return json.loads((DATA / "watch_feed.json").read_text())


def feed():
    raw = load()
    entries = sorted(raw["entries"], key=lambda e: e["date"])
    alerts = [e for e in entries if e["level"] in LEVEL_RANK]
    if not alerts:
        raise ValueError("No weather/news alerts in watch_feed.json")
    peak = max(alerts, key=lambda e: LEVEL_RANK[e["level"]])
    first = alerts[0]
    lead_days = (date.fromisoformat(SATELLITE_SIGNAL_DATE) - date.fromisoformat(first["date"])).days
    peak_lead_days = (date.fromisoformat(SATELLITE_SIGNAL_DATE) - date.fromisoformat(peak["date"])).days
    # Chartable series derived straight from the same entries: no separate numbers to keep in sync.
    level_series = [{"date": e["date"], "level": e["level"], "level_rank": LEVEL_RANK.get(e["level"])}
                     for e in entries]
    river_level_series = [{"date": e["date"], "level_m": e["level_m"], "headline": e["headline"],
                            "source": e["source"], "source_url": e["source_url"]}
                           for e in entries if e.get("level_m") is not None]
    return {
        "area": raw["area"],
        "entries": entries,
        "note": raw["source_note"],
        "numeric_discrepancy_note": raw.get("numeric_discrepancy_note"),
        "level_series": level_series,
        "river_level_series": river_level_series,
        "historical_record": raw.get("historical_record"),
        "first_alert_date": first["date"],
        "first_alert_level": first["level"],
        "peak_level": peak["level"],
        "peak_level_date": peak["date"],
        "satellite_signal_date": SATELLITE_SIGNAL_DATE,
        "lead_time_days": lead_days,
        "peak_lead_time_days": peak_lead_days,
        "summary": (f"Archived alerts for this area first reached '{first['level']}' level on "
                    f"{first['date']}, {lead_days} day(s) before the satellite signal scene used "
                    f"in this case study ({SATELLITE_SIGNAL_DATE}), and reached '{peak['level']}' "
                    f"level on {peak['date']}, {peak_lead_days} day(s) before that scene. In a live "
                    "deployment, this kind of feed -- not the satellite -- is what would trigger "
                    "tasking a fresh image of this area in the first place."),
    }


if __name__ == "__main__":
    print(json.dumps(feed(), indent=2))
