# Modellbericht V2

**Ergebnis:** Die Wasserklassifikation verbessert sich auf zurückgehaltenen Referenzereignissen. Der separat trainierte Zeitkandidat besteht die spätere Prüfung nicht und ist nicht als Standard freigegeben. Die aktive Zukunftsregel bleibt Persistenz.

## Wasserklassifikation

| Verfahren | F1 | Präzision | Recall |
|---|---:|---:|---:|
| V1: MNDWI > 0.15 | 84.72 % | 99.70 % | 73.66 % |
| Auf Validierung optimierte MNDWI-Regel | 89.03 % | 98.98 % | 80.90 % |
| Eigener trainierter Klassifikator | 93.66 % | 97.98 % | 89.72 % |

86 Referenzchips, 423.699 Stichprobenpixel; 80.000 Testpixel aus den komplett zurückgehaltenen Länderereignissen Bolivien und USA. Klare, homogen annotierte 20-m-Blöcke. Keine Feldmessungen; fachlich nachbearbeitete Labels können Index-Bias enthalten. Kein Test der gesamten Brasilien-Flutkarte.

| Testereignis | Gelernter Klassifikator F1 | V1-Regel F1 |
|---|---:|---:|
| Bolivia | 94.13 % | 84.95 % |
| USA | 91.62 % | 83.74 % |

## Zeitprognose: negatives Ergebnis bleibt sichtbar

Der erweiterte Fit verwendet 21 historische Trainingspaare und 10 Validierungspaare. Fit und Schwellenwahl verwenden keine Mai-/Juni-Zielkarten.

| Prüfung | Zeitkandidat F1 | Persistenz F1 |
|---|---:|---:|
| Historische Validierung | 80.82 % | 52.82 % |
| Mai-Entwicklungsfall, 6.–21. Mai | 4.70 % | 81.73 % |
| Zusätzliches Paar, 2.–22. Juni | 15.19 % | 91.05 % |

**Entscheidung:** Kandidat zurückweisen. Alle Werte des Kandidaten bleiben im JSON-Bericht erhalten. Die späteren Prüfungen dienen der Freigabeentscheidung, nicht einer nachträglichen Anpassung der Modellgewichte oder Schwellen. Es wird keine unvoreingenommene Schätzung einer neu ausgewählten Tradingstrategie behauptet.

Die Trainingspaare haben maximal 6.08 % aktuell erkannte neue Wasserpixel in den Stichproben. Im Mai-Fall sind es 17.75 %. Das illustriert die deutlich andere Ereignisgröße; es beweist nicht allein die Ursache des Fehlschlags.

Auch mit mehr Bildpaaren ist ein Zeitmodell nicht automatisch besser. Die Mai-/Juni-Situationen sind nicht ausreichend durch die historischen Paare repräsentiert. Zukünftiger Niederschlag und hydraulische Randbedingungen fehlen. Eine allgemeine Aussage über alle Flutereignisse wäre nicht gerechtfertigt.

Die Zeit-Zielkarten sind Proxy-Labels des eingefrorenen Wasserklassifikators. Die Klassifikations-F1 oben und die Zeit-F1 in dieser Tabelle sind unterschiedliche Aufgaben und dürfen nicht miteinander verglichen werden. Die UI verwendet für ihre Karten zusätzlich räumliche Zusammenhangsfilter; ihre Pixelmetriken können daher leicht von den Roh-Proxywerten hier abweichen.

## Aktiv in der Anwendung

- Trainierter Wasserklassifikator und separate Kalibrierung.
- Historische Referenz aus 13 vor dem Prognosezeitpunkt liegenden Aufnahmen.
- Unsicherheitsebene und Vergleich zur V1-Regel.
- Standortexposition und aktuelle/prognostizierte Flächen getrennt.
- Persistenz als freigegebene Zukunftsregel, zurückgewiesener Zeitkandidat transparent dokumentiert.
- Historische AGCO/SPY-Rechnung bleibt eine hypothetische Fallstudie, keine gelernte Kursstrategie.

Details und Reproduktion: README_V2.md.
