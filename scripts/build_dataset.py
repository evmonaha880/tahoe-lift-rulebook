"""Join parsed events to weather. Unit = (lift, local date) for every lift scheduled that day (roster) or named in an event.
Features come from the 15-minute station files (+ Sierra Avalanche Center danger). Outcome columns come only from the posts.
usage: python3 -I scripts/build_dataset.py 2023 2024 2025   -> data/derived/lift_days.csv"""
import os, sys, csv, json, re, collections
from datetime import datetime
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
def fl(x):
    try: return float(x)
    except Exception: return None
RIDGE = ["Siberia", "Summit", "Roundhouse Top", "Scott Top", "Belmont", "Funitel Top"]
def load_weather(Y):
    """hourly-bin dict: (date_iso, hour) -> {station_key: {gust, spd, temp, snow24, prec24}}"""
    out = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(list)))
    for m in ["10", "11", "12", "01", "02", "03", "04", "05"]:
        yr = Y if m in ("10", "11", "12") else Y + 1
        f = os.path.join(R, "raw", "wwg", "15min", f"{yr}-{m}.csv")
        if not os.path.exists(f): continue
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            try: d = datetime.strptime(r["Date"], "%m/%d/%y"); hh = int(r["Time"]) // 100
            except Exception: continue
            st = next((k for k in RIDGE + ["Roundhouse Btm"] if k in r["Station"]), None)
            if not st: continue
            b = out[(d.date().isoformat(), hh)][st]
            for k, col in (("gust", "Wind Gust (mph)"), ("spd", "Wind Spd (mph)"), ("temp", "Temp (°F)"), ("snow24", "Snow 24Hr (In)"), ("prec24", "Precip 24Hr (In)")):
                v = fl(r.get(col)); 
                if v is not None: b[k].append(v)
    return out
def avy():
    d = {}
    for p in json.load(open(os.path.join(R, "raw", "avy", "sac_products.json"))):
        if p["product_type"] != "forecast" or not p.get("danger"): continue
        cur = [x for x in p["danger"] if x.get("valid_day") == "current"]
        if not cur: continue
        v = [x for x in (cur[0].get("lower"), cur[0].get("middle"), cur[0].get("upper")) if isinstance(x, int)]
        if v: d[p["start_date"][:10]] = max(v)
    return d
AV = avy()
def feats(W, date):
    def agg(h0, h1, key, fn, stations=RIDGE):
        vals = [x for h in range(h0, h1) for s in stations for x in W.get((date, h), {}).get(s, {}).get(key, [])]
        return fn(vals) if vals else None
    return {"early_gust": agg(5, 9, "gust", max), "early_spd": agg(5, 9, "spd", max),
            "day_gust": agg(6, 16, "gust", max), "day_spd": agg(6, 16, "spd", max),
            "fnt_day_gust": agg(6, 16, "gust", max, ["Funitel Top"]),
            "temp_base": agg(6, 10, "temp", lambda v: sum(v) / len(v), ["Roundhouse Btm"]),
            "snow24": agg(8, 10, "snow24", max, RIDGE + ["Roundhouse Btm"]), "prec24": agg(8, 10, "prec24", max, RIDGE + ["Roundhouse Btm"]),
            "avy": AV.get(date)}
rows = []
for Y in map(int, sys.argv[1:]):
    W = f"{Y}-{str(Y+1)[2:]}"; weather = load_weather(Y)
    ev = []
    for sp in ("train", "heldout"):
        for e in json.load(open(os.path.join(R, "derived", f"{W}_{sp}_events.json"))): e["split"] = sp; ev.append(e)
    by = collections.defaultdict(list)
    for e in ev: by[e["start"][:10]].append(e)
    for date, es in sorted(by.items()):
        sched = {e["lift"] for e in es if e["event_type"] == "scheduled_opening" and e["lift"] and e["lift"] != "ALL"}
        lifts = set(sched) | {e["lift"] for e in es if e["lift"] and e["lift"] != "ALL" and e["event_type"] in ("hold_start", "closed_day", "delay", "partial", "reopen")}
        if not lifts: continue
        f = feats(weather, date)
        for L in sorted(lifts):
            mine = [e for e in es if e["event_type"] in ("hold_start", "closed_day", "delay", "partial") and (e["lift"] == L or e["lift"] == "ALL")]
            row = {"winter": W, "date": date, "lift": L, "scheduled": L in sched, **f,
                   "held": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") for e in mine)),
                   "held_wind": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") and e["cause"] == "wind" for e in mine)),
                   "held_unstated": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") and not e["cause"] for e in mine)),
                   "first_event": min([e["start"][11:16] for e in mine] or [""]),
                   "in_heldout_posts": int(any(e["split"] == "heldout" for e in mine))}
            rows.append(row)
out = os.path.join(R, "derived", "lift_days.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
n = len(rows); print(f"{n} lift-days -> {out}")
for W in sorted({r['winter'] for r in rows}):
    x = [r for r in rows if r['winter'] == W]
    print(W, len(x), "lift-days;", sum(r['held'] for r in x), "held;", sum(r['held_wind'] for r in x), "wind-stated;",
          f"{sum(r['early_gust'] is not None for r in x)/len(x):.0%} have early gust,", f"{sum(r['avy'] is not None for r in x)/len(x):.0%} have avalanche rating")
