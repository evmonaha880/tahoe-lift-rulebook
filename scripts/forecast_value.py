"""Does the forecaster's morning gust (blog_forecast.csv) add to the station morning gust for calling a wind-hold day? Leave-one-winter-out over the 6 winters that have forecast posts.
Day level: did any lift hold for wind that day. Station = max gust 05:00-09:00 (early_gust). Forecast = ridgetop gust figure in the post for that day, posted by 09:00 (hi end of a range).
Three rules, each fitted on the other winters: station line, forecast line, 'either' (two lines, OR). Reported on (1) days that have a forecast figure and (2) every covered-winter day (a missing figure = no information).
DERIVED: the forecast figures are read from text by rule. usage: python3 -I scripts/forecast_value.py   -> results/forecast_value.json"""
import os, json, pandas as pd
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
l = pd.read_csv(os.path.join(ROOT, "data/derived/lift_days.csv"), usecols=["winter", "date", "in_season", "held_wind", "early_gust"]); l = l[l.in_season == 1]
d = l.groupby("date").agg(winter=("winter", "first"), held=("held_wind", "max"), early=("early_gust", "max")).reset_index()
f = pd.read_csv(os.path.join(ROOT, "data/derived/blog_forecast.csv")); f = f[(f.horizon == 0) & (f.asof_by_0900 == 1)].sort_values("posted_local").groupby("tgt_date").tail(1)
d = d.merge(f[["tgt_date", "fc_gust_hi"]], left_on="date", right_on="tgt_date", how="left")
cov = d[d.winter.isin(["2020-21", "2021-22", "2022-23", "2023-24", "2024-25", "2025-26"])].copy()
def f1(y, p):
    tp = (y & p).sum(); fp = ((~y) & p).sum(); fn = (y & ~p).sum(); return 2 * tp / (2 * tp + fp + fn) if tp else 0.0
def run(sub):
    tot = {k: [0, 0, 0] for k in ("station", "forecast", "either")}; byw = {k: {} for k in tot}
    for W in sorted(sub.winter.unique()):
        tr, te = sub[sub.winter != W], sub[sub.winter == W]
        if len(te) < 15: continue
        y, yt = tr.held.values.astype(bool), te.held.values.astype(bool)
        E, F, Et, Ft = tr.early.fillna(0).values, tr.fc_gust_hi.fillna(0).values, te.early.fillna(0).values, te.fc_gust_hi.fillna(0).values
        a = max(range(20, 140, 2), key=lambda t: f1(y, E >= t)); b = max(range(20, 140, 2), key=lambda t: f1(y, F >= t))
        a2, b2 = max(((x, z) for x in range(30, 100, 5) for z in range(30, 100, 5)), key=lambda xz: f1(y, (E >= xz[0]) | (F >= xz[1])))
        for k, p in (("station", Et >= a), ("forecast", Ft >= b), ("either", (Et >= a2) | (Ft >= b2))):
            byw[k][W] = round(f1(yt, p), 3); tot[k][0] += (yt & p).sum(); tot[k][1] += ((~yt) & p).sum(); tot[k][2] += (yt & ~p).sum()
    return {k: dict(pooled_f1=round(2 * v[0] / (2 * v[0] + v[1] + v[2]), 3), precision=round(v[0] / (v[0] + v[1]), 3), recall=round(v[0] / (v[0] + v[2]), 3), by_winter=byw[k]) for k, v in tot.items()}
out = dict(split="leave-one-winter-out, 6 winters with forecast posts (2020-21 to 2025-26)", as_of="morning: station 05:00-09:00; forecast posted by 09:00",
           days_covered=len(cov), days_with_forecast_figure=int(cov.fc_gust_hi.notna().sum()), wind_hold_days=int(cov.held.sum()),
           on_days_with_forecast_figure=run(cov[cov.fc_gust_hi.notna()]), on_all_covered_days=run(cov))
json.dump(out, open(os.path.join(ROOT, "results/forecast_value.json"), "w"), indent=1)
for k in ("on_days_with_forecast_figure", "on_all_covered_days"):
    print(k, {m: out[k][m]["pooled_f1"] for m in out[k]})
