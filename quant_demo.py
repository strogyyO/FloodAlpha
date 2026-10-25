"""Illustrative alt-data terminal — NOT part of the flood/market analysis.

Everything here is clearly a demonstration, not real financial research:

  - The "physical alt-data proxies" are fictional narrative examples of the
    KIND of unconventional signal a quant fund might track (e.g. "Supercharger
    queue length"). None of them is actually being measured by this code —
    there is no real sensor, satellite feed, or scrape behind any of them.
  - The "sensor" series returned by quant_sensor() is synthetically generated
    from the real stock price plus random noise, shaped to look plausibly
    correlated without being a visibly perfect clone of the price. It is
    fabricated data, labeled as such in every response ("simulated": true).
  - The "signal" returned by quant_signal() is a coin flip (random.random())
    with a randomly generated confidence score. It carries no analytical
    content and is labeled accordingly.

The only real data used anywhere in this module is the daily close price,
fetched live from Yahoo Finance's public chart API — the same approach
market.py already uses for AGCO/SPY. Unlike the rest of Flood Alpha, which
runs fully offline after first install, this module requires live internet
access each time a ticker is looked up.
"""
from __future__ import annotations
import hashlib
import random
from datetime import datetime, timedelta
import requests

SUPPORTED_TICKERS = ["TSLA", "WMT", "NKE", "XOM", "CAT"]

