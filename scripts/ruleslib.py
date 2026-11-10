"""Shared rule-fitting code: the one place the project defines how a rule is fitted and scored.
Used by baselines.py and build_app_model.py (recover_rules.py defines the same functions; keep them identical).
Loads data/derived/lift_days.csv, which build_dataset.py writes."""
import os, csv
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
# Views (environment switches; outputs get a suffix so the headline files never change):
#   (none)                        the 8 core winters 2018-19 to 2025-26: the headline
#   LIFT_DAYS=lift_days_11w       all 11 winters                                    -> _11w
#   LIFT_DAYS=lift_days_11w DROP_WINTERS=2015-16   10 winters: adds 2016-18 but no estimated wind -> _10w
#   NAMED_ONLY=1                  only lift-days a roster post named (no closure-created rows)    -> _named  (combines with the others)
LIFT_DAYS = os.environ.get("LIFT_DAYS", "lift_days")
DROP_WINTERS = [w for w in os.environ.get("DROP_WINTERS", "").split(",") if w]
NAMED_ONLY = os.environ.get("NAMED_ONLY") == "1"
SUF = ("" if LIFT_DAYS == "lift_days" else "_10w" if DROP_WINTERS == ["2015-16"] else "_11w") + ("_named" if NAMED_ONLY else "")
VIEW = {"": "the 8 core winters (2018-19 to 2025-26)", "_11w": "all 11 winters (2015-16 to 2025-26; 2015-16 wind is an estimate, 2016-18 wind is hourly from two stations)", "_10w": "10 winters (2016-17 to 2025-26; no estimated wind)"}[SUF.replace("_named", "")] + (", named-roster lift-days only" if NAMED_ONLY else "")
rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "derived", LIFT_DAYS + ".csv"))))
NUM = ["early_gust", "early_spd", "day_gust", "day_spd", "fnt_day_gust", "temp_base", "avy", "swe24", "swe6", "prec24s", "new_snow24", "depth"]
for r in rows:
    for k in NUM: r[k] = float(r[k]) if r[k] != "" else None
    for k in ("held", "held_wind", "held_unstated", "held_patrol", "held_mech", "held_weather"): r[k] = int(r[k])
    r["scheduled"] = r["scheduled"] == "True"
    r["closed_all"] = int(r["closed_all"]); r["in_season"] = int(r["in_season"]); r["covid_era"] = r.get("covid_era", "")
    for k in ("sib_h40", "sib_h60"): r[k] = float(r[k]) if r[k] != "" else None
rows = [r for r in rows if r["winter"] not in DROP_WINTERS]
rows = [r for r in rows if r["in_season"] == 1]            # season windows (rules/season_windows.json + the first roster day): days the side was not open are not evidence
for r in rows:
    r["expected"] = r["scheduled"] or r["closed_all"] == 1      # a lift under a whole-side closure was meant to run that day even though no roster was posted
    r["fit_ok"] = r["expected"] and r["covid_era"] != "restricted"   # winter 2020-21 ran under COVID operating rules (reservations, capacity): lifts ran or not for non-weather reasons, so it stays in the replay but is left out of lift-level fits
if NAMED_ONLY: rows = [r for r in rows if r["scheduled"]]
WINTERS = sorted({r["winter"] for r in rows})
FEATS = ["early_gust", "day_gust", "early_spd", "day_spd", "fnt_day_gust", "avy", "temp_base", "swe24", "swe6", "prec24s", "new_snow24"]   # same list as recover_rules.py
def f1(tp, fp, fn): return 2 * tp / (2 * tp + fp + fn) if tp else 0.0
def prf(c):
    tp, fp, fn = c["tp"], c["fp"], c["fn"]
    return dict(tp=tp, fp=fp, fn=fn, precision=round(tp / (tp + fp), 3) if tp + fp else None, recall=round(tp / (tp + fn), 3) if tp + fn else None, f1=round(f1(tp, fp, fn), 3))
def add(c, pred, y): c["tp"] += bool(pred and y); c["fp"] += bool(pred and not y); c["fn"] += bool((not pred) and y)
def fit(rs, y, feats):
    """best single threshold rule 'feature >= t' by F1 (same search as recover_rules.py)"""
    best = None
    for f in feats:
        sub = [r for r in rs if r[f] is not None]; vals = sorted({r[f] for r in sub})
        if len(vals) < 3: continue
        step = max(1, len(vals) // 40)
        for t in vals[::step]:
            tp = sum(1 for r in sub if r[f] >= t and r[y]); fp = sum(1 for r in sub if r[f] >= t and not r[y]); fn = sum(1 for r in sub if r[f] < t and r[y])
            s = f1(tp, fp, fn)
            if best is None or s > best[0]: best = (s, f, t)
    return best
NEW = lambda: dict(tp=0, fp=0, fn=0)
