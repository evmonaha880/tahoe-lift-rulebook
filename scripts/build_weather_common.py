"""One weather table with the SAME columns for every winter 2015-16 to 2025-26 (Oct 1 to May 31), so a rule can be scored on any winter with the same inputs.
Sources, each available (or honestly blank) in every winter:
  sib_*  / bel_*  Western Weather Group hourly stations Siberia 8700 ft and Belmont 8000 ft (the two crest stations present in every hourly file 2016-17 on). Blank for 2015-16.
  era5_*          ERA5 reanalysis at the ridge point (Open-Meteo): 10 m gust, 10 m speed, temperature. MODELLED, about 25 km grid, all 11 winters.
  era5s_*         ERA5 snowfall, precipitation and surface pressure at the Alpine base point. MODELLED, all 11 winters.
  snotel_*        NRCS SNOTEL 784 (Palisades/Alpine) snow water and depth, measured, all 11 winters.
  trk_*           Truckee-Tahoe airport ASOS, valley wind (kt to mph). Blank for 2015-16.
  gust_est_*      a Siberia gust ESTIMATE from era5_* and snotel_* only (inputs identical in every winter), fitted leave-one-winter-out so a winter never sees its own gusts.
  gust_best_*     the station value where the station has one, else gust_est_*; gust_src (day) and gust_src_early say which. Early = hours 5-8 (known by 9 am), day = hours 6-15.
Times are local clock hours. Station and ERA5 hours are Pacific; SNOTEL is read at its 09:00 stamp (NRCS local standard time, DST not verified, same assumption as build_dataset.py).
usage: python3 -I scripts/build_weather_common.py  -> data/derived/weather_common.csv, results/weather_common.json (how good the estimate is, by winter)"""
import os, csv, json, datetime, collections
import numpy as np
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RAW = os.path.join(ROOT, "data", "raw")
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I mode does not put the script folder on the path
from config import WINTERS
def fl(x):
    try: return float(x)
    except Exception: return None
def days(W):
    y = int(W[:4]); d = datetime.date(y, 10, 1)
    while d <= datetime.date(y + 1, 5, 31): yield d; d += datetime.timedelta(days=1)
def mx(v): return round(max(v), 1) if v else None
def mean(v): return round(sum(v) / len(v), 1) if v else None
def hrs(by_hour, d, h0, h1):
    return [x for h in range(h0, h1) for x in by_hour.get((d, h), [])]
def era5(W):
    j = json.load(open(os.path.join(RAW, "openmeteo", f"era5_{W}.json")))["hourly"]; out = collections.defaultdict(lambda: collections.defaultdict(list))
    for i, t in enumerate(j["time"]):
        d, h = datetime.date.fromisoformat(t[:10]), int(t[11:13])
        for k in ("wind_gusts_10m", "wind_speed_10m", "temperature_2m"):
            if j[k][i] is not None: out[k][(d, h)].append(j[k][i])
    return out
def era5s(W):
    j = json.load(open(os.path.join(RAW, "openmeteo", f"era5snow_{W}.json")))["hourly"]; out = collections.defaultdict(dict)
    for i, t in enumerate(j["time"]):
        for k in ("snowfall", "precipitation", "surface_pressure"):
            if j[k][i] is not None: out[k][(datetime.date.fromisoformat(t[:10]), int(t[11:13]))] = j[k][i]
    return out
def snotel(W):
    out = {}
    for line in open(os.path.join(RAW, "snotel", f"784_hourly_{W}.csv")):
        if line.startswith("#") or line.startswith("Date") or not line.strip(): continue
        c = line.rstrip("\n").split(",")
        try: out[datetime.datetime.strptime(c[0], "%Y-%m-%d %H:%M")] = (fl(c[1]), fl(c[2]))
        except Exception: pass
    return out