COMPANY_SPECIFIC_PROXIES = {
    "TSLA": [
        {"id": "tsla_supercharger_queue", "name": "Supercharger Queue Length & Idle Time",
         "metric": "Vehicles Waiting / Peak Minutes", "edge": "Real-time (vs monthly delivery numbers)",
         "mechanism": "Tesla's direct-to-consumer model means Supercharger usage is a proxy for active fleet utilization and new demand.",
         "financial_transmission": "Lower utilization -> lower brand heat -> lower demand growth -> margin compression.",
         "deep_dive": "A fictional example of a leading, high-frequency proxy versus a lagging, low-frequency official metric."},
        {"id": "tsla_paint_shop_thermal", "name": "Gigafactory Paint Shop Thermal Signature",
         "metric": "HVAC Cooling Load (MW)", "edge": "Daily (vs quarterly production reports)",
         "mechanism": "The paint shop is a common bottleneck in EV manufacturing; thermal load over the paint shop roof is often used as an illustration of a production-cadence proxy.",
         "financial_transmission": "Paint shop bottleneck -> lower throughput -> higher unit COGS -> missed margin targets.",
         "deep_dive": "Illustrates how a facility-level physical signal could, in principle, lead an official quarterly report."},
        {"id": "tsla_austin_steel_customs", "name": "Specialty Steel Coil Imports to Austin, TX",
         "metric": "Shipment Volume (Metric Tonnes)", "edge": "Weekly (vs quarterly production guidance)",
         "mechanism": "Customs import data for specific steel grades destined for a known factory is a commonly cited example of public-but-rarely-parsed data.",
         "financial_transmission": "Drop in raw material intake -> production slowdown -> revenue miss.",
         "deep_dive": "A textbook example of a 'hidden in plain sight' public dataset."},
    ],
    "WMT": [
        {"id": "wmt_pickup_spot_occupancy", "name": "Grocery Pickup Spot Occupancy",
         "metric": "Designated Spot Fill Rate (%)", "edge": "Daily (vs monthly same-store sales)",
         "mechanism": "Counting occupied pickup-only parking spots is a common illustration of a high-margin-channel proxy.",
         "financial_transmission": "High pickup occupancy -> grocery share gains -> better margin mix -> EPS beat.",
         "deep_dive": "Distinguishes high-margin pre-committed buyers from general low-margin foot traffic."},
        {"id": "wmt_bentonville_truck_idle", "name": "Distribution Center Truck Idling",
         "metric": "Diesel Particulate / Idle Hours", "edge": "Weekly (vs quarterly inventory turn)",
         "mechanism": "Freight truck idle time at a central distribution hub is a common illustration of an inventory-flow proxy.",
         "financial_transmission": "Fast turnover -> lower working capital -> higher free cash flow.",
         "deep_dive": "Illustrates a physical-logistics proxy for a balance-sheet metric."},
        {"id": "wmt_great_value_scraping", "name": "Private-Label Price Change Scraping",
         "metric": "Price Change Frequency & Magnitude (%)", "edge": "Daily (vs quarterly gross margin reports)",
         "mechanism": "Scraping public e-commerce listings for price-change timing is a standard, legal alt-data category.",
         "financial_transmission": "Stable private-label pricing vs. rising national brands -> margin expansion.",
         "deep_dive": "One of the more common real alt-data categories in practice, shown here as a fictional example."},
    ],
    "NKE": [
        {"id": "nke_snkrs_velocity", "name": "Limited-Release App Sellout Velocity",
         "metric": "Milliseconds to Sell Out", "edge": "Real-time (vs quarterly brand-heat surveys)",
         "mechanism": "Sellout speed on a releases app is a commonly cited 'hype' proxy.",
         "financial_transmission": "Faster sellout -> higher full-price sell-through -> less promotional discounting.",
         "deep_dive": "Illustrates an objective transaction-based proxy versus a subjective survey metric."},
        {"id": "nke_vietnam_factory_light", "name": "Supplier Factory Nighttime Lights",
         "metric": "Radiance (nW/cm²/sr)", "edge": "Monthly (vs monthly revenue reports)",
         "mechanism": "Nighttime satellite radiance over a known manufacturing region is a textbook alt-data example.",
         "financial_transmission": "Lower factory lights -> production curtailment -> supply shortage -> revenue miss.",
         "deep_dive": "One of the most cited real categories of satellite-derived alt-data, shown here illustratively."},
        {"id": "nke_stockx_premium", "name": "Secondary Market Resale Premium Index",
         "metric": "Average Resale Price vs. Retail (%)", "edge": "Real-time (vs quarterly order cancellations)",
         "mechanism": "Resale-market premiums are commonly used to illustrate demand-sentiment proxies.",
         "financial_transmission": "Collapsing resale premium -> weakening brand heat -> future order cancellations.",
         "deep_dive": "Illustrates a market-based sentiment proxy."},
    ],
    "XOM": [
        {"id": "xom_permian_flare_shadow", "name": "Storage Tank Floating-Roof Shadow Geometry",
         "metric": "Shadow Rim Diameter (Meters)", "edge": "Daily (vs weekly EIA reports)",
         "mechanism": "Floating-roof tank shadow length is a well-known real technique for estimating oil storage levels from satellite imagery.",
         "financial_transmission": "Inventory draws -> tighter supply -> higher realized price -> upstream EBITDA uplift.",
         "deep_dive": "One of the better-documented real satellite alt-data techniques, shown here illustratively."},
        {"id": "xom_guyana_fpso_docking", "name": "Tanker Docking Frequency at a Named Asset",
         "metric": "Ship-to-Ship Transfers per Month", "edge": "Weekly (vs quarterly production guidance)",
         "mechanism": "Public AIS vessel-tracking data is a standard, legal alt-data category for monitoring a specific offshore asset.",
         "financial_transmission": "Increased docking frequency -> higher realized output -> free cash flow expansion.",
         "deep_dive": "AIS-based tracking is widely used in practice; shown here as an illustrative example."},
        {"id": "xom_padd3_barge_rates", "name": "Regional Barge Freight Rates",
         "metric": "Freight Cost per Barrel ($/bbl)", "edge": "Daily (vs monthly refining margin reports)",
         "mechanism": "Local logistics costs are a common illustration of a refining-margin proxy beyond headline crude prices.",
         "financial_transmission": "Spiking freight + flat product prices -> refining margin compression.",
         "deep_dive": "Illustrates that margins depend on local logistics, not just commodity prices."},
    ],
    "CAT": [
        {"id": "cat_moline_rail_dwell", "name": "Rail Yard Dwell Time at a Named Hub",
         "metric": "Railcar Hours in Yard", "edge": "Daily (vs monthly ISM manufacturing)",
         "mechanism": "Rail dwell time at a known shipping hub is a common illustration of a dealer-restocking proxy.",
         "financial_transmission": "Lower dwell time -> faster dealer restocking -> higher recognized revenue.",
         "deep_dive": "Illustrates a physical-logistics proxy for channel health."},
        {"id": "cat_dealer_lot_satellite", "name": "Dealer Lot Inventory Density (Computer Vision)",
         "metric": "Machines per Acre on Dealer Lots", "edge": "Monthly (vs quarterly dealer inventory reports)",
         "mechanism": "Satellite object-counting on dealer lots is a commonly cited real computer-vision alt-data technique.",
         "financial_transmission": "High lot density -> channel stuffing or demand softness -> future production cuts.",
         "deep_dive": "One of the better-known real computer-vision alt-data use cases, shown here illustratively."},
        {"id": "cat_hms_scrap_differential", "name": "Regional Scrap Steel Price Differential",
         "metric": "Local Price vs. Global Benchmark ($/ton)", "edge": "Weekly (vs quarterly COGS reports)",
         "mechanism": "Scrap steel pricing is a widely cited leading indicator of industrial demand.",
         "financial_transmission": "Widening negative differential -> weakening demand -> lower future equipment orders.",
         "deep_dive": "Illustrates a commodity-market proxy for downstream industrial demand."},
    ],
}

