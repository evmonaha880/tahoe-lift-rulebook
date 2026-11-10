"""Leave-one-winter-out comparison of the learned rules against simple wind rules, at day level and lift level.
Reads data/derived/lift_days.csv (built by build_dataset.py). Writes results/baselines.json.
usage: python3 -I scripts/baselines.py
Method: for each winter, fit on the other seven, score on that winter; counts are summed across winters for the pooled figures.
Lift level uses expected lift-days only (a roster post named the lift as meant to run, or the whole side was closed that day and the lift normally runs), and only the lift-winters the per-lift rules can score (lift has >=40 days overall, >=25 training rows, >=10 test rows),
so every method below is scored on exactly the same rows."""
import os, csv, json, collections
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ruleslib import *
out = {"method": __doc__.split("\n")[1] + " " + __doc__.split("\n")[2], "day_level": {}, "lift_level": {}}
# ---------------- day level: did any lift hold for wind that day (days with at least one lift post)
days = {}
for r in rows:
    d = days.setdefault((r["winter"], r["date"]), dict(winter=r["winter"], day_gust=r["day_gust"], held_wind=0))
    d["held_wind"] |= r["held_wind"]
D = list(days.values()); pool = {"learned": NEW(), "mph25": NEW()}
for W in WINTERS:
    tr = [d for d in D if d["winter"] != W and d["day_gust"] is not None]; te = [d for d in D if d["winter"] == W and d["day_gust"] is not None]
    _, _, t = fit(tr, "held_wind", ["day_gust"]); a, b = NEW(), NEW()
    for d in te: add(a, d["day_gust"] >= t, d["held_wind"]); add(b, d["day_gust"] >= 25, d["held_wind"])
    for k, c in (("tp", a), ("fp", a), ("fn", a)): pool["learned"][k] += c[k]
    for k in ("tp", "fp", "fn"): pool["mph25"][k] += b[k]
    out["day_level"][W] = dict(n_days=len(te), line_mph=round(t, 1), learned=prf(a), mph25=prf(b))
out["day_level"]["pooled"] = dict(learned=prf(pool["learned"]), mph25=prf(pool["mph25"]))
# ---------------- the same day-level line, using only what is known by 9am (early_gust, 05:00-09:00) instead of the full-day maximum
dm = {}
for r in rows:
    d = dm.setdefault((r["winter"], r["date"]), dict(winter=r["winter"], g=r["early_gust"], held_wind=0)); d["held_wind"] |= r["held_wind"]
DM = list(dm.values()); poolm = NEW(); lines_m = []
for W in WINTERS:
    tr = [d for d in DM if d["winter"] != W and d["g"] is not None]; te = [d for d in DM if d["winter"] == W and d["g"] is not None]
    if not tr or not te: continue
    _, _, t = fit(tr, "held_wind", ["g"]); lines_m.append(t)
    for d in te: add(poolm, d["g"] >= t, d["held_wind"])
