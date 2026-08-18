# MAPTOOL3 — Implementation (current state)

Single-file browser app: upload lat/lng locations, fetch 20-min and 30-min driving isochrones from ORS API, display on a Leaflet map.

## Tech Stack

- Pure HTML/CSS/JS — no build step, no server
- Leaflet.js (CDN) + OpenStreetMap tiles
- OpenRouteService Isochrone API v2 (api.heigit.org)

## ORS API

- **Endpoint**: POST `https://api.openrouteservice.org/v2/isochrones/driving-car`
- **Headers**: `Authorization: Bearer {key}`, `Content-Type: application/json`
- **Body**: `{ "locations": [[lng, lat]], "range": [1800], "range_type": "time", "units": "m" }` (or `[1200]` for 20-min)
- **Free tier**: ~500 requests/day

## Fetch Strategy

Two separate phases, each in batches of 5 with 15s pause:
1. **Phase 1** — Fetch all 30-min isochrones
2. **Phase 2** — Fetch all 20-min isochrones

Each request fetches a single range to avoid API ambiguity.

## Caching

`localStorage` key `maptool3_isochrones`. Each entry stores `{ iso30, iso20, lat, lng }`. Cache is checked per range before fetching; stale entries (coordinates changed) are skipped.

## Upload Modes

- **Isochrone mode** (default): replaces all data, clears cache, fetches isochrones
- **Dots-only mode** (checkbox): appends dots to existing map, no isochrones

## Rendering

| Layer | Color | Opacity |
|---|---|---|
| 20-min isochrone | Green `#4caf50` | 63% |
| 30-min isochrone | Red `#cc3333` | 33% |
| Location dot | Anthracite `#2a2a2a` | 100% |

## Files

| File | Purpose |
|---|---|
| `index.html` | App (~650 lines) |
| `README.md` | This file |
| `start_server.bat` | Python HTTP server on port 8080 |
