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
    """Sierra Avalanche Center danger for the day (1-5). Newer products carry bands; older ones only the top-level danger_rating,
    which equals the max of the bands wherever both exist (checked on 2,685 products). start_date is UTC and equals the Pacific date."""
    d = {}
    for p in json.load(open(os.path.join(R, "raw", "avy", "sac_products.json"))):
        if p["product_type"] != "forecast": continue
        v = []
        cur = [x for x in (p.get("danger") or []) if x.get("valid_day") == "current"]
        if cur: v = [int(x) for x in (cur[0].get("lower"), cur[0].get("middle"), cur[0].get("upper")) if str(x).lstrip("-").isdigit() and int(x) > 0]
        if v: d[p["start_date"][:10]] = max(v)
        elif isinstance(p.get("danger_rating"), int) and p["danger_rating"] > 0: d[p["start_date"][:10]] = p["danger_rating"]
    return d
AV = avy()
def snotel(Y):
    """SNOTEL 784 hourly -> {datetime: (swe, depth, prec)} ; timestamps are local standard time per NRCS (UNVERIFIED for DST)"""
    d = {}
    f = os.path.join(R, "raw", "snotel", f"784_hourly_{Y}-{str(Y+1)[2:]}.csv")
    for line in open(f):
        if line.startswith("#") or line.startswith("Date") or not line.strip(): continue
        c = line.rstrip("\n").split(",")
        try: d[datetime.strptime(c[0], "%Y-%m-%d %H:%M")] = (fl(c[1]), fl(c[2]), fl(c[3]))
        except Exception: pass
    return d
import statistics
from datetime import timedelta
def load_depth(Y):
    """Alpine Meadows Roundhouse Btm snow depth (in), 15-minute, glitch-filtered: a reading is dropped if it is >25in from the median of its +-6h
    neighbours, reads ~0 when the neighbours are deep, or is >190 (sensor stuck / dropout codes seen in 2019-20 and 2024-25)."""
    raw = {}
    for m in ["11", "12", "01", "02", "03", "04", "05"]:
        yr = Y if m in ("11", "12") else Y + 1
        f = os.path.join(R, "raw", "wwg", "15min", f"{yr}-{m}.csv")
        if not os.path.exists(f): continue
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            if "Roundhouse Btm" not in r["Station"]: continue
            try: raw[datetime.strptime(r["Date"] + " " + r["Time"].zfill(4), "%m/%d/%y %H%M")] = fl(r.get("Snow Depth (HS) (in)"))
            except Exception: continue
    out = {}
    for t, v in raw.items():
        if v is None: continue
        nb = [raw.get(t + timedelta(minutes=k)) for k in range(-360, 361, 15) if k]
        nb = [x for x in nb if x is not None]
        m = statistics.median(nb) if len(nb) > 10 else None
        if v > 190 or (m is not None and (abs(v - m) > 25 or (v < 1 and m > 5))): continue
        out[t] = v
    return out
def depth_gain(D, date):
    """snow added in the 24h before 9am local: depth now minus the lowest depth in the previous 24h (3-hourly, 5-reading medians)"""
    t9 = datetime.strptime(date, "%Y-%m-%d") + timedelta(hours=9)
    def dep(t):
        v = [D[t + timedelta(minutes=k)] for k in (-30, -15, 0, 15, 30) if (t + timedelta(minutes=k)) in D]
        return statistics.median(v) if v else None
    now = dep(t9); prev = [x for x in (dep(t9 - timedelta(hours=h)) for h in range(0, 25, 3)) if x is not None]
    return max(0.0, now - min(prev)) if now is not None and len(prev) >= 5 else None
def snow_feats(S, date):
    from datetime import timedelta
    t9 = datetime.strptime(date, "%Y-%m-%d") + timedelta(hours=9)
    g = lambda t, i: (S.get(t) or (None, None, None))[i]
    def diff(i, h):
        a, b = g(t9, i), g(t9 - timedelta(hours=h), i)
        return max(0.0, a - b) if a is not None and b is not None else None
    ups = [g(t9 - timedelta(hours=k), 1) for k in range(24, -1, -1)]
    inc = sum(max(0.0, ups[i + 1] - ups[i]) for i in range(24) if ups[i] is not None and ups[i + 1] is not None) if all(u is not None for u in ups) else None
    return {"swe24": diff(0, 24), "swe6": diff(0, 6), "prec24s": diff(2, 24), "new_snow24": inc, "depth": g(t9, 1)}
