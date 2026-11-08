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
            st = next((k for k in RIDGE + ["Roundhouse Btm", "Treeline Cirque", "Yellow Valve", "Sherwood", "KT"] if k in r["Station"]), None)
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
NWS = []
_nf = os.path.join(R, "derived", "nws_alerts.csv")
if os.path.exists(_nf):
    for _r in csv.DictReader(open(_nf)):
        _i = datetime.fromisoformat(_r["issue_utc"].replace("Z", "+00:00")); _e = datetime.fromisoformat(_r["expire_utc"].replace("Z", "+00:00"))
        if _e <= _i: _e = _i + __import__("datetime").timedelta(hours=12)        # a watch that was upgraded carries an expire time before its issue time
        NWS.append((_r["phenomena"] + "." + _r["significance"], _i, _e))
NWS_COLS = {"nws_hw_w": ("HW.W",), "nws_hw_a": ("HW.A",), "nws_wi": ("WI.Y",), "nws_ws_w": ("WS.W",), "nws_ws_a": ("WS.A",), "nws_ww": ("WW.Y",), "nws_bz": ("BZ.W",), "nws_flood": ("FA.A", "FA.W", "FF.A", "FF.W", "FL.W", "FL.A")}
def nws_flags(date):
    """National Weather Service alerts for the Greater Lake Tahoe Area zone active at any point between 6am and 4pm Pacific"""
    from zoneinfo import ZoneInfo
    a = datetime.strptime(date, "%Y-%m-%d").replace(hour=6, tzinfo=ZoneInfo("America/Los_Angeles")); b = a.replace(hour=16)
    act = {k for k, i, e in NWS if i <= b and e >= a}
    out = {c: int(bool(act & set(v))) for c, v in NWS_COLS.items()}
    out["nws_wind_any"] = int(bool(act & {"HW.W", "HW.A", "WI.Y"})); out["nws_storm_any"] = int(bool(act & {"WS.W", "BZ.W", "WW.Y", "WS.A"}))
    pre = {k for k, i, e in NWS if i <= a and e >= a}                                   # already in force at 6am: what a morning-of forecast could have known
    out["nws_pre_wind"] = int(bool(pre & {"HW.W", "HW.A", "WI.Y"})); out["nws_pre_storm"] = int(bool(pre & {"WS.W", "BZ.W", "WW.Y", "WS.A"}))
    return out
LIFT_STATION = json.load(open(os.path.join(R, "..", "rules", "lift_stations.json")))["stations"]
def hour_feats(W, date, t):
    """wind at Siberia in the hour of the first post about the lift, and the strongest gust in the three hours before it (None without a post time)"""
    if not t: return {"gust_at_event": "", "gust_prior3h": "", "spd_at_event": ""}
    h = int(t[:2]); g = lambda hh, k: [x for x in W.get((date, hh), {}).get("Siberia", {}).get(k, [])]
    now = g(h, "gust"); pri = [x for hh in range(h - 3, h + 1) for x in g(hh, "gust")]; sp = g(h, "spd")
    return {"gust_at_event": max(now) if now else "", "gust_prior3h": max(pri) if pri else "", "spd_at_event": max(sp) if sp else ""}
def local_feats(W, date, L):
    st = LIFT_STATION.get(L)
    if not st: return {"local_station": "", "local_gust": ""}
    v = [x for h in range(6, 16) for x in W.get((date, h), {}).get(st, {}).get("gust", [])]
    return {"local_station": st, "local_gust": max(v) if v else ""}
def hours_over(W, date, st, thr):
    """hours between 6am and 4pm local with a 15-minute gust reading at or above thr at one station (readings / 4); None when the station has no readings"""
    v = [x for h in range(6, 16) for x in W.get((date, h), {}).get(st, {}).get("gust", [])]
    return round(sum(1 for x in v if x >= thr) / 4, 2) if v else None
