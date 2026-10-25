"""Offline-capable local Python dashboard. Run: python app.py"""
from __future__ import annotations
import argparse
import csv
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from model_v2 import FloodModel, DEFAULT_THRESHOLD, DEFAULT_DELTA
from market import plan, event_study
from quant_demo import quant_proxies, quant_sensor, quant_signal

ROOT = Path(__file__).resolve().parent


def parameters(query):
    q = parse_qs(query)
    specs = [("threshold", DEFAULT_THRESHOLD, .1, .95), ("delta", DEFAULT_DELTA, .05, .7), ("radius", 500, 100, 1500)]
    values = []
    for name, default, lower, upper in specs:
        try:
            v = float(q.get(name, [default])[0])
        except (ValueError, TypeError):
            raise ValueError(f"Invalid parameter: {name}")
        if not lower <= v <= upper:
            raise ValueError(f"Parameter {name} must be in [{lower}, {upper}]")
        values.append(round(v, 3) if name != "radius" else int(v))
    return values


def make_handler(model):
    class Handler(BaseHTTPRequestHandler):
        def send(self, body, mime="application/json; charset=utf-8", status=200, filename=None):
            if not isinstance(body, bytes):
                body = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            try:
                threshold, delta, radius = parameters(parsed.query)
                if parsed.path in ["/", "/index.html"]:
                    html=(ROOT/"web"/"index.html").read_text().replace("__DEFAULT_THRESHOLD__",str(round(DEFAULT_THRESHOLD,3)))
                    return self.send(html, "text/html; charset=utf-8")
                if parsed.path.startswith("/static/"):
                    static_root = (ROOT/"web"/"static").resolve()
                    target = (static_root/parsed.path.removeprefix("/static/")).resolve()
                    mime = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}.get(target.suffix)
                    if not mime or not target.is_relative_to(static_root) or not target.is_file():
                        return self.send("Not found", "text/plain", 404)
                    return self.send(target.read_bytes(), mime)
                if parsed.path == "/health":
                    return self.send(json.dumps({"status": "ok", "model_version":"2.0", "sites": len(model.sites), "data": "real Sentinel-2 + historical OSM", "active_forecast":model.forecast_report["deployment"]}))
                if parsed.path == "/api/analysis":
                    return self.send(json.dumps(model.analyze(threshold, delta, radius), allow_nan=False))
                if parsed.path == "/api/model-info":
                    return self.send(json.dumps(model.model_info(), allow_nan=False))
                if parsed.path == "/api/validation":
                    return self.send(json.dumps(model.evaluate(threshold, delta), allow_nan=False))
                if parsed.path == "/api/trading-plan":
                    return self.send(json.dumps(plan(model.analyze(threshold, delta, radius)), allow_nan=False))
                if parsed.path == "/api/event-study":
                    return self.send(json.dumps(event_study(model.analyze(threshold, delta, radius)), allow_nan=False))
                if parsed.path.startswith("/image/"):
                    kind = parsed.path.split("/")[-1].removesuffix(".png")
                    if kind not in ["before", "event", "future", "flood", "unknown", "error", "forecast", "probability", "uncertainty", "legacy"]:
                        return self.send("Not found", "text/plain", 404)
                    return self.send(model.png(kind, threshold, delta), "image/png")
                if parsed.path == "/export/sites.csv":
                    fields = ["id", "name", "score", "signal", "direct_fraction", "forecast_fraction", "uncertain_fraction", "road_fraction", "coverage", "approximate", "forecast", "osm_url"]
                    out = io.StringIO()
                    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
                    writer.writeheader()
                    for row in model.analyze(threshold, delta, radius)["sites"]:
                        # Prevent spreadsheet formula execution from untrusted OSM names.
                        safe = {k: ("'"+v if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r")) else v) for k,v in row.items()}
                        writer.writerow(safe)
                    return self.send("\ufeff"+out.getvalue(), "text/csv; charset=utf-8", filename="flood_alpha_sites.csv")
                if parsed.path == "/export/analysis.json":
                    return self.send(json.dumps(model.analyze(threshold, delta, radius), indent=2, allow_nan=False), filename="flood_alpha_analysis.json")
                if parsed.path in ["/api/quant/proxies", "/api/quant/sensor", "/api/quant/signal"]:
                    # Illustrative demo terminal, unrelated to the flood/market analysis above.
                    # Requires live internet access; see quant_demo.py for what is and isn't real here.
                    q = parse_qs(parsed.query)
                    ticker = q.get("ticker", [""])[0]
                    if parsed.path == "/api/quant/proxies":
                        return self.send(json.dumps(quant_proxies(ticker)))
                    if parsed.path == "/api/quant/sensor":
                        return self.send(json.dumps(quant_sensor(ticker, q.get("proxy_id", [""])[0])))
                    return self.send(json.dumps(quant_signal(ticker)))
                return self.send("Not found", "text/plain", 404)
            except (ValueError, KeyError) as exc:
                return self.send(json.dumps({"error": str(exc)}), status=400)
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as exc:
                self.log_error("%s", exc)
                return self.send(json.dumps({"error": "Verarbeitung fehlgeschlagen. Details im Python-Terminal."}), status=500)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--export", action="store_true", help="Write analysis and validation JSON without starting a server")
    args = parser.parse_args()
    model = FloodModel()
    if args.export:
        (ROOT/"analysis.json").write_text(json.dumps(model.analyze(), indent=2, allow_nan=False))
        (ROOT/"validation.json").write_text(json.dumps(model.evaluate(), indent=2, allow_nan=False))
        (ROOT/"event_study.json").write_text(json.dumps(event_study(model.analyze()), indent=2, allow_nan=False))
        print("analysis.json, validation.json and event_study.json written.")
        return
    server = ThreadingHTTPServer((args.host, args.port), make_handler(model))
    print(f"Flood Alpha läuft: http://{args.host}:{args.port}\nBeenden: Ctrl+C", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