def feats_agg(W, date, st):
    vals = [x for h in range(6, 16) for x in W.get((date, h), {}).get(st, {}).get("gust", [])]
    return max(vals) if vals else None
def feats(W, date, S):
    def agg(h0, h1, key, fn, stations=RIDGE):
        vals = [x for h in range(h0, h1) for s in stations for x in W.get((date, h), {}).get(s, {}).get(key, [])]
        return fn(vals) if vals else None
    return {"early_gust": agg(5, 9, "gust", max), "early_spd": agg(5, 9, "spd", max),
            "day_gust": agg(6, 16, "gust", max), "day_spd": agg(6, 16, "spd", max),
            "fnt_day_gust": agg(6, 16, "gust", max, ["Funitel Top"]),
            "temp_base": agg(6, 10, "temp", lambda v: sum(v) / len(v), ["Roundhouse Btm"]),
            **snow_feats(S, date), "avy": AV.get(date)}
# Group scopes ("all upper mountain lifts are on wind hold") are credited to each real lift in the group, from rules/lift_groups.json.
_LG = json.load(open(os.path.join(R, "..", "rules", "lift_groups.json")))
_P, _A = _LG["palisades"], _LG["alpine"]
_UP, _LO = set(_P["UPPER_MOUNTAIN"]["lifts"]), set(_P["LOWER_MOUNTAIN"]["lifts"])
GROUPS = {"UPPER_MOUNTAIN": _UP, "LOWER_MOUNTAIN": _LO,
          "ALL_PALISADES": _UP | _LO | set(_P["UNGROUPED"]) | set(_LG["not_in_the_2026_lifts_file"]["legacy_names_in_posts"]),
          "ALL_ALPINE": set(_A["named_together"]) | set(_A["named_separately_not_upper"]) | set(_A["also_alpine"])}
YEARS = list(map(int, sys.argv[1:]))
WEATHER = {Y: load_weather(Y) for Y in YEARS}
def fit_funitel():
    """The Funitel-top station was off in Feb-May 2024, Nov 2025-Feb 2026 and before Apr 2019 (the source returns no rows for those dates).
    Estimate its daily 6am-4pm max gust as a + b*Siberia + c*Belmont, fitted on days where all three were measured. Estimates are flagged."""
    X, Yv = [], []
    for Y in YEARS:
        if Y >= 2025: continue          # 2025-26 Funitel-top readings are a different regime (R2 -0.26 against the earlier fit): excluded from the fit
        days = collections.defaultdict(lambda: collections.defaultdict(float))
        for (dt, hh), sts in WEATHER[Y].items():
            if 6 <= hh < 16:
                for st in ("Funitel Top", "Siberia", "Belmont"):
                    g = sts.get(st, {}).get("gust")
                    if g: days[dt][st] = max(days[dt][st], max(g))
        for dt, v in days.items():
            if dt[5:7] in ("10", "05") or v.get("Funitel Top", 0) < 0.5: continue      # shoulder months are calm; 0.0 is a dropout, not wind
            if all(k in v for k in ("Funitel Top", "Siberia", "Belmont")): X.append([1.0, v["Siberia"], v["Belmont"]]); Yv.append(v["Funitel Top"])
    M = [[sum(r[i] * r[j] for r in X) for j in range(3)] + [sum(r[i] * y for r, y in zip(X, Yv))] for i in range(3)]
    for i in range(3):
        pv = max(range(i, 3), key=lambda r: abs(M[r][i])); M[i], M[pv] = M[pv], M[i]
        for r in range(3):
            if r != i: f_ = M[r][i] / M[i][i]; M[r] = [a - f_ * b for a, b in zip(M[r], M[i])]
    coef = [M[i][3] / M[i][i] for i in range(3)]
    pred = [sum(c * x for c, x in zip(coef, r)) for r in X]; my = sum(Yv) / len(Yv)
    r2 = 1 - sum((y - p) ** 2 for y, p in zip(Yv, pred)) / sum((y - my) ** 2 for y in Yv)
    print(f"Funitel-top estimate fitted on {len(Yv)} measured days: gust = {coef[0]:.2f} + {coef[1]:.2f}*Siberia + {coef[2]:.2f}*Belmont  (R2 {r2:.2f})")
    return coef
