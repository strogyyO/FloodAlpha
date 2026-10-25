"""Real daily prices and an explicitly hypothetical, fixed-rule event study."""
from datetime import datetime, timezone
import json
from pathlib import Path
import requests

DATA = Path(__file__).resolve().parent / "data"
COMPANY_SOURCE = "https://www.sec.gov/Archives/edgar/data/880266/000088026624000013/agco-20231231.htm"
SITE_ID = "way/475623590"


def fetch_market():
    metadata = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "source": "Yahoo Finance chart API", "currency": "USD", "company_source": COMPANY_SOURCE, "tickers": {}}
    for ticker in ["AGCO", "SPY"]:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker
        params = {"period1": 1713139200, "period2": 1718409600, "interval": "1d", "events": "div,splits"}
        r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
        r.raise_for_status()
        d = r.json()
        if not d.get("chart", {}).get("result"):
            raise ValueError("Market data unavailable: " + ticker)
        (DATA / f"market_{ticker}.json").write_text(json.dumps(d), encoding="utf-8")
        metadata["tickers"][ticker] = r.url
    (DATA / "market_manifest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def market_rows(ticker):
    result = json.loads((DATA / f"market_{ticker}.json").read_text())["chart"]["result"][0]
    quotes = result["indicators"]["quote"][0]
    rows = []
    for i, ts in enumerate(result["timestamp"]):
        if quotes["open"][i] is None or quotes["close"][i] is None:
            continue
        rows.append({"date": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
                     "open": quotes["open"][i], "close": quotes["close"][i]})
    return rows, result.get("events", {})


def plan(analysis):
    site = next((s for s in analysis["sites"] if s["id"] == SITE_ID), None)
    trigger = site is not None and site["direct_fraction"] is not None and (site["direct_fraction"] >= .05 or (site["road_fraction"] or 0) >= .10)
    return {"ticker": "AGCO", "site_id": SITE_ID, "company_source": COMPANY_SOURCE,
            "rule": "Bei ≥5 % direkter Exposition oder ≥10 % nassem Straßenumfeld: hypothetisch Short AGCO und Long SPY, je 1 USD Ausgangsnotional; sonst keine Position.",
            "triggered": trigger, "action": "Prüfposition: Short AGCO / Long SPY" if trigger else "Keine Position nach der festgelegten Regel",
            "signal_date": "2024-05-06", "entry_date": "2024-05-07", "exit_date": "2024-05-21",
            "assumptions": "Eintritt zum nächsten Börsentages-Open, Austritt zum Close am 21. Mai. Keine echte Order. Exposition ist kein Nachweis eines Unternehmensausfalls. SPY ist ein grober Marktvergleich, kein Beta-/Sektorhedge."}


def event_study(analysis):
    p = plan(analysis)
    entry, exit_ = p["entry_date"], p["exit_date"]
    series = {}
    for ticker in ["AGCO", "SPY"]:
        rows, events = market_rows(ticker)
        selected = [r for r in rows if entry <= r["date"] <= exit_]
        if not selected or selected[0]["date"] != entry or selected[-1]["date"] != exit_:
            raise ValueError("Entry or exit price missing")
        if any(entry <= datetime.fromtimestamp(e["date"], timezone.utc).date().isoformat() <= exit_
               for e in events.get("splits", {}).values()):
            raise ValueError("Split within study window requires explicit share-count adjustment")
        initial = selected[0]["open"]
        dividends = [(datetime.fromtimestamp(e["date"], timezone.utc).date().isoformat(), e["amount"])
                     for e in events.get("dividends", {}).values()]
        # Cash dividends credited/debited on ex-date; no dividend reinvestment.
        for row in selected:
            cash = sum(amount for day, amount in dividends if entry < day <= row["date"])
            row["total_return"] = (row["close"]-initial+cash)/initial
        series[ticker] = {"entry_open": initial, "exit_close": selected[-1]["close"],
                          "total_return": selected[-1]["total_return"], "rows": selected}
    active = p["triggered"]
    days = (datetime.fromisoformat(exit_)-datetime.fromisoformat(entry)).days
    # Fixed 10bp per execution on each initial 1 USD leg; four executions in total.
    transaction_cost = .001*4 if active else 0
    borrow_cost = .05*days/365 if active else 0
    gross = (-series["AGCO"]["total_return"]+series["SPY"]["total_return"]) if active else 0
    curve = []
    spy_by_day = {r["date"]: r for r in series["SPY"]["rows"]}
    for r in series["AGCO"]["rows"]:
        if r["date"] in spy_by_day:
            pnl = (-r["total_return"]+spy_by_day[r["date"]]["total_return"])/2 if active else 0
            curve.append({"date": r["date"], "gross_return_on_gross_exposure": pnl})
    return {"plan": p, "prices": series, "curve": curve,
            "gross_pnl_usd_per_2usd": gross, "net_pnl_usd_per_2usd": gross-transaction_cost-borrow_cost,
            "net_return_on_gross_exposure": (gross-transaction_cost-borrow_cost)/2,
            "costs": {"transaction_usd": transaction_cost, "borrow_usd": borrow_cost, "per_execution_bps": 10, "annual_borrow_rate": .05},
            "limitations": "Eine rückblickend ausgewählte Fallstudie. Kein Nachweis kausaler Kurswirkung oder handelbaren Alphas; kein News-/Wettervergleich. Historische Datenverfügbarkeit und Leihbarkeit nicht belegt. Finanzierung, variable Leihsätze, Steuern und tatsächliche Ausführung nicht modelliert.",
            "source": json.loads((DATA / "market_manifest.json").read_text())}


if __name__ == "__main__":
    fetch_market()
    print("Real AGCO/SPY price series downloaded.")
