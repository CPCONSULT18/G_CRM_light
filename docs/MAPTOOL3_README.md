# MAPTOOL3 — Isochrone Map

Upload location files (CSV/JSON with lat/lng) and view 20-min (green) and 30-min (red) driving isochrones from OpenRouteService on a Leaflet map.

**Features:**
- Upload isochrone locations or dot-only locations (checkbox toggle)
- Two-phase batch fetching: 30-min isochrones first, then 20-min (5 per batch, 15s pause)
- Isochrone polygons cached in localStorage per address
- ORS API key saved in localStorage

**Usage:**
1. Open `index.html` via HTTP (e.g. `start_server.bat`)
2. Enter your ORS API key and click Save
3. Upload a CSV/JSON with `lat` and `lng` columns (uncheck "Dots only" for isochrones)
4. Isochrones auto-fetch in two phases

**No PLZ data, no gap detection, no circles, no filters.**
