"""Quality flags for the 15-minute weather files, one row per station-day: readings in the 06:00-16:00 window (40 expected),
flag ok / partial / missing, dropout (a 0.0 gust on a day another ridge station gusts over 20 mph), impossible values.
Writes data/derived/weather_qc.csv; scripts/check_data.py reads it.   usage: python3 -I scripts/weather_qc.py"""
import os, csv, glob, collections
from datetime import datetime
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RIDGE = ["Siberia", "Summit", "Roundhouse Top", "Scott Top", "Belmont", "Funitel Top"]
cnt = collections.defaultdict(int); gmax = {}; bad = collections.Counter()
for f in sorted(glob.glob(os.path.join(root, "data/raw/wwg/15min/*.csv"))):
    for r in csv.DictReader(open(f, encoding="utf-8-sig")):
        st = next((k for k in RIDGE if k in r["Station"]), None)
        if not st: continue
        try: d = datetime.strptime(r["Date"], "%m/%d/%y").date().isoformat(); hh = int(r["Time"]) // 100
        except Exception: continue
        try: g = float(r["Wind Gust (mph)"])
        except Exception: g = None
        try: t = float(r["Temp (°F)"])
        except Exception: t = None
        if g is not None and not 0 <= g <= 250: bad[(d, st)] += 1
        if t is not None and not -45 <= t <= 110: bad[(d, st)] += 1
        if 6 <= hh < 16:
            cnt[(d, st)] += 1
            if g is not None: gmax[(d, st)] = max(gmax.get((d, st), 0), g)
rows = []; days = sorted({k[0] for k in cnt})
for d in days:
    others = {s: gmax.get((d, s), 0) for s in RIDGE}
    for s in RIDGE:
        if (d, s) not in cnt: continue
        n = cnt[(d, s)]; flag = "ok" if n >= 36 else "partial" if n >= 20 else "missing"
        dropout = int(gmax.get((d, s), 0) < 0.5 and max(v for k, v in others.items() if k != s) > 20)
        rows.append([d, s, n, flag, dropout, bad.get((d, s), 0)])
with open(os.path.join(root, "data/derived/weather_qc.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["date", "station", "readings_06_16", "flag", "dropout", "impossible_values"]); w.writerows(rows)
c = collections.Counter(r[3] for r in rows); print(f"weather_qc: {len(rows)} station-days; {dict(c)}; dropouts {sum(r[4] for r in rows)}; impossible values {sum(r[5] for r in rows)}")
