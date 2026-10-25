// Translation layer. Pure data + lookup helpers — no DOM/network code.
// `BACKEND_TEXT_KEY` maps the small, fixed set of natural-language strings the
// Python backend returns (model.py / model_v2.py / market.py) onto translation
// keys, so the UI can render them in the selected language without touching
// the backend (see DESIGN_INTEGRATION.md).

export const T = {
de:{
title:`Flood Alpha · Canoas 2024`,
pill:`ECHTE DATEN · LOKAL & OFFLINE`,
btn_csv:`Standorte ↓ CSV`,btn_json:`Analyse ↓ JSON`,
hero_eyebrow:`Canoas, Brasilien / historische Fallstudie 2024`,
hero_h1:`Canoas, Brasilien — Flut im Mai 2024`,
hero_lede:`Ein eigener, gelernter Klassifikator erkennt Wasser aus sechs Spektralbändern. Ein separat trainiertes Zeitmodell wird gegen Persistenz geprüft — nur eine bestandene Modellprüfung erlaubt seine Freigabe.`,
hero_evidence_loading:`Modellbeleg wird geladen …`,
hero_evidence:`Beleg: eigener Klassifikator F1 {f1} gegenüber {base} Basislinie (zurückgehaltene Ereignisse) · {gate}`,
hero_gate_pass:`Zeitmodell freigegeben`,hero_gate_fail:`Zeitmodell zurückgewiesen, Persistenz aktiv`,
stat1_label:`Neue erkannte Wasserfläche`,stat1_small:`gegenüber der historischen Referenz`,
stat2_label:`Direkt exponierte Standorte`,stat2_small:`≥ 5 % der erfassten Fläche`,
stat3_label:`Trockene Standorte, nasses Straßenumfeld`,stat3_small:`Prüfhinweis, kein Sperrungsnachweis`,
stat4_label:`Auswertbare Vergleichsfläche`,stat4_small:`Wolkenmaske + gültige Historie`,
t_before_date:`21. Apr`,t_event_date:`06. Mai`,t_future_date:`21. Mai`,
t_before:`vorher`,t_event:`Signal`,t_future:`Ergebnis`,
tab_probability:`Wasserscore`,tab_legacy:`V1-Regel`,tab_forecast:`Tag 15 · Prognose`,tab_error:`Prognosefehler`,
map_canvas_al:`Interaktive Satellitenkarte mit Industriestandorten`,zoomin_al:`Vergrößern`,zoomout_al:`Verkleinern`,reset_btn:`Ansicht zurücksetzen`,map_hint:`Scrollen: Zoom · Ziehen: Verschieben · Standort anklicken`,
controls_summary:`Analyseparameter anpassen`,
label_threshold:`Wasser-Entscheidungsschwelle`,label_delta:`Score-Anstieg gegenüber Referenz`,label_radius:`Straßenumfeld`,
hint_controls:`Wasserscore aus trainiertem Modell mit separater Kalibrierung. Zusammenhängende Flächen ab 4 Pixeln mit sicherem Kern werden erhalten. Brücken und Tunnel sind von der Straßenexposition ausgenommen.`,
chk_water:`Erkanntes Wasser einblenden`,chk_uncertain:`Unsichere Wasserscores (0.2–0.8)`,chk_road:`Nasse Straßenabschnitte`,chk_site:`Industriestandorte`,
status_init:`Echte Daten werden verarbeitet …`,
rail_selection_title:`Standortauswahl`,
focus_empty:`Klicke auf eine Fläche auf der Karte oder eine Zeile in der Liste unten. Direkte Exposition und das Straßenumfeld werden getrennt ausgewiesen.`,
rail_market_title:`Marktfallstudie · AGCO / SPY`,
market_p1:`AGCO nennt Canoas im Geschäftsbericht 2023 als Regionalzentrale und Produktionsstandort. Die historische OSM-Fläche wird direkt zugeordnet; es werden keine Zulieferbeziehungen erfunden.`,
tradeplan_init:`Regel wird geprüft …`,
reveal_btn:`15 Tage vorspulen → Prognose prüfen`,
evaluation_init_hint:`Die spätere Aufnahme wird ausschließlich zur Auswertung geöffnet. Kein Zukunftsbild fließt in die Eingangsmerkmale ein.`,
market_link:`Unternehmensquelle: SEC / 10-K ↗`,
exposure_title:`Exposure-Rangliste`,exposure_desc:`Alle erfassten Industriestandorte, sortiert nach Prüfindex.`,
site_search_ph:`Standort suchen …`,site_search_al:`Standort suchen`,
th_site:`Standort / historische OSM-Geometrie`,th_wet:`Heute nass`,th_forecast:`Tag 15 · Prognose`,th_road:`Straßenumfeld`,th_index:`Prüfindex¹`,
footnote_index:`¹ Heuristischer Index = 70 × Flächenanteil + 30 × Anteil nasser Straßenpixel. Keine Ausfallwahrscheinlichkeit und kein Kauf-/Verkaufssignal.`,
drawer_eyebrow:`Beleg & Methodik`,
bottom_notice:`<b>V2:</b> eigener trainierter Wasserklassifikator, sechs Spektralbänder und zehn abgeleitete Merkmale, separate Kalibrierung und geographischer Test; historische Referenz aus mehreren Bildern; zeitliches Modell mit separatem Training, Validierung und späterem Test. <b>Grenzen:</b> Fachlich nachbearbeitete Referenzlabels können Fehler enthalten. Die Zeitprognose nutzt abgeleitete Wasserkarten als Ziel. Betriebsunterbrechungen, Lieferketten und Kurswirkungen sind weiterhin nicht gelernt.`,
src1_summary:`Datenherkunft und Zeitstempel`,
src1_p1:`Enthält modifizierte Copernicus Sentinel-Daten 2024. Quelle: ESA/Copernicus, bereitgestellt über Microsoft Planetary Computer. Geometrien © OpenStreetMap-Mitwirkende, ODbL 1.0.`,
src1_p2:`Die Aufnahmedaten belegen keinen damaligen Veröffentlichungszeitpunkt. Der heutige Archivabruf rekonstruiert keine historische Handelslatenz.`,
src2_summary:`Methode und Grenzen`,
src2_p1:`Die Klassifikation verwendet B02/B03/B04/B08/B11/B12 sowie NDWI, MNDWI, NDVI, NDBI, AWEI und weitere spektrale Merkmale. L2A-Oberflächenreflektanzen werden auch für die Trainingschips neu geladen, um einen L1C-/L2A-Domänenwechsel zu vermeiden.`,
src2_p2:`Kalibrierung: separates Ereignis Paraguay. Modellauswahl und Entscheidungsschwelle: Spanien. Unberührter Klassifikationstest: Bolivien und USA. Referenzlabels stammen aus Sen1Floods11 und wurden von Fachleuten nachbearbeitet; sie sind keine unabhängigen Feldmessungen.`,
src2_p3:`Die zeitliche Prognose lernt aus historischen Aufnahmepaaren mit 10–20 Tagen Abstand. Eingaben enthalten nur zum Prognosezeitpunkt bekannte Bilder und Zeitabstände. Vorhersageziel sind spätere Klassifikator-Wasserkarten (Proxy-Labels). Der Mai 2024 bleibt vom zeitlichen Training und der Modellauswahl getrennt, wurde aber im ersten Experiment bereits betrachtet. Ein zusätzliches Juni-Paar wurde vor dem erweiterten Training als abschließende zeitliche Prüfung festgelegt.`,
src2_p4:`Unsichere Wasserscores werden als eigene Ebene gezeigt. Die Übertragung der Kalibrierung auf Brasilien ist nicht garantiert. Standort-Prüfindex und Tradingregel bleiben explizite Heuristiken. Nasse Straßen beweisen weder Sperrungen noch fehlende Alternativrouten.`,
footer1:`FLOOD / ALPHA · Python + echte Erdbeobachtung`,footer2:`Kein API-Key · keine externen Kartenbibliotheken · Offline-Demo`,
err_generic:`Fehler – Details oben.`,img_load_fail:`Bild konnte nicht geladen werden: `,
status_computing:`Analyse wird berechnet …`,status_computed:`Berechnet · {n} historische Standorte`,
site_approx_suffix:` · ungefähre Lage`,sitecount_label:`{n} Standorte`,
model_classifier_label:`Eigener Klassifikator · F1`,model_oldrule_label:`Alte MNDWI-Regel · F1`,model_tuned_label:`Optimierte MNDWI-Regel · F1`,model_refchips_label:`Referenzchips / Stichprobenpixel`,
model_hint:`Testereignisse: {events}. Länderereignisse bleiben vom Training getrennt. Fachlich nachbearbeitete Labels, keine Feldmessungen. Referenz vor der Mai-Flut: {hist} frühere Aufnahmen. Zeitprognose trainiert auf {pairs} historischen Aufnahmepaaren.`,
model_gate_passed:`Zeitmodell: Freigabeprüfung bestanden`,model_gate_failed:`Zeitmodell zurückgewiesen · Persistenz bleibt Standard. Die Klassifikation ist unabhängig davon verbessert.`,
prov_role_before:`Vorher`,prov_role_event:`Signal`,prov_role_future:`Späterer Vergleich`,prov_osm_label:`OSM-Snapshot:`,prov_download_label:`Archivabruf:`,
focus_point_badge:`OSM-Punkt · 60 m Näherung`,focus_area_badge:`OSM-Fläche · Stand April 2024`,focus_direct_label:`Direkt erkannt`,
focus_hint:`{forecast}. Unsichere aktuelle Wasserscores: {u}. Dies ist ein Expositionshinweis, keine bestätigte Betriebsunterbrechung.`,
focus_coverage:`Auswertbare Standortfläche: {c}.`,focus_open_link:`Originalstandort öffnen ↗`,
forecast_enough:`Am 21. Mai sind {pct} % der auswertbaren Fläche als Wasser prognostiziert`,forecast_insufficient:`Zu wenig belastbare Beobachtungen`,
signal_datagap:`Datenlücke`,signal_direct:`Prüfen: direkt exponiert`,signal_road:`Prüfen: Umfeld exponiert`,signal_none:`Kein Bildsignal`,
action_trigger:`Prüfposition: Short AGCO / Long SPY`,action_none:`Keine Position nach der festgelegten Regel`,
validation_limitations:`Klassifikation: zurückgehaltene Länderereignisse. Zeitliche Prognose: Proxy-Wasserkarten statt Feldmessungen, ein Testereignis. Keine bestätigten Betriebsausfälle oder Tradingvorteile.`,
market_limitations:`Eine rückblickend ausgewählte Fallstudie. Kein Nachweis kausaler Kurswirkung oder handelbaren Alphas; kein News-/Wettervergleich. Historische Datenverfügbarkeit und Leihbarkeit nicht belegt. Finanzierung, variable Leihsätze, Steuern und tatsächliche Ausführung nicht modelliert.`,
backend_error_generic:`Verarbeitung fehlgeschlagen. Details im Python-Terminal.`,
eval_active:`Zeitmodell aktiv`,eval_persistence_active:`Persistenz aktiv: Zeitmodell hat die spätere Prüfung nicht bestanden`,eval_coverage:`{v} % Fläche auswertbar.`,
evalgrid_active_f1:`Aktive Prognose · F1`,evalgrid_persistence_f1:`Persistenz · F1`,evalgrid_precision:`Prognose · Präzision`,evalgrid_recall:`Prognose · Recall`,
eval_proxy_note:`Die Zielkarten sind Proxy-Labels des eingefrorenen Wasserklassifikators. Die Metriken belegen keine Betriebsausfälle oder Aktienprognosen.`,
eval_rejected_notice:`<b>Zurückgewiesener Kandidat:</b> F1 {f1} % in dieser Karte. Zusätzliches Juni-Paar: Kandidat {jf1} %, Persistenz {jp1} %. Deshalb keine Freigabe des Zeitmodells.`,
market_eyebrow3:`Hypothetische Fallstudie · Ergebnis aufgedeckt`,market_net_label:`Netto / 2 USD Bruttoexposition`,market_agco_label:`AGCO · Total Return`,market_svg_al:`Bruttorendite der hypothetischen Position`,
market_hint2:`Linie: tägliche Bruttorendite. Kennzahl oben: nach fixen Transaktions- und Leihkosten. SPY-Total-Return: {spy} %. {limitations}`,
market_hint3:`Quelle: Yahoo Finance, {date}. USD, tägliche Open-/Close-Kurse; Dividenden als Cash.`,
reveal_loading:`Spätere Aufnahme wird geladen …`,reveal_done:`Ergebnis aufgedeckt · Parameter weiter explorierbar`,reveal_retry:`Erneut aufdecken`,
stamp_before:`SENTINEL-2 / 21 APR 2024 / VOR DEM EREIGNIS`,stamp_event:`SENTINEL-2 / 06 MAY 2024 / PROGNOSEZEITPUNKT`,stamp_future:`SENTINEL-2 / 21 MAY 2024 / SPÄTERE BEOBACHTUNG`,
stamp_probability:`V2 / GELERNTER WASSERSCORE / ROT: NIEDRIG · CYAN: HOCH`,stamp_legacy:`V1 / FESTE MNDWI-REGEL / ORANGE: ERKANNTES WASSER`,
stamp_forecast:`PROGNOSE FÜR 21 MAY / PERSISTENZ MIT GELERNTER WASSERERKENNUNG`,stamp_error:`15-TAGE-PROGNOSE / GRÜN: TREFFER · ORANGE: FEHLALARM · ROT: VERPASST`,
legend_error_hit:`Richtig nass`,legend_error_false:`Falsch nass`,legend_error_missed:`Neue Fläche verpasst`,
legend_prob_low:`Niedriger Wasserscore`,legend_prob_high:`Hoher Wasserscore`,legend_forecast_water:`Prognostizierte Wasserfläche`,legend_site:`Standort`,
legend_legacy_water:`V1-Regel: neues Wasser`,legend_event_water:`Neu erkanntes Wasser`,legend_not_evaluable:`Nicht auswertbar`,legend_default_site:`Historischer Standort`,
},
en:{
title:`Flood Alpha · Canoas 2024`,
pill:`REAL DATA · LOCAL & OFFLINE`,
btn_csv:`Sites ↓ CSV`,btn_json:`Analysis ↓ JSON`,
hero_eyebrow:`Canoas, Brazil / historical case study 2024`,
hero_h1:`Canoas, Brazil — the May 2024 flood`,
hero_lede:`A custom trained classifier detects water from six spectral bands. A separately trained temporal model is tested against persistence — only a passed model check allows its release.`,
hero_evidence_loading:`Loading model evidence …`,
hero_evidence:`Evidence: custom classifier F1 {f1} vs. {base} baseline (held-out events) · {gate}`,
hero_gate_pass:`temporal model released`,hero_gate_fail:`temporal model rejected, persistence active`,
stat1_label:`New detected water area`,stat1_small:`relative to the historical reference`,
stat2_label:`Directly exposed sites`,stat2_small:`≥ 5% of mapped area`,
stat3_label:`Dry sites, wet road surroundings`,stat3_small:`Indicative check, not proof of closure`,
stat4_label:`Evaluable comparison area`,stat4_small:`Cloud mask + valid history`,
t_before_date:`Apr 21`,t_event_date:`May 6`,t_future_date:`May 21`,
t_before:`before`,t_event:`signal`,t_future:`result`,
tab_probability:`Water score`,tab_legacy:`V1 rule`,tab_forecast:`Day 15 · forecast`,tab_error:`Forecast error`,
map_canvas_al:`Interactive satellite map with industrial sites`,zoomin_al:`Zoom in`,zoomout_al:`Zoom out`,reset_btn:`Reset view`,map_hint:`Scroll: zoom · Drag: pan · Click a site`,
controls_summary:`Adjust analysis parameters`,
label_threshold:`Water decision threshold`,label_delta:`Score increase vs. reference`,label_radius:`Road surroundings`,
hint_controls:`Water score from a trained model with separate calibration. Connected areas of at least 4 pixels with a confident core are kept. Bridges and tunnels are excluded from road exposure.`,
chk_water:`Show detected water`,chk_uncertain:`Uncertain water scores (0.2–0.8)`,chk_road:`Wet road segments`,chk_site:`Industrial sites`,
status_init:`Processing real data …`,
rail_selection_title:`Site selection`,
focus_empty:`Click an area on the map or a row in the list below. Direct exposure and road surroundings are shown separately.`,
rail_market_title:`Market case study · AGCO / SPY`,
market_p1:`AGCO names Canoas in its 2023 annual report as a regional headquarters and production site. The historical OSM area is mapped directly; no supplier relationships are invented.`,
tradeplan_init:`Checking rule …`,
reveal_btn:`Fast-forward 15 days → check forecast`,
evaluation_init_hint:`The later image is opened exclusively for evaluation. No future image flows into the input features.`,
market_link:`Company source: SEC / 10-K ↗`,
exposure_title:`Exposure ranking`,exposure_desc:`Every mapped industrial site, sorted by check index.`,
site_search_ph:`Search site …`,site_search_al:`Search site`,
th_site:`Site / historical OSM geometry`,th_wet:`Wet today`,th_forecast:`Day 15 · forecast`,th_road:`Road surroundings`,th_index:`Check index¹`,
footnote_index:`¹ Heuristic index = 70 × area share + 30 × share of wet road pixels. Not a failure probability or a buy/sell signal.`,
drawer_eyebrow:`Evidence & methodology`,
bottom_notice:`<b>V2:</b> custom trained water classifier, six spectral bands and ten derived features, separate calibration and geographic test; historical reference from multiple images; temporal model with separate training, validation, and later test. <b>Limitations:</b> Expert-post-processed reference labels may contain errors. The temporal forecast uses derived water maps as its target. Operational disruptions, supply chains, and price effects are still not learned.`,
src1_summary:`Data provenance and timestamps`,
src1_p1:`Contains modified Copernicus Sentinel data 2024. Source: ESA/Copernicus, provided via Microsoft Planetary Computer. Geometries © OpenStreetMap contributors, ODbL 1.0.`,
src1_p2:`The acquisition dates do not prove the actual publication time back then. Today's archive retrieval does not reconstruct historical trading latency.`,
src2_summary:`Method and limitations`,
src2_p1:`Classification uses B02/B03/B04/B08/B11/B12 as well as NDWI, MNDWI, NDVI, NDBI, AWEI, and other spectral features. L2A surface reflectances are also re-fetched for the training chips to avoid an L1C/L2A domain shift.`,
src2_p2:`Calibration: separate event Paraguay. Model selection and decision threshold: Spain. Untouched classification test: Bolivia and USA. Reference labels come from Sen1Floods11 and were post-processed by experts; they are not independent field measurements.`,
src2_p3:`The temporal forecast learns from historical image pairs 10–20 days apart. Inputs contain only images and time gaps known at the forecast time. The prediction target is later classifier water maps (proxy labels). May 2024 remains separate from temporal training and model selection, but was already examined in the first experiment. An additional June pair was fixed as a final temporal check before the extended training.`,
src2_p4:`Uncertain water scores are shown as a separate layer. Calibration transfer to Brazil is not guaranteed. The site check index and trading rule remain explicit heuristics. Wet roads prove neither closures nor missing alternative routes.`,
footer1:`FLOOD / ALPHA · Python + real Earth observation`,footer2:`No API key · no external map libraries · offline demo`,
err_generic:`Error – see details above.`,img_load_fail:`Image could not be loaded: `,
status_computing:`Computing analysis …`,status_computed:`Computed · {n} historical sites`,
site_approx_suffix:` · approximate location`,sitecount_label:`{n} sites`,
model_classifier_label:`Custom trained classifier · F1`,model_oldrule_label:`Original MNDWI rule · F1`,model_tuned_label:`Optimized MNDWI rule · F1`,model_refchips_label:`Reference chips / sample pixels`,
model_hint:`Test events: {events}. Country events remain separate from training. Expert-post-processed labels, not field measurements. Reference before the May flood: {hist} earlier images. Temporal forecast trained on {pairs} historical image pairs.`,
model_gate_passed:`Temporal model: release check passed`,model_gate_failed:`Temporal model rejected · persistence remains the default. Classification is improved independently of this.`,
prov_role_before:`Before`,prov_role_event:`Signal`,prov_role_future:`Later comparison`,prov_osm_label:`OSM snapshot:`,prov_download_label:`Archive retrieval:`,
focus_point_badge:`OSM point · 60 m approximation`,focus_area_badge:`OSM area · as of April 2024`,focus_direct_label:`Directly detected`,
focus_hint:`{forecast}. Uncertain current water scores: {u}. This is an exposure indicator, not a confirmed operational disruption.`,
focus_coverage:`Evaluable site area: {c}.`,focus_open_link:`Open original site ↗`,
forecast_enough:`On May 21, {pct}% of the evaluable area is forecast to be water`,forecast_insufficient:`Not enough robust observations`,
signal_datagap:`Data gap`,signal_direct:`Check: directly exposed`,signal_road:`Check: surroundings exposed`,signal_none:`No image signal`,
action_trigger:`Check position: short AGCO / long SPY`,action_none:`No position under the fixed rule`,
validation_limitations:`Classification: held-out country events. Temporal forecast: proxy water maps instead of field measurements, one test event. No confirmed operational outages or trading advantage.`,
market_limitations:`A retrospectively selected case study. No proof of causal price impact or tradable alpha; no comparison with news or weather. Historical data availability and borrow availability are not verified. Financing, variable borrow rates, taxes, and actual execution are not modeled.`,
backend_error_generic:`Processing failed. See details in the Python terminal.`,
eval_active:`Temporal model active`,eval_persistence_active:`Persistence active: temporal model failed the later check`,eval_coverage:`{v}% area evaluable.`,
evalgrid_active_f1:`Active forecast · F1`,evalgrid_persistence_f1:`Persistence · F1`,evalgrid_precision:`Forecast · precision`,evalgrid_recall:`Forecast · recall`,
eval_proxy_note:`The target maps are proxy labels from the frozen water classifier. The metrics do not demonstrate operational outages or stock forecasts.`,
eval_rejected_notice:`<b>Rejected candidate:</b> F1 {f1}% on this map. Additional June pair: candidate {jf1}%, persistence {jp1}%. Hence no release of the temporal model.`,
market_eyebrow3:`Hypothetical case study · result revealed`,market_net_label:`Net / 2 USD gross exposure`,market_agco_label:`AGCO · total return`,market_svg_al:`Gross return of the hypothetical position`,
market_hint2:`Line: daily gross return. Metric above: after fixed transaction and borrow costs. SPY total return: {spy}%. {limitations}`,
market_hint3:`Source: Yahoo Finance, {date}. USD, daily open/close prices; dividends as cash.`,
reveal_loading:`Loading later image …`,reveal_done:`Result revealed · parameters still explorable`,reveal_retry:`Try reveal again`,
stamp_before:`SENTINEL-2 / APR 21 2024 / BEFORE THE EVENT`,stamp_event:`SENTINEL-2 / MAY 6 2024 / FORECAST TIMESTAMP`,stamp_future:`SENTINEL-2 / MAY 21 2024 / LATER OBSERVATION`,
stamp_probability:`V2 / LEARNED WATER SCORE / RED: LOW · CYAN: HIGH`,stamp_legacy:`V1 / FIXED MNDWI RULE / ORANGE: DETECTED WATER`,
stamp_forecast:`FORECAST FOR MAY 21 / PERSISTENCE WITH LEARNED WATER DETECTION`,stamp_error:`15-DAY FORECAST / GREEN: HIT · ORANGE: FALSE ALARM · RED: MISSED`,
legend_error_hit:`Correctly wet`,legend_error_false:`False wet`,legend_error_missed:`New area missed`,
legend_prob_low:`Low water score`,legend_prob_high:`High water score`,legend_forecast_water:`Forecast water area`,legend_site:`Site`,
legend_legacy_water:`V1 rule: new water`,legend_event_water:`Newly detected water`,legend_not_evaluable:`Not evaluable`,legend_default_site:`Historical site`,
}
};

