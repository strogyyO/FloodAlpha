# Flood Alpha — lauffähiger Python-Prototyp mit echten Daten

Historische Fallstudie der Überflutung von Canoas, Brasilien, Mai 2024.

Die Anwendung verbindet echte Satellitenbilder mit historischen Industriestandorten und Straßen, erstellt eine Expositions-Watchlist, prüft eine einfache 15-Tage-Prognose und rechnet eine feste hypothetische Börsenposition mit echten AGCO-/SPY-Kursen durch.

## Start

Python 3.10 oder neuer, empfohlen 3.12–3.14. ZIP entpacken und im Ordner `flood_alpha`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Im Browser öffnen: **http://127.0.0.1:8765**

Windows: statt `source` den Befehl `.venv\Scripts\activate` verwenden; gegebenenfalls `python` statt `python3`.

Auf macOS/Linux alternativ `bash run.sh`. Die erste Installation braucht Internet. Danach läuft die mitgelieferte Fallstudie vollständig offline: keine API-Schlüssel, keine externen Kartenkacheln, keine Cloud-Anwendung. Die mitgelieferten Daten sind echte heruntergeladene Ausschnitte, keine simulierten Bilder.

## Demo in drei Minuten

1. Auf **21. Apr · vorher** klicken: die Situation vor der Flut.
2. Auf **06. Mai · Signal** wechseln: neue Wasserflächen und Standortexposition erkunden.
3. Standort in der Tabelle anklicken. Direkte Exposition und nasse Straßen im Umfeld sind getrennt ausgewiesen. AGCO South America befindet sich ebenfalls in der Liste.
4. Die feste hypothetische Tradingregel für AGCO ansehen. Ihr Kursausgang bleibt zunächst verborgen.
5. **15 Tage vorspulen**: die Aufnahme vom 21. Mai, Fehlerkarte, Prognosemetriken und den tatsächlichen Kursverlauf aufdecken.
6. CSV oder JSON exportieren. Parameter ändern und die Empfindlichkeit untersuchen. Nach dem Aufdecken sind Änderungen explorativ, kein neuer unberührter Test.

## Daten und Zeitpunkte

| Bestandteil | Herkunft | Zeitraum |
|---|---|---|
| Vorher-Aufnahme | Copernicus Sentinel-2 L2A, Kachel 22JDN | 21.04.2024 |
| Signal-Aufnahme | Copernicus Sentinel-2 L2A, Kachel 22JDN | 06.05.2024 |
| Spätere Beobachtung | Copernicus Sentinel-2 L2A, Kachel 22JDN | 21.05.2024 |
| Industriestandorte, Straßen, Brücken | Historischer OpenStreetMap-Snapshot via Overpass | 24.04.2024 |
| AGCO und SPY | Yahoo Finance, tägliche Open-/Close-Kurse und Dividenden | April–Juni 2024 |
| Zuordnung AGCO ↔ Canoas | AGCO Form 10-K 2023, SEC | vor dem Ereignis veröffentlicht |

Analysegebiet: 51.30°W bis 51.07°W, 29.91°S bis 29.74°S. Gemeinsames Raster: EPSG:32722, 20 m, 1114 × 945 Pixel. Die Reflektanzbänder B02/B03/B04/B11 und die Szenenklassifikation SCL liegen komprimiert in `data/`. Die Einzelaufnahmen, ursprüngliche STAC-Metadaten, Original-OSM-Objekte, Marktpreisantworten und SHA-256-Prüfsummen werden mitgeliefert. Es werden keine vorübergehend signierten Download-URLs gespeichert.

Primärquellen und Zugriff:

- [Planetary Computer / Sentinel-2](https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a)
- [Copernicus Sentinel-2](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2)
- [Historische Overpass-Abfragen](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL#date)
- [AGCO 2023 10-K, SEC](https://www.sec.gov/Archives/edgar/data/880266/000088026624000013/agco-20231231.htm)
- Die exakten Szenen- und Daten-URLs stehen in `data/manifest.json` und `data/market_manifest.json`.

Der Archivabruf erfolgte bei Erstellung des Prototyps. Aufnahmedatum und heutige STAC-Metadaten beweisen nicht, wann ein Marktteilnehmer damals das Bild hätte erhalten können. Historische Veröffentlichungs- und Verarbeitungslatenzen sind nicht rekonstruiert.

## Was berechnet wird

### Wassererkennung

MNDWI = (B03 − B11) / (B03 + B11), auf Reflektanzen mit korrekter Skalierung und additivem Offset. Die Bänder werden auf ein gemeinsames 20-m-Raster gebracht. SCL-Klassen 0, 1, 2, 3, 8, 9, 10 und 11 werden ausgeschlossen, um ungültige Pixel, dunkle Flächen, Schatten, Wolken und Schnee zu maskieren. Der Maskenrand wird um zwei Pixel erweitert.

Neue Wasserpixel am 6. Mai erfüllen gleichzeitig:

- am 21. April und 6. Mai gültig;
- vorher MNDWI ≤ Wasserschwelle;
- am 6. Mai MNDWI > Wasserschwelle;
- MNDWI-Zunahme > Änderungsschwelle.

Zusammenhängende Flecken mit weniger als 25 Pixeln (1 ha) werden entfernt. Startwerte: Wasserschwelle 0.15, Änderungsschwelle 0.18. Das ist eine nachvollziehbare spektrale Heuristik, kein trainiertes Segmentierungsmodell. Es wird kein erfundenes Genauigkeitsmaß der Fluterkennung angegeben.

### Exposition

Die OSM-Industrieflächen werden mit neuem Wasser verschnitten. OSM-Punktobjekte haben kein belegtes Fabrikpolygon und werden ausdrücklich als 60-m-Näherung markiert. Generische Industrieflächen, die benannte Produktionsstätten enthalten, werden entfernt, um einige Doppelzählungen zu vermeiden; vollständige Entity-Auflösung ist nicht garantiert.

Straßen werden mit einem 10-m-Puffer gerastert. Der Anteil nasser Straßenpixel im einstellbaren Standortumfeld ist ein Prüfhinweis. Brücken und Tunnel sind ausgenommen. Es findet **keine** Verkehrsflussanalyse und **kein** Nachweis fehlender Alternativrouten statt.

Prüfindex = 70 × direkt exponierter Flächenanteil + 30 × nasser Straßenanteil. Standorte mit weniger als 80 % gültiger Flächenabdeckung werden nicht bewertet. Dieser Index ist keine kalibrierte Ausfallwahrscheinlichkeit.

### Echte Vorwärtsprognose mit einfachem Modell

Der am 6. Mai eingefrorene Persistenzansatz sagt: Neu erkannte Wasserflächen bleiben am 21. Mai nass. Der Zukunftsdatensatz wird bei der Prognose und dem Standort-Ranking nicht benutzt; das wird getestet. Erst die Auswertung greift darauf zu.

F1, Präzision, Recall und IoU werden nur auf in allen drei Aufnahmen gültigen, zuvor trockenen Pixeln berechnet. Die Vergleichsmethode lautet „keine neue Wasserfläche“. Das ist absichtlich eine schwache Referenz. Ein sinnvoller Wetter-/Pegelvergleich fehlt noch.

Die Referenz vom 21. Mai entsteht aus **demselben Sensor und demselben Wasserindex**. Sie ist eine spätere Beobachtung, keine unabhängige Ground Truth. Die Metriken bewerten Wasserpersistenz, keine Betriebsunterbrechungen. Es ist ein einziges räumlich zusammenhängendes Ereignis; Pixel sind keine unabhängigen Testfälle.

### Hypothetische Tradingregel mit echten Preisen

Die AGCO-OSM-Fläche `way/475623590` wird anhand des Namens und des in der SEC-Unternehmensquelle belegten Standorts Canoas zugeordnet. Diese Zuordnung ist manuell kuratiert, keine automatische globale Unternehmensauflösung.

Fest implementierte Demonstrationsregel: ≥5 % direkte Flächenexposition oder ≥10 % nasses Straßenumfeld → Short AGCO und Long SPY mit jeweils 1 USD Ausgangsnotional; sonst keine Position. Keine Order wird gesendet. Einstieg am 7. Mai 2024 zum Open, Ausstieg am 21. Mai zum Close. Zeitraum, Instrumente und Schwellen sind eine rückblickend konzipierte Fallstudie, kein vorab registrierter Handelstest.

- Stückzahlen werden beim Einstieg aus dem Preis berechnet und nicht täglich neu gewichtet.
- Cash-Dividenden zwischen Einstieg und Ausstieg werden als Gutschrift bzw. Short-Verpflichtung berücksichtigt; keine Wiederanlage.
- Transaktionskosten: 10 Basispunkte pro Ausführung auf das anfängliche Notional, vier Ausführungen.
- Aktienleihe: pauschal 5 % p.a. auf 1 USD Short-Notional für die Kalendertage.
- Angezeigte Nettorendite = Netto-P&L / 2 USD anfänglicher Bruttoexposition. Sie ist keine Rendite auf Margin oder unbekanntes Eigenkapital.
- SPY ist ein grober Dollar-Marktvergleich, kein Beta- oder Sektorhedge. Finanzierung, tatsächliche Leihverfügbarkeit, variable Leihkosten, Steuern und Slippage über den pauschalen Kostensatz hinaus fehlen.

**Ein positives Ergebnis belegt weder Kausalität noch handelbares Alpha.** Es fehlt insbesondere der Vergleich mit zeitgleich verfügbaren Nachrichten, Wetterdaten und Pegeln. Die Aktienkurse können aus vielen anderen Gründen reagieren. Aus Satellitenbildern werden keine internen Maschinenschäden oder bestätigten Betriebsunterbrechungen abgeleitet. Zulieferbeziehungen sind nicht erfunden oder als Platzhalter eingetragen.

## Dateien

- `app.py`: lokaler HTTP-Server, CSV-/JSON-Export, Parameterprüfung.
- `model.py`: Rasterverarbeitung, Wassererkennung, Standortanalyse, spätere Auswertung.
- `market.py`: reproduzierbarer Kursdownload, feste Handelsregel, hypothetische Ergebnisrechnung.
- `fetch_data.py`: API-Abfragen und räumliche Downloads; Wiederaufnahme vorhandener Bildausschnitte.
- `web/index.html`: lokale Oberfläche, interaktive Karte, Zukunft aufdecken, Ergebnisgrafik.
- `data/`: echte Daten, Metadaten und Herkunft.
- `tests/test_core.py`: numerische Prüfung, Datenintegrität, Zukunftstrennung und Kostenrechnung.
- `analysis.json`, `validation.json`, `event_study.json`: vorberechnete Ergebnisse mit Startparametern.

## Neu berechnen, Daten herunterladen und testen

```bash
# Vorbereitete Ergebnisse neu berechnen
python app.py --export

# Tests mit mitgelieferten Daten
python -m unittest discover -s tests -v

# Daten vollständig neu herunterladen (Internet erforderlich)
python fetch_data.py --force

# Nur Kurse erneut herunterladen
python market.py

# Anderen lokalen Port verwenden
python app.py --port 8766
```

Die archivierten Daten ermöglichen eine stabile Offline-Demo. Erneute Downloads hängen von der Erreichbarkeit, Verfügbarkeit und den Limits der externen APIs ab. Yahoo Finance ist kein vertraglich garantierter Marktdatenfeed. Bei Fehlern bricht der Download ab; es werden keine synthetischen Ersatzdaten erzeugt.

## Nächster sinnvoller Forschungsschritt

Mehrere Ereignisse und Regionen vorab festlegen, zeitgenössische Nachrichten/Wetter/Pegel samt Veröffentlichungszeitpunkten sichern, tatsächliche Unterbrechungen unabhängig labeln und anschließend dieselbe Prognose mit und ohne Bilddaten vergleichen. Erst dann lässt sich die ursprüngliche Frage nach notwendiger Satelliteninformation belastbar beantworten.

## Datenrechte

Enthält modifizierte Copernicus Sentinel-Daten 2024; siehe [Copernicus-Rechte](https://www.copernicus.eu/en/access-data/copyright-and-licences). © OpenStreetMap-Mitwirkende, [ODbL 1.0 / Namensnennung](https://www.openstreetmap.org/copyright). OSM-Ausschnitte bleiben ODbL-lizenziert. Kursdaten sind für diese lokale Demonstration beigefügt; bei Veröffentlichung oder Weiterverteilung gelten die Nutzungsbedingungen des Datenanbieters, insbesondere keine pauschal zugesicherte Open-Data-Lizenz. Der Anwendungscode steht unter MIT (siehe LICENSE).