out["day_level_morning"] = dict(pooled=prf(poolm), line_mph_min=round(min(lines_m), 1), line_mph_max=round(max(lines_m), 1), feature="early_gust: maximum gust 05:00-09:00 at the ridge stations", full_day_f1=out["day_level"]["pooled"]["learned"]["f1"])
# ---------------- lift level, on two row sets
def lift_level(S, feats=None, gust="day_gust"):
    feats = feats or FEATS      # feats: what each lift's own rule may pick from; gust: the column the single line and the 25 mph rule read
    cnt = collections.Counter(r["lift"] for r in S); LIFTS = sorted(l for l, n in cnt.items() if n >= 40)
    M = ["per_lift_called_at_50pct", "per_lift_any_pass", "best_single_wind_line", "mph25"]
    agg = {W: {m: NEW() for m in M} for W in WINTERS}; nrows = collections.Counter(); lines = {}; fits = {}
    for L in LIFTS:
        full = [r for r in S if r["lift"] == L]
        for W in WINTERS:
            tr = [r for r in full if r["winter"] != W]; te = [r for r in full if r["winter"] == W]
            if len(tr) < 25 or len(te) < 10: continue
            b = fit(tr, "held", feats)
            if b: fits[(L, W)] = (b[1], b[2], tr, te)
    for W in WINTERS:
        trainrows = [r for r in S if r["lift"] in LIFTS and r["winter"] != W and r[gust] is not None]
        b = fit(trainrows, "held", [gust]); lines[W] = b[2] if b else None
    for (L, W), (f, t, tr, te) in fits.items():
        above = [r for r in tr if r[f] is not None and r[f] >= t]
        p_hold = sum(r["held"] for r in above) / len(above) if above else 0.0       # the rule's own hit rate on the training winters
        for r in te:
            fire = r[f] is not None and r[f] >= t
            add(agg[W]["per_lift_any_pass"], fire, r["held"]); add(agg[W]["per_lift_called_at_50pct"], fire and p_hold >= 0.5, r["held"])
            add(agg[W]["mph25"], r[gust] is not None and r[gust] >= 25, r["held"])
            if lines[W] is not None: add(agg[W]["best_single_wind_line"], r[gust] is not None and r[gust] >= lines[W], r["held"])
            nrows[W] += 1
    pooled = {m: NEW() for m in M}; res = {}
    for W in WINTERS:
        if not nrows[W]: continue
        res[W] = dict(n_lift_days=nrows[W], wind_line_mph=round(lines[W], 1) if lines[W] else None, hold_rate=None, **{m: prf(agg[W][m]) for m in M})
        for m in M:
            for k in ("tp", "fp", "fn"): pooled[m][k] += agg[W][m][k]
    res["pooled"] = dict(n_lift_days=sum(nrows.values()), **{m: prf(pooled[m]) for m in M})
    win = collections.Counter(max(M, key=lambda m: res[W][m]["f1"]) for W in WINTERS if W in res)
    res["winters_won_by_method"] = dict(win)
    return res
SCHED = [r for r in rows if r["fit_ok"]]
out["lift_level"] = lift_level(SCHED)                                   # headline: the roster said the lift was meant to run
out["lift_level_all_named"] = lift_level(rows)                          # includes lifts that appear only because a post named them (76% held): inflated, shown to reconcile
out["lift_level_without_began_on_hold"] = lift_level([r for r in SCHED if r["began_on_hold"] != "1"])   # rows where the lift began the day on hold are held by construction (decision 58): shown without them so the headline is not read alone
out["lift_level_without_began_on_hold"]["row_set"] = "expected lift-days, minus lifts that began the day on hold (those are held by definition until their reopening post)"
MORNING_FEATS = [f for f in FEATS if f not in ("day_gust", "day_spd", "fnt_day_gust")]      # only what is known by about 9 am (rules/features.json "asof"); the headline lift-level numbers above may pick same-day features
out["lift_level_by_9am"] = lift_level(SCHED, MORNING_FEATS, "early_gust")
out["lift_level_by_9am"]["row_set"] = "same lift-days as the headline, but every rule (each lift's own, the single wind line, the 25 mph rule) reads only features known by about 9 to 10 am: the 05:00-09:00 ridge gust (early_gust), early wind speed, avalanche rating, base temperature and snowfall"
out["lift_level"]["row_set"] = "expected lift-days only (scheduled, plus lifts that normally run on a whole-side closure day)"; out["lift_level_all_named"]["row_set"] = "all lift-days incl. unscheduled lifts named only in hold/delay posts (selection-biased)"
dw = sum(1 for W in WINTERS if out["day_level"][W]["learned"]["f1"] > out["day_level"][W]["mph25"]["f1"])
out["day_level"]["winters_learned_beats_25mph"] = f"{dw} of {len(WINTERS)}"
json.dump(out, open(os.path.join(ROOT, "results", f"baselines{SUF}.json"), "w"), indent=1)
# ---------------- print
print("DAY LEVEL (learned day-gust line vs 25 mph)")
for W in WINTERS + ["pooled"]:
    x = out["day_level"][W]; a, b = x["learned"], x["mph25"]
    print(f"  {W:8} {'line '+str(x['line_mph']) if W!='pooled' else '':10} learned P{a['precision']} R{a['recall']} F1 {a['f1']}   25mph P{b['precision']} R{b['recall']} F1 {b['f1']}")