FNT_COEF = fit_funitel()
rows = []
for Y in YEARS:
    W = f"{Y}-{str(Y+1)[2:]}"; weather = WEATHER[Y]; SN = snotel(Y); DEPTH = load_depth(Y)
    ev = []
    for sp in ("train", "heldout"):
        for e in json.load(open(os.path.join(R, "derived", f"{W}_{sp}_events.json"))): e["split"] = sp; ev.append(e)
    by = collections.defaultdict(list)
    for e in ev: by[e["start"][:10]].append(e)
    for date, es in sorted(by.items()):
        sched = {e["lift"] for e in es if e["event_type"] == "scheduled_opening" and e["lift"] and e["lift"] != "ALL"}
        lifts = set(sched) | {e["lift"] for e in es if e["lift"] and e["lift"] not in ("ALL", "ALL_OTHER", "ALL_ALPINE", "ALL_PALISADES", "UPPER_MOUNTAIN", "LOWER_MOUNTAIN") and e["event_type"] in ("hold_start", "closed_day", "delay", "partial", "reopen")}
        if any(e["lift"] == "ALL_OTHER" for e in es): lifts = set(lifts) | {"(all other lifts)"}
        if not lifts: continue
        f = feats(weather, date, SN)
        f["new_snow24_snotel"] = f["new_snow24"]                    # old noisy SNOTEL-depth figure, kept for comparison
        f["new_snow24"] = depth_gain(DEPTH, date)                   # Alpine base depth sensor, dropout-filtered
        f["fnt_measured"] = f["fnt_day_gust"]                         # raw station reading (blank when the station was off)
        _sib = feats_agg(weather, date, "Siberia")
        if f["fnt_day_gust"] is not None and f["fnt_day_gust"] < 0.5 and _sib is not None and _sib > 20: f["fnt_day_gust"] = None     # 0.0 on a windy day = sensor dropout
        if Y >= 2025: f["fnt_day_gust"] = None                       # 2025-26 readings are a different regime: use the estimate for the whole winter so the series stays comparable
        if f["fnt_day_gust"] is None:
            sib = feats_agg(weather, date, "Siberia"); bel = feats_agg(weather, date, "Belmont")
            if sib is not None and bel is not None: f["fnt_day_gust"] = round(FNT_COEF[0] + FNT_COEF[1] * sib + FNT_COEF[2] * bel, 1); f["fnt_src"] = "estimated"
            else: f["fnt_src"] = ""
        else: f["fnt_src"] = "measured"
        for L in sorted(lifts):
            mine = [e for e in es if e["event_type"] in ("hold_start", "closed_day", "delay", "partial") and (e["lift"] == L or e["lift"] == "ALL" or (e["lift"] == "ALL_OTHER" and L not in e.get("except", [])) or (e["lift"] in GROUPS and L in GROUPS[e["lift"]] and not any(x["source_post_id"] == e["source_post_id"] and x["lift"] == L and x["event_type"] in ("reopen", "scheduled_opening", "partial") for x in es)))]
            row = {"winter": W, "date": date, "lift": L, "scheduled": L in sched, **f,
                   "held": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") for e in mine)),
                   "held_wind": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") and e["cause"] == "wind" for e in mine)),
                   "held_patrol": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") and e["cause"] == "patrol" for e in mine)),
                   "held_mech": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") and e["cause"] == "mechanical" for e in mine)),
                   "held_weather": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") and e["cause"] == "weather" for e in mine)),
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
          f"{sum(r['early_gust'] is not None for r in x)/len(x):.0%} have early gust, {sum(r['swe24'] is not None for r in x)/len(x):.0%} have snow,", f"{sum(r['avy'] is not None for r in x)/len(x):.0%} have avalanche rating")