def feats(W, date, S):
    def agg(h0, h1, key, fn, stations=RIDGE):
        vals = [x for h in range(h0, h1) for s in stations for x in W.get((date, h), {}).get(s, {}).get(key, [])]
        return fn(vals) if vals else None
    return {"early_gust": agg(5, 9, "gust", max), "early_spd": agg(5, 9, "spd", max),
            "day_gust": agg(6, 16, "gust", max), "day_spd": agg(6, 16, "spd", max),
            "fnt_day_gust": agg(6, 16, "gust", max, ["Funitel Top"]),
            "sib_h40": hours_over(W, date, "Siberia", 40), "sib_h60": hours_over(W, date, "Siberia", 60),
            "temp_base": agg(6, 10, "temp", lambda v: sum(v) / len(v), ["Roundhouse Btm"]),
            **snow_feats(S, date), "avy": AV.get(date)}
# Group scopes ("all upper mountain lifts are on wind hold") are credited to each real lift in the group, from rules/lift_groups.json.
_LG = json.load(open(os.path.join(R, "..", "rules", "lift_groups.json")))
_P, _A = _LG["palisades"], _LG["alpine"]
_UP, _LO = set(_P["UPPER_MOUNTAIN"]["lifts"]), set(_P["LOWER_MOUNTAIN"]["lifts"])
GROUPS = {"UPPER_MOUNTAIN": _UP, "LOWER_MOUNTAIN": _LO,
          "ALL_PALISADES": _UP | _LO | set(_P["UNGROUPED"]) | set(_LG["not_in_the_2026_lifts_file"]["legacy_names_in_posts"]),
          "ALL_ALPINE": set(_A["named_together"]) | set(_A["named_separately_not_upper"]) | set(_A["also_alpine"])}
SIDE = {}
for _l in GROUPS["ALL_PALISADES"]: SIDE[_l] = "palisades"
for _l in GROUPS["ALL_ALPINE"]: SIDE[_l] = "alpine"
SIDE["Base to Base Gondola"] = "link"      # joins the two sides; it keeps its own seasonal timeline, so it counts as in season when either side is
SEASONS = json.load(open(os.path.join(R, "..", "rules", "season_windows.json")))["winters"]
OPS = ("scheduled_opening", "reopen", "hold_start", "closed_day", "delay", "partial")
def effective_windows(W, ev):
    """open = earliest of the web date and the first day a roster post lists a lift on that side; close = latest of the web date and the last such roster day (union, so no real operating day is cut)"""
    out = {}
    for side in ("palisades", "alpine"):
        days = sorted({e["start"][:10] for e in ev if e["event_type"] == "scheduled_opening" and SIDE.get(e["lift"]) == side})   # roster days only: a storm post alone is not an operating day
        any_days = sorted({e["start"][:10] for e in ev if e["event_type"] in ("scheduled_opening", "reopen", "hold_start", "delay", "partial") and SIDE.get(e["lift"]) == side})   # a hold or reopening also proves the side was running
        web = SEASONS.get(W, {}).get(side, {})
        o = [d for d in (web.get("open"), days[0] if days else None) if d]; c = [d for d in (web.get("close"), any_days[-1] if any_days else None) if d]
        out[side] = {"open": min(o) if o else None, "close": max(c) if c else None, "first_post_day": days[0] if days else None, "last_post_day": any_days[-1] if any_days else None, "web_open": web.get("open"), "web_close": web.get("close")}
    ov = [out[sd]["open"] for sd in ("palisades", "alpine") if out[sd]["open"]]; cv = [out[sd]["close"] for sd in ("palisades", "alpine") if out[sd]["close"]]
    out["link"] = {"open": min(ov) if ov else None, "close": max(cv) if cv else None, "note": "Base to Base Gondola: in season when either side is"}
    return out
def typical_roster(ev):
    n = collections.Counter(e["lift"] for e in ev if e["event_type"] == "scheduled_opening" and e["lift"] in SIDE)
    r = {"palisades": set(), "alpine": set(), "link": set()}
    for l, c in n.items():
        if c >= 8: r[SIDE[l]].add(l)
    return r
