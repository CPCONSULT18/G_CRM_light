import argparse
import csv
import os
import shutil
import time

import requests

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "UpdateBS.csv")
BAK = os.path.join(BASE, "UpdateBS_backup.csv")

ENCODING = "latin-1"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "MAPTOOL3-geocoder/1.0 (office-address-update)"
DELAY = 1.1
MAX_ATTEMPTS = 3
TIMEOUT = 15


def query_nominatim(q):
    params = {
        "q": q,
        "format": "json",
        "limit": 1,
        "countrycodes": "de",
        "addressdetails": 1,
    }
    headers = {"User-Agent": USER_AGENT}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            r = requests.get(NOMINATIM, params=params, headers=headers, timeout=TIMEOUT)
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", "5")) + 1
                print(f"    rate limited, waiting {wait:.0f}s")
                time.sleep(wait)
                continue
            r.raise_for_status()
            results = r.json()
            if not results:
                return None, None
            return float(results[0]["lat"]), float(results[0]["lon"])
        except requests.RequestException as e:
            print(f"    request error: {e}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 * attempt)
    return None, None


def build_query(mode, address, plz, city):
    if mode == "plz":
        return f"{plz}, Deutschland"
    addr = (address or "").strip()
    if addr:
        return f"{addr}, {plz} {city}, Deutschland"
    return f"{plz} {city}, Deutschland"


def fmt(v):
    return f"{v:.7f}" if v is not None else ""


def main():
    ap = argparse.ArgumentParser(description="Geocode rows with empty lat/lng and update the CSV in place.")
    ap.add_argument("--mode", choices=["address", "plz"], default="address",
                    help="'address' = street + plz + city (default), 'plz' = postal code only")
    ap.add_argument("--dry-run", action="store_true",
                    help="only print which rows would be geocoded, do not write")
    args = ap.parse_args()

    if not os.path.exists(SRC):
        raise SystemExit(f"File not found: {SRC}")

    if not os.path.exists(BAK):
        shutil.copy2(SRC, BAK)
        print(f"Backup created: {BAK}")

    with open(SRC, "r", encoding=ENCODING, newline="") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    data = rows[1:]

    todo = []
    for i, r in enumerate(data):
        if not (r[8].strip() and r[9].strip()):
            todo.append(i)

    print(f"Rows needing geocoding: {len(todo)}")

    updated = 0
    failed = []
    for idx in todo:
        r = data[idx]
        rid, address, city, plz = r[0], r[1], r[2], r[3]
        q = build_query(args.mode, address, plz, city)
        print(f"  id {rid}: {q}")
        lat, lon = query_nominatim(q)
        if lat is None:
            if args.mode == "address" and (address or "").strip():
                fallback_q = build_query("plz", "", plz, city)
                print(f"    no address match, retrying with postal code only: {fallback_q}")
                lat, lon = query_nominatim(fallback_q)
        if lat is None:
            failed.append(rid)
            print(f"    FAILED (kept empty)")
        else:
            r[8] = fmt(lat)
            r[9] = fmt(lon)
            updated += 1
            print(f"    -> {r[8]}, {r[9]}")
        time.sleep(DELAY)

    if args.dry_run:
        print("Dry run - no file written.")
        return

    if updated:
        with open(SRC, "w", encoding=ENCODING, newline="") as f:
            writer = csv.writer(f, lineterminator="\r\n")
            writer.writerow(header)
            writer.writerows(data)
        print(f"\nUpdated {updated} row(s) in {SRC}")
    else:
        print("\nNothing to update.")

    if failed:
        print(f"\nFailed ({len(failed)}): {failed} - lat/lng left empty for review.")


if __name__ == "__main__":
    main()