def wwg(W):
    out = {"Siberia": collections.defaultdict(lambda: collections.defaultdict(list)), "Belmont": collections.defaultdict(lambda: collections.defaultdict(list))}
    y = int(W[:4])
    for m in ("10", "11", "12", "01", "02", "03", "04", "05"):
        f = os.path.join(RAW, "wwg", "60min", f"{y if m in ('10', '11', '12') else y + 1}-{m}.csv")
        if not os.path.exists(f): continue
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            st = "Siberia" if "Siberia" in r["Station"] else "Belmont" if "Belmont" in r["Station"] else None
            if not st: continue
            try: d = datetime.datetime.strptime(r["Date"], "%m/%d/%y").date(); h = int(r["Time"]) // 100
            except Exception: continue
            for k, col in (("gust", "Wind Gust (mph)"), ("spd", "Wind Spd (mph)"), ("temp", "Temp (°F)")):
                v = fl(r.get(col))
                if v is not None: out[st][k][(d, h)].append(v)
    return out
def trk(W):
    out = collections.defaultdict(lambda: collections.defaultdict(list)); f = os.path.join(RAW, "iem_asos", f"TRK_{W}.csv")
    if not os.path.exists(f): return out
    for r in csv.DictReader(open(f)):
        try: t = datetime.datetime.strptime(r["valid"], "%Y-%m-%d %H:%M")
        except Exception: continue
        for k, col in (("gust", "gust"), ("spd", "sknt")):
            v = fl(r.get(col))
            if v is not None: out[k][(t.date(), t.hour)].append(v * 1.15078)
    return out
DROPOUT = set(); q = os.path.join(ROOT, "data", "derived", "weather_qc.csv")
if not os.path.exists(q): raise SystemExit("data/derived/weather_qc.csv is missing: run scripts/weather_qc.py first (without it dropout days would stay in the weather table)")
for r in csv.DictReader(open(q)):
    if r["dropout"] == "1": DROPOUT.add((r["date"], r["station"]))
rows = []
for W in WINTERS:
    E, ES, SN, S, T = era5(W), era5s(W), snotel(W), wwg(W), trk(W)
    def sn(d, field):
        for dh in (0, 1, -1):
            v = SN.get(datetime.datetime(d.year, d.month, d.day, 9) + datetime.timedelta(hours=dh))
            if v and v[field] is not None: return v[field]
        return None
    for d in days(W):
        pd_ = d - datetime.timedelta(days=1)
        r = dict(date=str(d), winter=W)
        for st, pre in (("Siberia", "sib"), ("Belmont", "bel")):
            g = S[st]["gust"]; ok = (str(d), st) not in DROPOUT
            r[f"{pre}_early_gust"] = mx(hrs(g, d, 5, 9)) if ok else None; r[f"{pre}_day_gust"] = mx(hrs(g, d, 6, 16)) if ok else None
            r[f"{pre}_early_spd"] = mx(hrs(S[st]["spd"], d, 5, 9)); r[f"{pre}_day_spd"] = mx(hrs(S[st]["spd"], d, 6, 16))
        r["sib_temp_early"] = mean(hrs(S["Siberia"]["temp"], d, 6, 10))
        g, s, t = E["wind_gusts_10m"], E["wind_speed_10m"], E["temperature_2m"]
        r["era5_early_gust"] = mx(hrs(g, d, 5, 9)); r["era5_day_gust"] = mx(hrs(g, d, 6, 16)); r["era5_early_spd"] = mx(hrs(s, d, 5, 9)); r["era5_day_spd"] = mx(hrs(s, d, 6, 16)); r["era5_temp_early"] = mean(hrs(t, d, 6, 10))
        sf = ES["snowfall"]; pr = ES["precipitation"]; ps = ES["surface_pressure"]
        prior = [sf.get((pd_, h)) for h in range(9, 24)] + [sf.get((d, h)) for h in range(0, 9)]
        r["era5s_snow24"] = round(sum(x for x in prior if x is not None), 2) if any(x is not None for x in prior) else None
        pp = [pr.get((pd_, h)) for h in range(9, 24)] + [pr.get((d, h)) for h in range(0, 9)]
        r["era5s_prec24"] = round(sum(x for x in pp if x is not None), 2) if any(x is not None for x in pp) else None
        p9, p21 = ps.get((d, 9)), ps.get((pd_, 21)); r["era5s_p9"] = round(p9, 1) if p9 is not None else None; r["era5s_p_chg12"] = round(p9 - p21, 1) if p9 is not None and p21 is not None else None
        sw, sw0, dp, dp0 = sn(d, 0), sn(pd_, 0), sn(d, 1), sn(pd_, 1)
        r["snotel_swe"] = sw; r["snotel_depth"] = dp
        r["snotel_swe24"] = round(sw - sw0, 2) if sw is not None and sw0 is not None else None
        r["snotel_depth_gain24"] = round(dp - dp0, 1) if dp is not None and dp0 is not None else None
        r["trk_early_gust"] = mx(hrs(T["gust"], d, 5, 9)); r["trk_day_gust"] = mx(hrs(T["gust"], d, 6, 16)); r["trk_day_spd"] = mx(hrs(T["spd"], d, 6, 16))
        rows.append(r)