def closure_kind(es, date):
    """why a whole-side closure happened, from the post tags and the date: storm (wind, snow, avalanche, visibility, ice) / lightning / infrastructure (power, flooding) / schedule (no cause named, April to June, announced before 10am, e.g. 'Alpine is closed today' on a spring schedule) / unstated"""
    if not es: return ""
    tags = set(t for e in es for t in (e.get("cause_tags") or [])); causes = {e.get("cause") for e in es} - {None}
    if tags & {"avalanche", "snow", "ice", "visibility", "weather"} or "wind" in causes or "patrol" in causes: return "storm"
    if "wind" in tags: return "storm"
    if "lightning" in tags: return "lightning"
    if tags & {"power", "flood"}: return "infrastructure"
    first = min(e["start"][11:16] for e in es)
    return "schedule" if date[5:7] in ("04", "05", "06") and first < "10:00" else "unstated"
DAYFLAG = {"avy_control": r"avalanche|control work|mitigation|snow safety|hazard reduction", "power": r"power outage|lack of power|outage|electrical|generator|power loss|power is", "lightning": r"lightning|thunder",
           "ice": r"\bice\b|\bicy\b|icing|rime|de-?ic", "vis": r"visibility|\bfog\b|whiteout|white-out", "mech": r"mechanical|winch|hose|technical|repair", "flood": r"flood|road (?:is )?closed|rock ?slide|mudslide"}
def day_flags(W):
    """day-level cause words from EVERY post that day (not only the posts that produced an event): {date: {flag: number of posts}}"""
    out = collections.defaultdict(lambda: collections.Counter()); n = collections.Counter()
    from zoneinfo import ZoneInfo
    for sp in ("train", "heldout"):
        for p in json.load(open(os.path.join(R, "derived", f"{W}_{sp}.json"))):
            d = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d"); n[d] += 1
            for k, rx in DAYFLAG.items():
                if re.search(rx, p["text"], re.I): out[d][k] += 1
            if re.search(r"covid|coronavirus|pandemic|reservation|mask", p["text"], re.I): out[d]["covid"] += 1
    return out, n
def reader_labels(W):
    """blind-reader scores for the 'closed' class: {post id: (Subquadratic, Meta Muse)}"""
    out = {}
    for sp in ("train", "heldout"):
        try: a = json.load(open(os.path.join(R, "derived", f"{W}_{sp}_labels_subq.json"))); b = json.load(open(os.path.join(R, "derived", f"{W}_{sp}_labels_muse.json")))
        except Exception: continue
        for i in a:
            x, y = a.get(i, {}), b.get(i, {})
            out[str(i)] = (x.get("closed") if isinstance(x, dict) and "error" not in x else None, y.get("closed") if isinstance(y, dict) and "error" not in y else None)
    return out
def closure_conf(es, RL, f):
    """confidence in a whole-side closure: how many of the two blind readers also call the post a closure, and whether the weather or the named cause makes it plausible"""
    if not es: return {"closure_readers": "", "closure_plausible": "", "closure_conf": ""}
    hits = 0
    for e in es:
        a, b = RL.get(str(e["source_post_id"]), (None, None)); hits = max(hits, int((a or 0) >= .5) + int((b or 0) >= .5))
    tags = {t for e in es for t in (e.get("cause_tags") or [])}
    ok = (f.get("day_gust") or 0) >= 60 or (f.get("avy") or 0) >= 3 or (f.get("swe24") or 0) >= 1.0 or bool(tags & {"lightning", "power", "flood", "visibility", "ice", "avalanche", "snow", "weather"})
    return {"closure_readers": hits, "closure_plausible": int(ok), "closure_conf": "high" if hits == 2 and ok else "medium" if hits >= 1 or ok else "low"}
def reopen_cols(mine, es, L):
    """Observed: a reopening post for this lift (or its group) after the hold began the same day. Assumed (Evan, 2026-11-07): no reopening post that day means it did not reopen."""
    h = [e for e in mine if e["event_type"] in ("hold_start", "closed_day")]
    if not h: return {"reopen_posted": "", "hold_minutes": "", "reopen_assumed_none": ""}
    t0 = min(e["start"] for e in h)
    ro = sorted(x["start"] for x in es if x["event_type"] == "reopen" and x["start"] > t0 and (x["lift"] == L or x["lift"] == "ALL" or (x["lift"] in GROUPS and L in GROUPS[x["lift"]])))
    return {"reopen_posted": int(bool(ro)), "hold_minutes": minutes(t0, ro[0]) if ro else "", "reopen_assumed_none": int(not ro)}
