# Design Integration Guide

This documents the frontend redesign of Flood Alpha's single-page dashboard
(`web/index.html`), why it's structured the way it is, and how to keep
extending it as the Python backend (`model.py`, `model_v2.py`, `market.py`,
`app.py`) continues to evolve independently.

> **Note on revisions:** this redesign went through two passes. The first
> restyled the original dark dashboard's layout in place (sticky section nav,
> stacked panels, boxed KPI tiles) — it read as "the same site, new colors."
> This document describes the **second pass**, which changed the composition
> itself: a light editorial palette, a map-dominant workspace with a
> contextual side rail, a timeline scrubber in place of a tab row, and
> evidence folded into the narrative with a collapsible methodology drawer.
> The three-layer file split and the data/API contracts are unchanged across
> both passes.

## What changed, and what didn't

**Backend: one small, additive change.** `app.py` gained one new route,
`/static/<file>`, that serves the files under `web/static/` (CSS/JS only,
path-traversal-checked, 404 on anything else). Nothing in `model.py`,
`model_v2.py`, `market.py`, `features.py`, `temporal.py`, or any analytical
logic was touched. The existing API contract (`/api/analysis`,
`/api/validation`, `/api/trading-plan`, `/api/event-study`, `/image/*`,
`/export/*`) is byte-for-byte unchanged. All 24 existing tests in `tests/`
pass without modification.

**Frontend: restructured and reskinned, logic preserved.** The previous
`web/index.html` was a single ~30KB file mixing markup, ~500 lines of CSS,
and ~25 inline JS functions. It's now:

```
web/
  index.html          — markup only: top bar, hero, workspace, exposure table, drawer, footer
  static/
    styles.css        — design tokens + component styles (light editorial palette)
    i18n.js            — translation dictionary + t()/tf()/bt() helpers
    data.js            — all backend communication (data layer)
    app.js             — rendering, canvas map, interaction (app + presentation)
```

Every original JS function (`load`, `renderStats`, `renderTable`, `focus`,
`draw`, `setMode`, `evaluate`, `loadMarket`, `loadPlan`, pan/zoom handlers)
still exists with the same behavior — they were moved and given access to
`t()`/`fetchX()` helpers, not rewritten. The German↔English language toggle
(added in a prior pass) works identically, now living in `i18n.js`.

## Why these specific calls

- **Light editorial palette this time, not the dark institutional one from
  pass one.** The brief for this pass explicitly asked for a different
  product experience, not a darker/lighter restyle of the same shape — see
  the palette tokens at the top of `styles.css` (`--bg`, `--surface`,
  `--accent` etc.). The map itself stays a dark "window" (`--map-bg`)
  regardless of page theme: satellite RGB imagery and the canvas overlays
  still read best against dark, so the map is a deliberately dark panel
  embedded in an otherwise light page, rather than the whole page going dark.
- **No external fonts or icon CDNs — still true in this pass.** The
  product's own README and footer state "no API key, fully offline" as a
  core guarantee; a Google Fonts request would quietly break that on every
  page load. The hero headline uses a local-stack serif (`--font-serif`:
  `ui-serif, Georgia, …`) for an editorial feel without any network request;
  everything else uses the system sans stack.
- **Map/legend/canvas colors are intentionally untouched, again.** The cyan
  "new water," orange "site," purple "forecast," and green/orange/red
  hit/false-alarm/miss colors are a shared encoding across three places:
  pixels baked into backend-rendered PNGs (`model_v2.py`'s `png()`), the
  canvas-drawn site/road overlays in `app.js`, and the on-screen legend
  swatches. Restyling one without the other two would make the legend lie
  about what's on the map. These are instrument-reading colors, not UI
  chrome, so they were kept as-is across both redesign passes.
- **Map-dominant workspace with a contextual rail, not a nav bar over
  stacked sections.** The first pass kept the original's shape (sticky
  multi-tab nav, independent full-width panels for map / table / market /
  methodology) and just reskinned it — which is why it still read as the
  same product. This pass removes the section nav entirely: there's one
  continuous page, the map is the largest element on it, and the two things
  the brief asked to be visually connected — a selected site and the AGCO/SPY
  market case study — live stacked in the same right-hand rail (`.rail` in
  `index.html`), not in separate sections a reader has to scroll between.
- **A timeline scrubber instead of a row of mode tabs.** `before` (Apr 21),
  `event` (May 6), and `future` (May 21) are genuinely points in time, so
  they're presented as a dated scrubber (`.timeline`); the four derived
  analytical overlays (water score, V1 rule, forecast, forecast error) are a
  separate row of `.chip` toggles below it. Both groups still just set the
  same `data-mode` attribute `setMode()` already reads — this is a markup
  and CSS change, not a logic change.
