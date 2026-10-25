# Flood Alpha V2 — Modellierung, Klassifikation und Prüfung

Diese Version enthält einen selbst trainierten spektralen Wasserklassifikator und eine separat trainierte zeitliche Wasserprognose. Die ursprüngliche feste Regel bleibt in `model.py` erhalten. Die aktive Anwendung verwendet `model_v2.py`.

## Die Modellkette

1. Sentinel-2-L2A-Oberflächenreflektanzen aus B02/B03/B04/B08/B11/B12.
2. Gemeinsames 20-m-Raster, gültige Beobachtungen und Wolkenmaske.
3. Eigener Klassifikator aus sechs Bändern und zehn spektralen Merkmalen.
4. Separate Kalibrierung; Entscheidungsschwelle auf einem anderen Validierungsereignis.
5. Historische Referenz aus mehreren ausschließlich früheren Bildern.
6. Neue Wasserflächen als Abweichung von der Referenz mit räumlicher Zusammenhangsprüfung.
7. Zeitmodell aus kausalen Bildfolgen; Vergleich und mögliche Kombination mit Persistenz.
8. Standortexposition, Unsicherheit und explizit hypothetische Trading-Fallstudie.

Es werden keine externen Modellgewichte für die Wassererkennung oder Zeitprognose verwendet. Die L2A-Vorverarbeitung und Szenenklassifikation stammen weiterhin aus dem Copernicus-Datenprodukt.

## Trainingsreferenz und geographische Trennung

Die Referenz ist eine feste Teilstichprobe von Sen1Floods11. Für jedes vorhandene Länderereignis werden bis zu acht Chips per SHA-256-Sortierung ausgewählt. Expertenlabels werden aus dem öffentlichen Dataset geladen. Die passenden Sentinel-2-L2A-Bilder werden separat aus Planetary Computer neu beschafft, damit Training und Anwendung dieselbe Verarbeitungsebene haben. Die im Referenzdatensatz mitgelieferten L1C-Bilder werden nicht als Trainingseingabe verwendet.

Die Labels stammen aus einer optischen Initialklassifikation mit manueller Nachbearbeitung durch Fachleute; sie sind **keine unabhängigen Feldmessungen** und können verbleibende algorithmische/analytische Fehler enthalten. Für die Aggregation auf das 20-m-Raster bleiben nur homogene 2×2-Labelblöcke erhalten. Wolken, ungültige Pixel und unklare Labels werden nicht als trocken interpretiert. Pro Chip wird eine gleichverteilte Stichprobe von bis zu 5.000 gültigen Pixeln gezogen. Zwei der angefragten Chips werden wegen zu geringer gültiger Abdeckung ausgeschlossen; die Gründe stehen im Referenzmanifest.

Feste Partitionen:

| Zweck | Länderereignisse |
|---|---|
| Training | Ghana, Indien, Mekong, Nigeria, Pakistan, Somalia, Sri Lanka |
| Kalibrierung | Paraguay |
| Modell- und Schwellenwahl | Spanien |
| Zurückgehaltener Klassifikationstest | Bolivien, USA |

Die Stichprobe enthält 86 Chips und 423.699 Pixel: 268.699 Training, 35.000 Kalibrierung, 40.000 Auswahl, 80.000 Test. Pixel sind räumlich korreliert; die Zahl der Pixel ist nicht die Zahl unabhängiger Ereignisse. Die gesamte offizielle Sen1Floods11-Benchmark wird nicht beansprucht.

Quellen:

