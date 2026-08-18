import csv
import os
import shutil

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "UpdateBS.csv")
BAK = os.path.join(BASE, "UpdateBS_backup.csv")

ENCODING = "latin-1"

if not os.path.exists(SRC):
    raise SystemExit(f"File not found: {SRC}")

if not os.path.exists(BAK):
    shutil.copy2(SRC, BAK)
    print(f"Backup created: {BAK}")
else:
    print(f"Backup already exists, keeping it: {BAK}")

with open(SRC, "r", encoding=ENCODING, newline="") as f:
    rows = list(csv.reader(f))

header = rows[0]
data = rows[1:]

seen = {}
dups = []
for i, r in enumerate(data):
    key = (r[1].strip().lower(), r[2].strip().lower(), r[3].strip().lower())
    if key in seen:
        dups.append((i + 2, r[0], seen[key][0], seen[key][1]))
    else:
        seen[key] = (i + 2, r[0])

keep = []
first_seen = set()
for r in data:
    key = (r[1].strip().lower(), r[2].strip().lower(), r[3].strip().lower())
    if key in first_seen:
        continue
    first_seen.add(key)
    keep.append(r)

print(f"Total data rows: {len(data)}")
print(f"Duplicate rows removed: {len(dups)}")
print(f"Unique rows kept: {len(keep)}")
for ln, rid, fln, fid in dups:
    print(f"  removed line {ln} (id {rid})  <- duplicate of line {fln} (id {fid})")

with open(SRC, "w", encoding=ENCODING, newline="") as f:
    writer = csv.writer(f, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(keep)

print(f"Updated: {SRC}")

print("\nNear-duplicates kept for manual review (not exact matches):")
near = [
    (70, "Zur Fluegelau 24", "Crailsheim", "74564", "orig: Crailsheim-Altenmuenster, 74564"),
    (84, "Karl-Singer-Str. 2", "Altenstadt an der Waldnaab", "92665", "orig: Altenstadt, 92665"),
    (120, "Koenigsberger Strasse 26", "Duesseldorf", "40321", "orig: Duesseldorf, 40231"),
]
for rid, a, c, p, note in near:
    print(f"  id {rid}: {a} | {c} | {p}  ({note})")
