# Flood Alpha V2

Lauffähiger Python-Prototyp mit eigenem trainiertem Wasserklassifikator, historischer Referenz und transparenter Modellprüfung.

**Neu:** sechs Sentinel-2-Bänder, 16 spektrale Merkmale, separate Kalibrierung und Tests auf komplett zurückgehaltenen Länderereignissen. Der zusätzlich trainierte Zeitkandidat wurde nach schlechter späterer Leistung zurückgewiesen; Persistenz bleibt die aktive Zukunftsregel.

- [Modellergebnisse und Grenzen](MODELLBERICHT.md)
- [Methode, Daten, Training und Reproduktion](README_V2.md)
- [Ursprünglicher V1-Stand](README_V1.md)

## Start

Empfohlen: Python 3.12–3.14. Im entpackten Ordner `flood_alpha`:

```bash
bash run.sh
```

Alternativ:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Windows: `.venv\Scripts\activate` statt `source .venv/bin/activate`.

Browser: http://127.0.0.1:8765

Die erste Bibliotheksinstallation benötigt Internet. Danach arbeitet die gebündelte Demo offline. Keine API-Schlüssel und keine externen Kartenkacheln.

## Oberfläche

Die Karte bietet aktuelle Wassererkennung, Wasserscores, Unsicherheit, die alte V1-Regel und die freigegebene Tag-15-Prognose. Die spätere Beobachtung und Prognosefehler werden erst nach dem Aufdecken gezeigt. Die zurückgewiesene Zeitprognose wird bei der Auswertung ausdrücklich ausgewiesen.

Die Modellprüfung unterscheidet Klassifikationsleistung auf Referenzlabels von späteren Wasser-Prognosemetriken. Die Standort- und Handelsregeln sind weiterhin nachvollziehbare Heuristiken, keine trainierten Betriebs- oder Kursprognosen.

## Tests

```bash
python -m unittest discover -s tests -v
python app.py --export
```

Das Paket enthält trainierte Modelle, Stichprobendaten und Caches. Historische Rohbilder außerhalb der drei Demoaufnahmen werden im Downloadpaket ausgelassen und können bei Bedarf mit `python prepare_v2.py series` erneut geladen werden. Der Projektordner enthält den vollständigen heruntergeladenen Forschungsstand.

Lizenzen und Quellen: siehe README_V2.md und LICENSE. Anwendungscode MIT; Quelldaten behalten ihre jeweiligen Rechte.
