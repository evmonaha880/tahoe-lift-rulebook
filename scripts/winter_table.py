"""Per-winter summary labelled by El Nino phase (ONI, Dec-Jan-Feb, values from NOAA CPC oni.txt as recorded in docs/DATA_SOURCES.md)."""
import os, csv, json, collections
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ONI = {"2018-19": (0.99, "weak El Niño"), "2019-20": (0.71, "weak El Niño"), "2020-21": (-0.99, "La Niña"), "2021-22": (-0.76, "La Niña"),
       "2022-23": (-0.55, "La Niña"), "2023-24": (1.84, "strong El Niño"), "2024-25": (-0.46, "neutral"), "2025-26": (-0.39, "neutral")}
rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "derived", "lift_days.csv"))))
res = json.load(open(os.path.join(ROOT, "results", "loo_results.json")))
days = collections.defaultdict(dict)
for r in rows:
    d = days[r["winter"]].setdefault(r["date"], dict(g=float(r["day_gust"]) if r["day_gust"] else None, w=0, h=0)); d["w"] |= int(r["held_wind"]); d["h"] |= int(r["held"])
out = []
print(f"{'winter':8} {'ONI':>5} {'phase':15} {'days w/ posts':>13} {'wind-hold days':>14} {'days gust>=60':>13} {'rule F1 (unseen)':>16} {'baseline F1':>11}")
for W, (oni, ph) in ONI.items():
    D = list(days[W].values()); n = len(D); wd = sum(d["w"] for d in D); gd = sum(1 for d in D if d["g"] is not None and d["g"] >= 60)
    f = res["day_level"][W]["learned"]["f1"]; b = res["day_level"][W]["baseline"]["f1"]
    print(f"{W:8} {oni:5.2f} {ph:15} {n:13} {wd:9} ({wd/n:4.0%}) {gd:8} ({gd/n:4.0%}) {f:16.2f} {b:11.2f}")
    out.append(dict(winter=W, oni=oni, phase=ph, days_with_posts=n, wind_hold_days=wd, gust60_days=gd, f1=f, baseline_f1=b))
json.dump(out, open(os.path.join(ROOT, "results", "winter_table.json"), "w"), indent=1)