let lang = (()=>{try{return localStorage.getItem('flood_alpha_lang')}catch(err){return null}})() || 'de';

export const getLang = () => lang;
export function setLang(next){
  lang = next;
  try{localStorage.setItem('flood_alpha_lang', lang)}catch(err){}
}

export const t = k => (T[lang] && T[lang][k]) ?? T.de[k] ?? k;
export const tf = (k, vars) => {
  let s = t(k);
  for (const key in vars) s = s.replaceAll('{'+key+'}', vars[key]);
  return s;
};

const SIGNAL_KEY = {'Datenlücke':'signal_datagap','Prüfen: direkt exponiert':'signal_direct','Prüfen: Umfeld exponiert':'signal_road','Kein Bildsignal':'signal_none'};
const ACTION_KEY = {'Prüfposition: Short AGCO / Long SPY':'action_trigger','Keine Position nach der festgelegten Regel':'action_none'};
const BACKEND_TEXT_KEY = {
'Klassifikation: zurückgehaltene Länderereignisse. Zeitliche Prognose: Proxy-Wasserkarten statt Feldmessungen, ein Testereignis. Keine bestätigten Betriebsausfälle oder Tradingvorteile.':'validation_limitations',
'Eine rückblickend ausgewählte Fallstudie. Kein Nachweis kausaler Kurswirkung oder handelbaren Alphas; kein News-/Wettervergleich. Historische Datenverfügbarkeit und Leihbarkeit nicht belegt. Finanzierung, variable Leihsätze, Steuern und tatsächliche Ausführung nicht modelliert.':'market_limitations',
'Verarbeitung fehlgeschlagen. Details im Python-Terminal.':'backend_error_generic',
};

export const bt = s => {
  if (s == null) return s;
  if (SIGNAL_KEY[s]) return t(SIGNAL_KEY[s]);
  if (ACTION_KEY[s]) return t(ACTION_KEY[s]);
  if (BACKEND_TEXT_KEY[s]) return t(BACKEND_TEXT_KEY[s]);
  return s;
};

export function applyI18n(){
  document.documentElement.lang = lang;
  document.title = t('title');
  document.querySelectorAll('[data-i18n]').forEach(el => { el.innerHTML = t(el.dataset.i18n) });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.dataset.i18nPh) });
  document.querySelectorAll('[data-i18n-al]').forEach(el => { el.setAttribute('aria-label', t(el.dataset.i18nAl)) });
  const btn = document.getElementById('langbtn');
  if (btn){
    btn.textContent = lang === 'de' ? 'EN' : 'DE';
    btn.setAttribute('aria-label', lang === 'de' ? 'Switch to English' : 'Auf Deutsch umschalten');
  }
}