PROXY_CORRELATION = {
    "tsla_supercharger_queue": 1, "tsla_paint_shop_thermal": 1, "tsla_austin_steel_customs": 1,
    "wmt_pickup_spot_occupancy": 1, "wmt_bentonville_truck_idle": 1, "wmt_great_value_scraping": 1,
    "nke_snkrs_velocity": -1, "nke_vietnam_factory_light": 1, "nke_stockx_premium": 1,
    "xom_permian_flare_shadow": -1, "xom_guyana_fpso_docking": 1, "xom_padd3_barge_rates": -1,
    "cat_moline_rail_dwell": -1, "cat_dealer_lot_satellite": -1, "cat_hms_scrap_differential": 1,
}

COMPANY_NAMES = {
    "TSLA": "Tesla, Inc.", "WMT": "Walmart Inc.", "NKE": "NIKE, Inc.",
    "XOM": "Exxon Mobil Corporation", "CAT": "Caterpillar Inc.",
}


def quant_proxies(ticker):
    ticker = ticker.strip().upper()
    if ticker not in SUPPORTED_TICKERS:
        return {"success": False, "error": f"'{ticker}' is not in this demo's supported list: {', '.join(SUPPORTED_TICKERS)}."}
    return {"success": True, "data": {"name": COMPANY_NAMES[ticker], "ticker": ticker,
            "proxies": COMPANY_SPECIFIC_PROXIES[ticker], "simulated": True}}


def _fetch_real_stock_data(ticker):
    """Live fetch of real daily closes via Yahoo's public chart API (same approach as market.py)."""
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker
        r = requests.get(url, params={"range": "1mo", "interval": "1d"}, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        r.raise_for_status()
        result = r.json().get("chart", {}).get("result")
        if not result:
            return None
        result = result[0]
        closes = result["indicators"]["quote"][0]["close"]
        dates, values = [], []
        for ts, close in zip(result["timestamp"], closes):
            if close is None:
                continue
            dates.append(datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d"))
            values.append(round(close, 2))
        return {"dates": dates, "values": values} if len(values) >= 5 else None
    except (requests.RequestException, ValueError, KeyError):
        return None


def quant_sensor(ticker, proxy_id):
    ticker = ticker.strip().upper()
    if ticker not in SUPPORTED_TICKERS:
        return {"success": False, "error": f"'{ticker}' is not in this demo's supported list."}
    real_stock = _fetch_real_stock_data(ticker)

    if not real_stock:
        days = 30
        dates = [(datetime.now() - timedelta(days=days - i)).strftime("%Y-%m-%d") for i in range(days)]
        seed = int(hashlib.md5(proxy_id.encode()).hexdigest(), 16) % 1000
        rng = random.Random(seed)
        base = rng.uniform(40, 100)
        values = [round(base + rng.uniform(-2, 2), 2) for _ in range(days)]
        return {"success": True, "data": {"dates": dates, "values": values, "real_stock_baseline": None,
                "simulated": True, "note": "No live price data available; proxy values are fully synthetic."}}

    dates, real_prices = real_stock["dates"], real_stock["values"]
    direction = PROXY_CORRELATION.get(proxy_id, 1)
    rng = random.Random()
    values = [50.0]
    for i in range(1, len(real_prices)):
        daily_return = (real_prices[i] - real_prices[i - 1]) / real_prices[i - 1]
        trend_bias = daily_return * 100 * direction * 0.4
        noise = rng.uniform(-2.5, 2.5)
        values.append(round(values[-1] + trend_bias + noise, 2))

    return {"success": True, "data": {"dates": dates, "values": values, "real_stock_baseline": real_stock,
            "simulated": True, "note": "Proxy values are synthetically generated from the real price plus random noise, not a real measurement."}}


def quant_signal(ticker):
    ticker = ticker.strip().upper()
    if ticker not in SUPPORTED_TICKERS:
        return {"success": False, "error": f"'{ticker}' is not in this demo's supported list."}
    rng = random.Random()
    action = "LONG" if rng.random() > 0.4 else "SHORT"
    return {"success": True, "data": {
        "action": f"{action} {ticker}", "confidence": rng.randint(75, 95),
        "hedge": "Short SPY" if action == "LONG" else "Long SPY", "stop_loss": "-2.5%",
        "rationale": "Demo only: this action is chosen at random (not derived from the proxy data above) to illustrate what a terminal's execution panel might look like.",
        "simulated": True}}