for key in ("lift_level", "lift_level_all_named"):
    print("\nLIFT LEVEL:", out[key]["row_set"])
    for W in WINTERS + ["pooled"]:
        if W not in out[key]: continue
        x = out[key][W]
        print(f"  {W:8} n={x['n_lift_days']:5} " + "  ".join(f"{m[:12]} P{x[m]['precision']} R{x[m]['recall']} F{x[m]['f1']}" for m in ["per_lift_called_at_50pct", "per_lift_any_pass", "best_single_wind_line", "mph25"]))
    print("  winters won by method (lift-level F1):", out[key]["winters_won_by_method"])
print("\nday level: learned line beats 25 mph in", out["day_level"]["winters_learned_beats_25mph"], "winters")

# ---------------- docs/RESULTS.md (generated from the same numbers)
def row(label, x): return f"| {label} | {x['precision']} | {x['recall']} | {x['f1']} |"
_NW = {7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven"}
def pct(x): return "n/a" if x is None else x
L = out["lift_level"]; LM = out["lift_level_by_9am"]; LA = out["lift_level_all_named"]; LB = out["lift_level_without_began_on_hold"]; DL = out["day_level"]
names = {"per_lift_called_at_50pct": "Per-lift rules, called at 50% odds", "per_lift_any_pass": "Per-lift rules, called whenever the lift passes its line",
         "best_single_wind_line": "Best single wind line (learned on the other winters)", "mph25": "25 mph rule"}
md = ["# Results: do the recovered rules predict winters they never saw?", "",
      f"Generated by `python3 -I scripts/baselines.py` from `data/derived/{LIFT_DAYS}.csv`; raw numbers in `results/baselines{SUF}.json`.", "",
      *([f"**View: {VIEW}.**", ""] if SUF else []),
      f"**Method.** Leave-one-winter-out: each rule is fitted on the other {_NW[len(WINTERS) - 1]} winters and scored on the one left out, rotated through all {_NW[len(WINTERS)]}. Pooled figures add the counts across the {_NW[len(WINTERS)]} test winters. "
      "Precision = of the calls \"will hold\", how many held; recall = of the holds, how many were called; F1 combines them. "
      "Day level asks: did any lift hold for wind that day? Lift level asks: did this expected lift hold or close that day (any stated cause, including a whole-mountain closure)?", "",
      f"## Day level ({sum(DL[W]['n_days'] for W in WINTERS):,} days with lift posts and wind data)", "",
      "| Held-out winter | Learned line (mph) | Learned P / R / F1 | 25 mph P / R / F1 |", "|---|---|---|---|"]
for W in WINTERS:
    x = DL[W]; a, b = x["learned"], x["mph25"]
    md.append(f"| {W} | {x['line_mph']} | {a['precision']} / {a['recall']} / **{a['f1']}** | {b['precision']} / {b['recall']} / {b['f1']} |")
a, b = DL["pooled"]["learned"], DL["pooled"]["mph25"]
md += [f"| **Pooled** | | {a['precision']} / {a['recall']} / **{a['f1']}** | {b['precision']} / {b['recall']} / {b['f1']} |", "",
       f"**Where the simple rule wins at day level: {'nowhere' if dw == len(WINTERS) else 'in ' + str(len(WINTERS) - dw) + ' of ' + str(len(WINTERS)) + ' winters'}.** The learned line (about 60 mph gusts, stable across winters) beats the 25 mph rule in {DL['winters_learned_beats_25mph']} winters. "
       f"The 25 mph rule catches nearly every hold (recall about 1.0) only because it calls almost every windy day a hold (pooled precision {b['precision']}).", "",
       "## Lift level, headline: expected lift-days only", "",
       f"{L['pooled']['n_lift_days']:,} expected lift-days scored. Expected means a roster post named the lift as meant to run that day, or the whole side was closed that day and the lift normally runs (whole-mountain closures count as holds), so these are fair denominators.", "",
       "| Method (pooled) | Precision | Recall | F1 |", "|---|---|---|---|"]
for m in names: md.append(row(names[m], L["pooled"][m]))
md += ["", "Per winter, lift-level F1:", "", "| Held-out winter | Scored lift-days | " + " | ".join(names[m] for m in names) + " |", "|---|---|---|---|---|---|"]
for W in WINTERS:
    if W in L: md.append(f"| {W} | {L[W]['n_lift_days']:,} | " + " | ".join(str(L[W][m]['f1']) for m in names) + " |")
big = [W for W in WINTERS if W in L and L[W]["n_lift_days"] >= 400]
_sd = collections.defaultdict(list)
for _r in csv.DictReader(open(os.path.join(ROOT, "data", "derived", LIFT_DAYS + ".csv"))):
    if _r["winter"] not in DROP_WINTERS and _r["side"] in ("palisades", "alpine") and _r["in_season"] == "1" and _r["covid_era"] == "": _sd[(_r["date"], _r["side"])].append(_r)
_named = {k for k, rs in _sd.items() if any(x["scheduled"] == "True" for x in rs)}
def _hi(keys):
    g = [float(x[0]["day_gust"]) for k, x in _sd.items() if k in keys and x[0]["day_gust"] not in ("", None)]; return (sum(v >= 60 for v in g) / len(g)) if g else 0
out["coverage"] = {"side_days": len(_sd), "named_side_days": len(_named), "named_share": round(len(_named) / max(len(_sd), 1), 3), "gust60_named": round(_hi(_named), 3), "gust60_left_out": round(_hi(set(_sd) - _named), 3)}
json.dump(out, open(os.path.join(ROOT, "results", f"baselines{SUF}.json"), "w"), indent=1)
_cov = (f"**Coverage.** Lift-level rules are fitted on the {len(_named):,} of {len(_sd):,} side-days ({100*len(_named)/max(len(_sd),1):.0f}%) whose schedule post names the lifts, mostly 2021-22 to 2023-24. "
        f"On the one measure checked, the side-days left out are {'windier' if _hi(set(_sd)-_named) > _hi(_named) + 0.005 else 'less windy' if _hi(set(_sd)-_named) < _hi(_named) - 0.005 else 'about as windy'}: {100*_hi(set(_sd)-_named):.0f}% have a crest gust of 60 mph or more, against {100*_hi(_named):.0f}% of the named ones. That does not show the selection is harmless: days with no named roster have rows mainly when a whole-side closure creates them (see the named-roster view). A sensitivity run that infers rosters where a stated lift count allows it (`docs/SENSITIVITY.md`) is data-limited and moves the pooled scores by about 0.01.")
md += ["", f"Only {', '.join(big)} have enough expected lift-days to mean much; the other winters score on fewer lift-days (the counts are in the table) because most of their posts give a count (\"32 lifts scheduled\") rather than names.", "",
       _cov, "",
       f"**Morning versus full-day wind.** The day-level line above uses the strongest gust of the whole day (06:00 to 16:00), which includes hours after a hold. Using only the gust known by 9am (05:00 to 09:00) gives a pooled F1 of {out['day_level_morning']['pooled']['f1']} against {DL['pooled']['learned']['f1']} for the full day, with a learned line of {out['day_level_morning']['line_mph_min']} to {out['day_level_morning']['line_mph_max']} mph. The full-day numbers describe a day; the morning numbers are what a call at opening could have used.", "",
       "**Simple rules against per-lift rules at lift level** (same-day features: the whole-day gust is hindsight; the by-9am version is further down):",
       f"- One learned wind line scores a pooled F1 of {L['pooled']['best_single_wind_line']['f1']}, against {L['pooled']['per_lift_any_pass']['f1']} for per-lift rules (any pass) and {L['pooled']['per_lift_called_at_50pct']['f1']} for per-lift rules at 50% odds: fitting each lift separately adds {L['pooled']['per_lift_any_pass']['f1'] - L['pooled']['best_single_wind_line']['f1']:+.3f} of F1.",
       f"- The 25 mph rule has the highest recall ({L['pooled']['mph25']['recall']}) but very low precision ({L['pooled']['mph25']['precision']}), so its pooled F1 is the lowest ({L['pooled']['mph25']['f1']}). It tops the F1 table in {L['winters_won_by_method'].get('mph25', 0)} of {len([W for W in WINTERS if W in L])} winters ({", ".join(W for W in WINTERS if W in L and L[W]["mph25"]["f1"] >= max(L[W][m]["f1"] for m in names)) or "none"}); the learned methods win pooled, not in every winter.",
       "- Per-lift rules called at 50% odds have the best precision of the learned methods, at the cost of recall: use them if a false alarm is costlier than a miss.", "",
       "## Lift level, without the lifts that began the day on hold", "",
       f"Under decision 58 a lift that begins the day on hold counts as scheduled and held until its reopening post, so those lift-days are held by definition. They are {L['pooled']['n_lift_days'] - LB['pooled']['n_lift_days']:,} of the {L['pooled']['n_lift_days']:,} scored rows. Dropping them leaves {LB['pooled']['n_lift_days']:,} rows, the harder question of whether a lift that was scheduled to run was held. Read the headline and this table together.", "",
       "| Method (pooled) | Precision | Recall | F1 |", "|---|---|---|---|"] + [row(names[m], LB["pooled"][m]) for m in names] + ["",
       "## Lift level, reconciliation: all named lift-days (not the headline)", "",
       f"Including lift-days where a lift appears only because a post named it as held or delayed ({LA['pooled']['n_lift_days']:,} rows) makes every method look better, because those extra rows are about 76% held by construction. "
       "We show it because the demo app may use this set.", "", "| Method (pooled) | Precision | Recall | F1 |", "|---|---|---|---|"]
for m in names: md.append(row(names[m], LA["pooled"][m]))
md += ["", f"On this set the 25 mph rule has the best F1 in {LA['winters_won_by_method'].get('mph25', 0)} of {len([W for W in WINTERS if W in LA])} winters, and the learned methods win the rest.", "",
       "## Lift level, using only what is known by 9am", "",
       f"The lift-level tables above let every rule read the whole day's gust (`day_gust`, hindsight: it includes hours after a hold begins) and each lift's own rule may pick other same-day features. This table keeps the same lift-days but lets every method read only what is known by about 9am: the 05:00-09:00 ridge gust, early wind speed, avalanche rating, base temperature (06:00-10:00 mean) and snowfall. Two caveats: the 05:00-09:00 window runs past holds posted earlier in the morning, and lift-days that began on hold (decision 58) are held by construction. It is the fairer test of a morning call, and the number to quote if the claim is \"predicts the morning of\".", "",
       "| Method (pooled) | Precision | Recall | F1 |", "|---|---|---|---|"] + [row(names[m], LM["pooled"][m]) for m in names] + ["",
       "## Limits", "",
       "- The outcome is the ops account's posts; a hold nobody posted is invisible, and a post parsed wrongly is a wrong label (about 90% of posts right on a 240-post hand check, plus or minus 5 points).",
       "- Per-lift results rest mainly on three winters (2021-22 to 2023-24) that list lifts by name on most days.",
       "- Wind features are crest sensors (Siberia, Alpine Summit); the Funitel-top wind is partly an estimate, and the avalanche and new-snow fixes are described in DATA_SOURCES.md.",
       "- No rule here is a forecast of tomorrow: day-level inputs use that day's own maximum gust."]
open(os.path.join(ROOT, "docs", f"RESULTS{SUF}.md"), "w").write("\n".join(md) + "\n")
print(f"wrote docs/RESULTS{SUF}.md and results/baselines{SUF}.json")