def covid_era(W, date):
    if W == "2019-20" and date >= "2020-03-01": return "pre_closure"           # the resort suspended operations on 2020-03-15; posts end 2020-03-14
    if W == "2020-21": return "restricted"                                     # reservations, capacity limits and health protocols all season
    return ""
def minutes(a, b):
    return round((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds() / 60)
YEARS = list(map(int, sys.argv[1:]))
EFFECTIVE = {}
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
def post_side(text):
    """'palisades', 'alpine' or None: the side of the mountain a post is about, from its own words (None when it names both or neither)."""
    t = re.sub(r"#\w+|https?://\S+", " ", (text or "").lower()); a = bool(re.search(r"\balpine\b", t)); p = bool(re.search(r"palisades|squaw|olympic valley", t))
    return "alpine" if a and not p else "palisades" if p and not a else None
def other_side_ok(e, L, es):
    """'All other lifts' covers the side of the mountain the post is about ('Alpine update', 'For Palisades'). A post naming neither side, or both,
    covers the whole resort. A lift that is reopened later the same day was held, whatever side the post named."""
    side = POSTSIDE.get(e["source_post_id"])
    return side is None or SIDE.get(L) in (None, "", "link", side) or any(x["lift"] == L and x["event_type"] == "reopen" and x["start"] > e["start"] for x in es)
POSTSIDE = {}
for Y in YEARS:
    W = f"{Y}-{str(Y+1)[2:]}"; weather = WEATHER[Y]; SN = snotel(Y); DEPTH = load_depth(Y)
    ev = []
    for sp in ("train", "heldout"):
        for e in json.load(open(os.path.join(R, "derived", f"{W}_{sp}_events.json"))): e["split"] = sp; ev.append(e)
        for _p in json.load(open(os.path.join(R, "derived", f"{W}_{sp}.json"))): POSTSIDE[_p["id"]] = post_side(_p["text"])
    EFFECTIVE[W] = effective_windows(W, ev); ROSTER = typical_roster(ev); DF, NPOSTS = day_flags(W); RL = reader_labels(W)
    by = collections.defaultdict(list)
    for e in ev: by[e["start"][:10]].append(e)
    for date, es in sorted(by.items()):
        sched = {e["lift"] for e in es if e["event_type"] == "scheduled_opening" and e["lift"] and e["lift"] not in ("ALL", "ALL_ALPINE", "ALL_PALISADES")}
        for e in es:                                                  # '12 lifts on the schedule, all lifts except ABC'
            if e["event_type"] == "scheduled_opening" and e["lift"] in ("ALL_ALPINE", "ALL_PALISADES"):
                sched |= ROSTER["alpine" if e["lift"] == "ALL_ALPINE" else "palisades"] - set(e.get("except", []))
        lifts = set(sched) | {e["lift"] for e in es if e["lift"] and e["lift"] not in ("ALL", "ALL_OTHER", "ALL_ALPINE", "ALL_PALISADES", "UPPER_MOUNTAIN", "LOWER_MOUNTAIN") and e["event_type"] in ("hold_start", "closed_day", "delay", "partial", "reopen")}
        if any(e["lift"] == "ALL_OTHER" for e in es): lifts = set(lifts) | {"(all other lifts)"}
        # whole-side closures ("Palisades Tahoe is CLOSED today", "all lifts at Alpine are closed"): every lift of that side that normally runs is a row, even when no roster was posted
        cl = [e for e in es if e["event_type"] == "closed_day" and e["lift"] in ("ALL", "ALL_PALISADES", "ALL_ALPINE")]
        cl_scope = set()
        for e in cl: cl_scope |= {"palisades", "alpine"} if e["lift"] == "ALL" else {"palisades"} if e["lift"] == "ALL_PALISADES" else {"alpine"}
        for sd in cl_scope: lifts = set(lifts) | ROSTER[sd] | (ROSTER["link"] if cl_scope == {"palisades", "alpine"} else set())
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
            mine = [e for e in es if e["event_type"] in ("hold_start", "closed_day", "delay", "partial") and (e["lift"] == L or (e["lift"] == "ALL" and L not in e.get("except", [])) or (e["lift"] == "ALL_ON_HOLD" and L not in e.get("except", []) and any(x["lift"] == L and x["event_type"] == "hold_start" and x["start"] < e["start"] for x in es)) or (e["lift"] == "ALL_OTHER" and L not in e.get("except", []) and other_side_ok(e, L, es)) or (e["lift"] in GROUPS and L in GROUPS[e["lift"]] and L not in e.get("except", []) and not any(x["source_post_id"] == e["source_post_id"] and x["lift"] == L and x["event_type"] in ("reopen", "scheduled_opening", "partial") for x in es)))]
            row = {"winter": W, "date": date, "lift": L, "scheduled": L in sched, **f,
                   "held": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") for e in mine)),
                   "held_wind": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") and e["cause"] == "wind" for e in mine)),
                   "held_patrol": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") and e["cause"] == "patrol" for e in mine)),
                   "held_mech": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") and e["cause"] == "mechanical" for e in mine)),
                   "held_weather": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") and e["cause"] == "weather" for e in mine)),
                   "held_unstated": int(any(e["event_type"] in ("hold_start", "closed_day", "delay") and not e["cause"] for e in mine)),
                   "closed_all": int(any(e["event_type"] == "closed_day" and (e["lift"] == "ALL" or (e["lift"] == "ALL_PALISADES" and SIDE.get(L) == "palisades") or (e["lift"] == "ALL_ALPINE" and SIDE.get(L) == "alpine")) for e in mine)),
                   "closure_kind": closure_kind([e for e in mine if e["event_type"] == "closed_day" and e["lift"] in ("ALL", "ALL_PALISADES", "ALL_ALPINE")], date),
                   **closure_conf([e for e in mine if e["event_type"] == "closed_day" and e["lift"] in ("ALL", "ALL_PALISADES", "ALL_ALPINE")], RL, f),
                   **reopen_cols(mine, es, L),
                   **hour_feats(weather, date, min([e["start"][11:16] for e in mine] or [""])), **local_feats(weather, date, L), **nws_flags(date),
                   "n_posts_day": NPOSTS.get(date, 0), "covid_era": covid_era(W, date),
                   **{"day_" + k: DF[date].get(k, 0) for k in list(DAYFLAG) + ["covid"]},
                   "closed_all_time": min([e["start"][11:16] for e in mine if e["event_type"] == "closed_day" and e["lift"] in ("ALL", "ALL_PALISADES", "ALL_ALPINE")] or [""]),
                   **{"tag_" + t: int(any(t in (e.get("cause_tags") or []) and e["event_type"] in ("hold_start", "closed_day", "delay") for e in mine)) for t in ("avalanche", "snow", "ice", "visibility", "lightning", "power", "flood", "rain", "grooming")},
                   "side": SIDE.get(L, ""),
                   "in_season": int(bool(SIDE.get(L)) and EFFECTIVE[W][SIDE[L]]["open"] is not None and EFFECTIVE[W][SIDE[L]]["open"] <= date <= (EFFECTIVE[W][SIDE[L]]["close"] or "9999")) if SIDE.get(L) else 1,
                   "first_event": min([e["start"][11:16] for e in mine] or [""]),
                   "in_heldout_posts": int(any(e["split"] == "heldout" for e in mine))}
            rows.append(row)
out = os.path.join(R, "derived", "lift_days.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
json.dump(EFFECTIVE, open(os.path.join(R, "derived", "season_windows_effective.json"), "w"), indent=1)
n = len(rows); print(f"{n} lift-days -> {out}")
for W in sorted({r['winter'] for r in rows}):
    x = [r for r in rows if r['winter'] == W]
    print(W, len(x), "lift-days;", sum(r['held'] for r in x), "held;", sum(r['held_wind'] for r in x), "wind-stated;",
          f"{sum(r['early_gust'] is not None for r in x)/len(x):.0%} have early gust, {sum(r['swe24'] is not None for r in x)/len(x):.0%} have snow,", f"{sum(r['avy'] is not None for r in x)/len(x):.0%} have avalanche rating")