- **Evidence folded into the narrative, full detail in a closed-by-default
  drawer.** The classifier F1 numbers now appear two ways: a one-line
  credibility statement under the hero headline (`#heroEvidence`, built in
  `renderModelInfo()`), and the full breakdown inside the `<details
  class="drawer">` at the bottom, collapsed on load. A first-time viewer
  gets the credibility signal immediately without a boxed "model validation"
  panel competing with the map for attention; a judge who wants the full
  rigor can expand it.

## The three-layer split (and why it matters for your workflow)

- **`data.js` (data layer):** owns every `fetch()` call and endpoint path.
  If a teammate adds a new backend endpoint (say, `/api/weather-overlay`),
  they add one function here (`fetchWeatherOverlay(q)`) — nothing else needs
  to know a URL.
- **`i18n.js` (content layer):** every user-visible string, in German and
  English, plus the small `BACKEND_TEXT_KEY`/`SIGNAL_KEY`/`ACTION_KEY` maps
  that translate the fixed set of natural-language strings the Python
  backend returns (e.g. `model.py`'s `signal` field, `market.py`'s `action`
  field). If the backend's wording changes, update the map here — no HTML
  or rendering logic changes.
- **`app.js` (application/presentation layer):** DOM rendering, the canvas
  map, and event wiring. It imports from the two layers above and contains
  no fetch URLs and no hardcoded copy.