- [Sen1Floods11, Originalrepository](https://github.com/cloudtostreet/Sen1Floods11)
- [Originalpublikation, CVPR Workshops 2020](https://openaccess.thecvf.com/content_CVPRW_2020/html/w11/Bonafilia_Sen1Floods11_A_Georeferenced_Dataset_to_Train_and_Test_Deep_Learning_CVPRW_2020_paper.html)
- [Dokumentation der L2A-Verarbeitung](https://sentiwiki.copernicus.eu/web/s2-processing)

## Eigener Wasserklassifikator

Die 16 Eingangsmerkmale sind sechs Reflektanzbänder, NDWI, MNDWI, NDVI, NDBI, zwei AWEI-Varianten, zwei Helligkeitsmittelwerte, Grün-SWIR-Differenz und SWIR-Verhältnis. Es werden keine Koordinaten als Merkmal verwendet. Indexformeln sind explizit in `features.py` implementiert.

Zwei kleine Modelle werden aus den Referenzstichproben trainiert:

- Histogram Gradient Boosting: 180 Iterationen, maximal 23 Blätter, Lernrate 0.07, Mindestblattgröße 35, L2-Regularisierung 1.
- Extra Trees: 100 Bäume, maximale Tiefe 17, Mindestblattgröße 12.

Jeder Chip hat im Fit dasselbe Gesamtgewicht. Die natürliche Klassenhäufigkeit innerhalb des Chips wird erhalten. Ein logistischer Kalibrator lernt die Zuordnung von Rohscores zu Wasserwahrscheinlichkeiten auf Paraguay. Modell und Entscheidungsschwelle werden ausschließlich auf Spanien gewählt. Erst danach werden die Testlabels verwendet.

Ausgewählt wurde Histogram Gradient Boosting. Auf den zurückgehaltenen Referenzstichproben:

| Verfahren | F1 |
|---|---:|
| Ursprüngliche MNDWI-Schwelle 0.15 | 84,72 % |
| Auf Spanien optimierte MNDWI-Schwelle | 89,03 % |
| Eigener trainierter Klassifikator | 93,66 % |

Der trainierte Klassifikator erreicht dabei 97,98 % Präzision und 89,72 % Recall. Der Brier-Score beträgt 0,0132, der über zehn Scoreintervalle berechnete Kalibrierungsfehler 0,0096. Diese Ergebnisse bewerten den **Pixelklassifikator auf klaren, homogen annotierten Referenzpixeln**. Sie sind kein Genauigkeitsnachweis der kompletten nachbearbeiteten Brasilien-Flutkarte, der Zukunftsprognose oder der Tradingregel.

Der Kalibrierungstransfer nach Brasilien ist nicht garantiert. Wasserscores zwischen 0.2 und 0.8 werden als explorative Unsicherheitsebene gezeigt. Sie sind kein formales Konfidenzintervall.

## Vorverarbeitung und Referenz

Die Reflektanzkorrektur ist von der Sentinel-2-Processing-Baseline abhängig. Historische Produkte vor PB 04.00 haben bei fehlenden expliziten Metadaten keinen additiven Offset; neuere Produkte erhalten den Offset −0.1 bei Skalierung 0.0001. Vorhandene `raster:bands`-Metadaten haben Vorrang. Ein Test prüft diese Unterscheidung.

SCL 0, 1, 3, 8, 9, 10 und 11 sowie fehlende/unplausible Reflektanzen sind ungültig. Der Rand wird um einen Pixel erweitert. SCL 2 wird bewusst nicht pauschal verworfen; dunkle Flächen werden durch den spektralen Klassifikator behandelt. Topographische Schatten können daher verbleibende Fehler erzeugen.

Die Referenz verwendet gültige Beobachtungen zwischen 21 und 150 Tagen vor dem jeweiligen Prognosezeitpunkt. Pro Pixel werden der Median des Wasserscores und die Häufigkeit erkannter Wasserbeobachtungen berechnet. Mindestens zwei historische Beobachtungen müssen vorliegen. Der 21-Tage-Abstand soll verhindern, dass die laufende Überflutung sofort zur Normalreferenz wird; dies ist eine Modellannahme, kein bewiesener optimaler Wert.

Neue Wasserflächen müssen über der gewählten Modellschwelle liegen, von der historischen Referenz abweichen und außerhalb der Referenzwasserfläche liegen. Zusammenhangsprüfung: mindestens vier Pixel (0,16 ha) und ein Kern mit Wasserscore ≥0.8 beziehungsweise mindestens der gewählten Entscheidungsschwelle. Damit bleiben kleinere klare Wasserobjekte erhalten als im pauschalen 1-ha-Filter der V1. Diese Nachbearbeitung ist nicht separat anhand von Feldlabels validiert.

## Zeitliche Prognose

Die historische Canoas-Bildfolge stammt aus Januar 2023 bis Juni 2024. Die Szenenauswahl erfolgt nach einer festgelegten maximalen Kachelbewölkung und zeitlichem Mindestabstand; die komplette Auswahl und Ausfälle stehen im Serienmanifest. Eine geringe Kachelbewölkung garantiert keine wolkenfreie Teilfläche. Alle Merkmale respektieren die lokale Gültigkeitsmaske.

Zeitmerkmale: aktueller und vorheriger Wasserscore, tägliche Veränderung, historische Referenz, historische Wasserhäufigkeit, Abweichung von normal, lokale Wasserscores, Entfernung zu Wasser/trockenen Flächen/Referenzwasser, Vorhersagehorizont, Abstand der letzten Aufnahme und Jahreszeit. Es gibt keine Zukunftsinterpolation und keine Verwendung später beobachteten Wetters.

Das Zeitmodell ist ein kleiner Histogram-Gradient-Boosting-Klassifikator. Der Zielwert ist die spätere Wasserklassifikation des eingefrorenen spektralen Modells. Das sind **Proxy-Labels**, keine unabhängigen Referenzbeobachtungen einer Überflutung oder Betriebsunterbrechung.

- Training: historische Aufnahmepaare bis Oktober 2023.
- Validierung: November 2023 bis März 2024.
- Horizonte im Training: 10–20 Tage, nächstes verfügbares Paar zu 15 Tagen.
- Feste Kandidaten für die Mischung mit Persistenz: 0 %, 25 %, 50 %, 75 %, 100 % Zeitmodellanteil. Gewicht und Schwelle werden ausschließlich auf den historischen Validierungsdaten gewählt.
- Die aktive Methode bleibt Persistenz, falls sie auf der Validierung gewinnt oder der gewählte Zeitkandidat die spätere Freigabeprüfung nicht besteht.

Das erste Experiment verfügte nur über zwei brauchbare Trainingspaare. Es schlug Persistenz auf Validierung, verlor jedoch in der Mai-Fallstudie. Dieser Befund wird in `artifacts/forecast_report_initial.json` aufbewahrt. Anschließend wurde die frühere Bildhistorie erweitert. **Die Mai-Fallstudie ist deshalb ein bereits betrachteter Entwicklungsfall und kein unberührter Abschlusstest der erweiterten Version.** Sie bleibt aus Fit und historischer Auswahl ausgeschlossen.

Das zusätzliche Aufnahmepaar vom 2. bis 22. Juni 2024 wurde vor dem erweiterten Training als abschließende zeitliche Prüfung festgelegt. Es betrifft dieselbe Region und den Nachlauf desselben Hochwassers. Auch dieses Paar belegt keine Generalisierung auf unabhängige Regionen oder Flutereignisse. Die Ergebnisse stehen in `artifacts/forecast_report.json` und `MODELLBERICHT.md`.

Die Karte „Tag 15“ zeigt die Prognose vom 6. Mai für den 21. Mai. „Prognosefehler“ vergleicht sie mit späteren Proxy-Wasserkarten. Die Anwendung zeigt außerdem aktuelle und prognostizierte Standortflächen getrennt. Der Standort-Prüfindex und die AGCO/SPY-Regel bleiben bewusst explizite Heuristiken; es wird keine gelernte Wahrscheinlichkeit für einen Betriebsausfall behauptet.

## Reproduzieren

Python 3.12–3.14 empfohlen. Der mitgelieferte sklearn-Artefaktstand benötigt scikit-learn 1.9.1. Modellgewichte werden lokal mit Joblib geladen; nur eigene oder vertrauenswürdige Artefakte laden.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Für die Modellbildung:

```bash
# Referenzlabels und passende L2A-Bilddaten
python prepare_v2.py benchmark --chips-per-event 8
python train_classifier.py

# Historische Bildfolge und kausale Prognose
python prepare_v2.py series
python train_forecast.py

# Tests und exportierte Ergebnisse
python -m unittest discover -s tests -v
python app.py --export
```

Das Downloadpaket enthält die Laufzeitdaten, Modellartefakte, Referenzstichproben, Zeitmodell-Trainingsstichproben und vorberechneten Wasserscores. Historische Rohbilder außerhalb der drei Demoaufnahmen können zum Begrenzen der Paketgröße fehlen und werden durch `prepare_v2.py series` wiederbeschafft. Der vollständige Forschungsstand im Projektordner enthält sie. Probabilitätscaches werden über den SHA-256-Hash des Klassifikators geprüft und nach einem veränderten Klassifikator neu berechnet.

`requirements-lock.txt` dokumentiert die hier verwendeten Versionen. Kleine numerische Abweichungen bei erneutem Fit auf anderen Plattformen sind möglich.

## Grenzen, die wir weiterhin prüfen müssen

- Unabhängige, zeitlich passende Referenzpolygone für die Brasilien-Fälle.
- Mehr vollständig unabhängige zeitliche Testereignisse und Regionen.
- Unsicherheit und Kalibrierung innerhalb bebauter Industrieflächen.
- Nutzen gegenüber Wetter, Pegeln und zeitgenössischen Nachrichten.
- Tatsächliche Unterbrechungs-, Wiederanlauf- und Marktdaten als getrennte Zielgrößen.

Die Anwendung und unsere eigenen Modellskripte stehen unter MIT. Copernicus, OSM, Referenzlabels und Börsenkurse behalten ihre jeweiligen Rechte und Bedingungen. Das Referenzrepository stellt die Daten öffentlich bereit und verlangt wissenschaftliche Zitierung; eine umfassende Weiterverteilungslizenz für alle abgeleiteten Referenzdateien wurde hier nicht verifiziert.