# ---- gust estimate from inputs that exist in every winter, fitted leave-one-winter-out
def feats(r, kind):
    g, s = r[f"era5_{kind}_gust"], r[f"era5_{kind}_spd"]
    sw = r["snotel_swe24"] if r["snotel_swe24"] is not None else 0.0; sn = r["era5s_snow24"] if r["era5s_snow24"] is not None else 0.0
    pc = r["era5s_p_chg12"] if r["era5s_p_chg12"] is not None else 0.0
    if g is None or s is None: return None
    return [1.0, g, s, max(sw, 0.0), sn, pc, g * g / 100.0]
report = {}
for kind in ("early", "day"):
    tgt = f"sib_{kind}_gust"; fit = [(r, feats(r, kind)) for r in rows if r[tgt] is not None and feats(r, kind)]
    for W in WINTERS:
        tr = [(r, f) for r, f in fit if r["winter"] != W]
        if len(tr) < 200: coef = None
        else:
            A = np.array([f for _, f in tr]); y = np.array([r[tgt] for r, _ in tr]); coef = np.linalg.lstsq(A, y, rcond=None)[0]
        for r in rows:
            if r["winter"] != W: continue
            f = feats(r, kind); r[f"gust_est_{kind}"] = round(float(max(0.0, np.dot(coef, f))), 1) if (coef is not None and f) else None
        te = [(r, feats(r, kind)) for r in rows if r["winter"] == W and r[tgt] is not None and feats(r, kind) and r[f"gust_est_{kind}"] is not None]
        if te:
            yv = np.array([r[tgt] for r, _ in te]); pv = np.array([r[f"gust_est_{kind}"] for r, _ in te])
            report.setdefault(kind, {})[W] = dict(days=len(te), mae_mph=round(float(np.mean(np.abs(yv - pv))), 1), r2=round(float(1 - np.sum((yv - pv) ** 2) / np.sum((yv - yv.mean()) ** 2)), 2),
                                                   era5_alone_mae_mph=round(float(np.mean(np.abs(yv - np.array([r[f"era5_{kind}_gust"] for r, _ in te])))), 1))
for r in rows:
    for kind in ("early", "day"):
        st = r[f"sib_{kind}_gust"]
        r[f"gust_best_{kind}"] = st if st is not None else r[f"gust_est_{kind}"]
    r["gust_src"] = "station" if r["sib_day_gust"] is not None else ("estimate" if r["gust_est_day"] is not None else "none")
    r["gust_src_early"] = "station" if r["sib_early_gust"] is not None else ("estimate" if r["gust_est_early"] is not None else "none")   # the known-by-9am gust can be an estimate even when the day gust is a station reading
path = os.path.join(ROOT, "data", "derived", "weather_common.csv")
with open(path + ".tmp", "w", newline="") as fh:
    w = csv.DictWriter(fh, list(rows[0])); w.writeheader(); w.writerows(rows)
os.replace(path + ".tmp", path)
json.dump(dict(about="Leave-one-winter-out accuracy of the Siberia gust estimate built from ERA5 and SNOTEL only (days with a station reading).", estimate=report), open(os.path.join(ROOT, "results", "weather_common.json"), "w"), indent=1)
print(len(rows), "days;", {W: sum(1 for r in rows if r["winter"] == W and r["gust_src"] == "station") for W in WINTERS})
for kind in report: print(kind, {W: (v["mae_mph"], v["r2"]) for W, v in report[kind].items()})
cols = [c for c in rows[0] if c not in ("date", "winter", "gust_src", "gust_src_early")]
print("blank share by winter (any column):", {W: round(sum(r[c] is None for r in rows if r["winter"] == W for c in cols) / (sum(1 for r in rows if r["winter"] == W) * len(cols)), 2) for W in WINTERS})