This mirrors the "Version 1 → Version 2 (this redesign) → Version 3
(teammate's new feature)" scenario directly: a teammate's new analytical
feature almost always means a new backend field, which means a one-line
addition to `data.js` (if it's a new endpoint) and a render function in
`app.js` that reuses the existing CSS classes — not a rewrite of the page.

## Adding a new feature to the redesigned UI

Say a teammate adds rainfall-gauge data to `model_v2.py`'s `analyze()`
response as `result["gauge_series"]`. To surface it:

1. **Data layer** — nothing needed if it rides along in `/api/analysis`
   (already fetched by `load()` in `app.js`). If it's a new endpoint, add
   `export const fetchGauges = q => apiGet('/api/gauges?' + q);` to `data.js`.
2. **Content layer** — add the display strings to both `de` and `en` blocks
   in `i18n.js` (e.g. `gauge_title`, `gauge_hint`).
3. **Presentation layer** — decide where it belongs in the narrative, then
   reuse an existing component class rather than inventing one:
   - Belongs with the map/selection? Add a `.rail-block` to `.rail` in
     `index.html`: `<div class="rail-block"><h4
     data-i18n="gauge_title">…</h4><div id="gauges"></div></div>`. It
     inherits the rail's border/padding/typography automatically.
   - Is its own evidence/reference material? Add it inside the `<details
     class="drawer">` body, e.g. another `.source-block` in `.source-grid`.
   - Is a new top-level dataset in its own right (comparable to the exposure
     table)? Copy the `.exposure` section's structure (`.exposure-head` +
     a content block + optional `.table-foot`) as a new `<section>` between
     `.workspace` and the drawer.
4. **Wire it up** — in `app.js`, read `data.gauge_series` inside the
   existing `load()` flow (it already has the full analysis response) and
   render into `#gauges` using `t()`/`tf()` for any copy, following the
   pattern in `renderModelInfo()` or `renderProvenance()`.

There is no router or section nav to register a new view with — the page is
one continuous document, so a new section just needs to be placed in reading
order and styled with the existing component classes above.

## Known integration risks

- **`/static/*` route is new.** If `web/static/` is ever renamed or the
  three JS files are merged, update the `<script type="module">` /
  `<link>` paths in `index.html` — there's no build step to catch a typo.
- **`i18n.js`'s `BACKEND_TEXT_KEY` map is string-keyed on exact backend
  text.** If someone edits the wording of `model.py`'s `signal` values,
  `market.py`'s `action` strings, or the `limitations` strings in
  `model_v2.py`/`market.py`, the old string silently stops matching and the
  UI falls back to showing the raw (German) backend string untranslated in
  English mode. Search `i18n.js` for the old string and update the map
  alongside any such backend wording change.
- **`__DEFAULT_THRESHOLD__` placeholder** in `index.html` (two occurrences)
  is still substituted by `app.py`'s naive `.replace()` at serve time —
  unchanged from before. Don't rename it without updating `app.py`.
- **Canvas-drawn colors must stay in sync with the legend and with
  `model_v2.py`'s `png()` output** (see above) — the three are coupled by
  convention, not by shared code.
- **`data-mode` is shared between two visually distinct control groups** —
  the `.timeline`'s `.tpoint` buttons (temporal: before/event/future) and
  the `.layerchips`' `.chip` buttons (derived overlays). `setMode()` in
  `app.js` treats every `[data-mode]` element identically. A new overlay
  mode just needs a `.chip` with the right `data-mode` value and a case
  added to `setMode()`'s `stamp`/`legendMap` lookups — no changes to the
  timeline.
- **Don't hardcode pixel budgets for text that gets translated.** The
  map's reset button is icon-only below 700px specifically because its
  German label ("Ansicht zurücksetzen") is much wider than the English one
  ("Reset view") and a fixed `calc()` reserve for the stamp text broke for
  one language and not the other. If you add more controls near translated
  text, prefer `flex-wrap`/icon-only fallbacks over a magic-number budget.

## Recommended git workflow for ongoing work

- Backend work (new models, data sources, endpoints) and frontend work
  (new panels, copy, layout) now touch almost entirely disjoint files —
  `model_v2.py`/`market.py`/`app.py`'s route list vs. `web/static/*.js` and
  `index.html` — so parallel work should merge cleanly.
- When adding a backend field that needs UI surface, land the backend
  change first, then the three-step UI addition above as a follow-up commit
  — keeps diffs reviewable and avoids a half-wired feature in one commit.
- Avoid reformatting `app.py`'s existing routes or `model_v2.py`/`market.py`
  in the same commit as a frontend change; it makes it hard to tell which
  edits are cosmetic and which affect the analysis.

## Example: the "Alt-Data Signal Explorer" (quant_demo.py)

A worked example of the integration pattern above, and a flag for anyone who
finds this section confusing: it's an illustrative demo, intentionally
unrelated to the flood/market analysis, placed right below the satellite map.

- **`quant_demo.py`** is a standalone module (not imported by `model.py`,
  `model_v2.py`, or `market.py`) exposing three pure functions —
  `quant_proxies`, `quant_sensor`, `quant_signal` — each returning a plain
  dict, mirroring `market.py`'s style.
- **`app.py`** gained one `if` branch dispatching three GET routes
  (`/api/quant/proxies`, `/api/quant/sensor`, `/api/quant/signal`) to those
  functions — same pattern as every other route, no new method handling.
- **Frontend**: a new `<section class="quant-demo">` in `index.html`
  (placed after `.workspace`, before `.exposure` — "below the satellite
  image" per the request that produced it), new component classes appended
  to the end of `styles.css`, new `quant_*` keys appended to `i18n.js`'s
  `de`/`en` blocks, and its own `web/static/quant.js` module — deliberately
  **not** merged into `app.js`, since it shares no state with the flood
  analysis (see the "no shared state" note at the top of `quant.js`). It
  only imports `t`/`tf` from `i18n.js`.
- **Why it's clearly labeled**: the source file this was built from
  presented fabricated "sensor" data (synthesized from the real price plus
  noise) and a random coin-flip trading signal as if they were real
  analysis. That directly conflicts with this project's existing standard —
  every other probability, F1 score, and limitation note in the app is
  either real or explicitly flagged as heuristic/hypothetical. `quant_demo.py`
  labels every response `"simulated": true` with a `note`/`rationale`
  field saying what's fabricated, and the UI surfaces that as a persistent
  "SIMULATED · NOT REAL" tag plus an upfront disclaimer banner. **If you
  extend this section, keep that labeling** — don't let a "simulated" value
  go unlabeled in the UI.
- **Only 5 tickers are supported** (`quant_demo.SUPPORTED_TICKERS`), each
  with hand-written proxy narratives. The original source script used
  `yfinance` to look up arbitrary tickers' sector/industry; that dependency
  was dropped in favor of the same lightweight `requests`-based Yahoo chart
  API call `market.py` already uses, at the cost of not supporting
  freeform tickers. To add a 6th ticker, add its proxies to
  `COMPANY_SPECIFIC_PROXIES` and its name to `COMPANY_NAMES` in
  `quant_demo.py`, and its symbol to `SUPPORTED_TICKERS`.
- **This is the one part of Flood Alpha that needs live internet after
  install** — `_fetch_real_stock_data()` calls Yahoo Finance at request
  time, every time a ticker is scanned. This is called out in the UI
  disclaimer; don't remove that line if you touch this section.
