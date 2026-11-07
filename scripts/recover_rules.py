"""Recover hold rules from lift_days.csv and test them on winters the rule never saw (leave-one-winter-out).
Observed = outcome stated in a post. Inferred = a threshold learned from weather. They are never merged.
usage: python3 -I scripts/recover_rules.py   -> rules/rulebook_palisades.json, results/loo_results.json"""
import os, csv, json, itertools, collections
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
rows = list(csv.DictReader(open(os.path.join(ROOT, "data", "derived", "lift_days.csv"))))
NUM = ["early_gust", "early_spd", "day_gust", "day_spd", "fnt_day_gust", "temp_base", "avy", "swe24", "swe6", "prec24s", "new_snow24", "depth"]
for r in rows:
    for k in NUM: r[k] = float(r[k]) if r[k] != "" else None
    for k in ("held", "held_wind", "held_unstated", "held_patrol", "held_mech", "held_weather"): r[k] = int(r[k])
    r["scheduled"] = r["scheduled"] == "True"
WINTERS = sorted({r["winter"] for r in rows})
FEATS = ["early_gust", "day_gust", "early_spd", "day_spd", "avy", "temp_base", "swe24", "swe6", "prec24s"]
def f1(tp, fp, fn): return 2 * tp / (2 * tp + fp + fn) if tp else 0.0
def score(rs, pred, y):
    tp = sum(1 for r in rs if pred(r) and r[y]); fp = sum(1 for r in rs if pred(r) and not r[y]); fn = sum(1 for r in rs if not pred(r) and r[y])
    return dict(tp=tp, fp=fp, fn=fn, n=len(rs), precision=round(tp / (tp + fp), 3) if tp + fp else None,
                recall=round(tp / (tp + fn), 3) if tp + fn else None, f1=round(f1(tp, fp, fn), 3), base_rate=round(sum(r[y] for r in rs) / len(rs), 3) if rs else None)
def fit(rs, y, feats=FEATS, ge=True):
    """best single threshold rule 'feature >= t' by F1 on rs"""
    best = None
    for f in feats:
        vals = sorted({r[f] for r in rs if r[f] is not None})
        if len(vals) < 3: continue
        step = max(1, len(vals) // 40)
        for t in vals[::step]:
            s = score([r for r in rs if r[f] is not None], lambda r: r[f] >= t, y)
            if best is None or s["f1"] > best[0]["f1"]: best = (s, f, t)
    return best
BASE = lambda r: r["day_gust"] is not None and r["day_gust"] >= 25
res = {"day_level": {}, "lift_level": {}}
# ---------- day level: did ANY lift hold for wind that day? (days with at least one lift post)
days = {}
for r in rows:
    d = days.setdefault((r["winter"], r["date"]), dict(r, held_wind=0, held=0, held_patrol=0, held_mech=0, held_weather=0))
    for k in ("held_wind", "held", "held_patrol", "held_mech", "held_weather"): d[k] |= r[k]
D = list(days.values())
print(f"DAY LEVEL: {len(D)} days with lift posts; wind-hold days {sum(d['held_wind'] for d in D)}; any-hold days {sum(d['held'] for d in D)}")
print(f"{'held-out winter':16} {'n days':>6} {'base rate':>9} | {'learned rule':32} {'F1':>5} {'prec':>5} {'rec':>5} | {'baseline gust>=25':17} {'F1':>5} {'prec':>5} {'rec':>5}")
for W in WINTERS:
    tr = [d for d in D if d["winter"] != W]; te = [d for d in D if d["winter"] == W]
    s, f, t = fit(tr, "held_wind"); sc = score([d for d in te if d[f] is not None], lambda r: r[f] >= t, "held_wind"); bs = score(te, BASE, "held_wind")
    print(f"{W:16} {len(te):6} {sc['base_rate']:9.1%} | {f+' >= '+str(t):32} {sc['f1']:5.2f} {sc['precision'] or 0:5.2f} {sc['recall'] or 0:5.2f} | {'':17} {bs['f1']:5.2f} {bs['precision'] or 0:5.2f} {bs['recall'] or 0:5.2f}")
    res["day_level"][W] = dict(rule=f"{f} >= {t}", learned=sc, baseline=bs, trained_on=[w for w in WINTERS if w != W])
def fit_pair(rs, y, feats):
    """best 'A >= a AND B >= b' rule by F1 (tries a small grid of quantile thresholds)"""
    best = None; cand = {}
    for f in feats:
        vals = sorted(r[f] for r in rs if r[f] is not None)
        if len(vals) > 20: cand[f] = sorted({vals[int(len(vals) * q)] for q in (.3, .45, .6, .7, .8, .9, .95)})
    for f1_, f2_ in itertools.combinations(cand, 2):
        for a in cand[f1_]:
            for b in cand[f2_]:
                sub = [r for r in rs if r[f1_] is not None and r[f2_] is not None]
                sc = score(sub, lambda r: r[f1_] >= a and r[f2_] >= b, y)
                if best is None or sc["f1"] > best[0]["f1"]: best = (sc, (f1_, a), (f2_, b))
    return best
# ---------- cause families at day level: is it really "not wind only"?
print("\nCAUSE FAMILIES (day level, leave-one-winter-out; F1 of the learned rule, 'n' = days with that stated cause)")
res["cause_families"] = {}
for fam, label in (("held_wind", "wind"), ("held_patrol", "snow safety / avalanche control"), ("held_mech", "mechanical"), ("held_weather", "lightning / ice / rain")):
    n = sum(d[fam] for d in D); line = []; rules = []
    for W in WINTERS:
        tr = [d for d in D if d["winter"] != W]; te = [d for d in D if d["winter"] == W]; b = fit(tr, fam)
        if not b or not sum(d[fam] for d in tr): line.append("  n/a"); continue
        _, f, t = b; sc = score([d for d in te if d[f] is not None], lambda r: r[f] >= t, fam)
        if sc["base_rate"] is None: line.append("  n/a (feature missing)"); continue
        line.append(f"{sc['f1']:5.2f} (base {sc['base_rate']:.0%})"); rules.append(f"{f}>={t}")
    full = fit(D, fam)
    print(f"{label:34} n={n:3} | " + " | ".join(line) + f" | best feature on all winters: {full[1]+' >= '+str(round(full[2], 2)) if full else '-'}")
    res["cause_families"][label] = dict(days=n, folds=dict(zip(WINTERS, line)), best=(full[1], full[2]) if full else None)

print("\nSNOW-SAFETY HOLDS, two-feature rule (snow AND avalanche danger etc.), leave-one-winter-out:")
SNOWF = ["prec24s", "swe24", "swe6", "avy", "depth", "temp_base"]
for W in WINTERS:
    tr = [d for d in D if d["winter"] != W]; te = [d for d in D if d["winter"] == W]; b = fit_pair(tr, "held_patrol", SNOWF)
    if not b: continue
    (_, (fa, a), (fb, bb)) = b; sub = [d for d in te if d[fa] is not None and d[fb] is not None]
    if not sub: continue
    sc = score(sub, lambda r: r[fa] >= a and r[fb] >= bb, "held_patrol"); allpos = 2 * sc["base_rate"] / (1 + sc["base_rate"])
    print(f"  {W}: {fa}>={a:.2f} AND {fb}>={bb:.2f} -> F1 {sc['f1']:.2f} (precision {sc['precision']}, recall {sc['recall']}); 'always say hold' would score {allpos:.2f}")
# ---------- lift level (scheduled lift-days only: the roster says the lift was meant to run)
S = [r for r in rows if r["scheduled"]]
cnt = collections.Counter(r["lift"] for r in S); LIFTS = [l for l, n in cnt.items() if n >= 40]
print(f"\nLIFT LEVEL: {len(S)} scheduled lift-days, {len(LIFTS)} lifts with >=40 days")
agg_l = collections.defaultdict(lambda: dict(tp=0, fp=0, fn=0)); agg_b = collections.defaultdict(lambda: dict(tp=0, fp=0, fn=0))
book = []
for L in sorted(LIFTS):
    full = [r for r in S if r["lift"] == L]; fs = FEATS + (["fnt_day_gust"] if L == "Funitel" else [])
    s, f, t = fit(full, "held", fs)
    above = [r for r in full if r[f] is not None and r[f] >= t]; below = [r for r in full if r[f] is not None and r[f] < t]
    rule = dict(lift=L, rule=f"{f} >= {t}", tag="inferred", scheduled_days=len(full), hold_rate_above=round(sum(r['held'] for r in above) / max(1, len(above)), 3), n_above=len(above),
                hold_rate_below=round(sum(r['held'] for r in below) / max(1, len(below)), 3), n_below=len(below),
                observed_wind_stated_days=sum(r['held_wind'] for r in full), observed_held_days=sum(r['held'] for r in full),
                unstated_cause_days=sum(r['held_unstated'] for r in full), loo={})
    for W in WINTERS:
        tr = [r for r in full if r["winter"] != W]; te = [r for r in full if r["winter"] == W and r["scheduled"]]
        if len(tr) < 25 or len(te) < 10: continue
        b = fit(tr, "held", fs)
        if not b: continue
        _, ff, tt = b
        for r in te:
            p = r[ff] is not None and r[ff] >= tt; a = agg_l[W]; a["tp"] += p and r["held"]; a["fp"] += p and not r["held"]; a["fn"] += (not p) and r["held"]
            p2 = BASE(r); a2 = agg_b[W]; a2["tp"] += p2 and r["held"]; a2["fp"] += p2 and not r["held"]; a2["fn"] += (not p2) and r["held"]
    book.append(rule)
print(f"{'held-out winter':16} | {'learned per-lift rules':>30} | {'one global rule: gust>=25':>28}\n{'':16} | {'F1':>8} {'prec':>6} {'rec':>6} | {'F1':>8} {'prec':>6} {'rec':>6}")
for W in WINTERS:
    if W not in agg_l: continue
    a, b = agg_l[W], agg_b[W]
    pr = lambda x: (x["tp"] / (x["tp"] + x["fp"]) if x["tp"] + x["fp"] else 0, x["tp"] / (x["tp"] + x["fn"]) if x["tp"] + x["fn"] else 0)
    print(f"{W:16} | {f1(a['tp'], a['fp'], a['fn']):8.2f} {pr(a)[0]:6.2f} {pr(a)[1]:6.2f} | {f1(b['tp'], b['fp'], b['fn']):8.2f} {pr(b)[0]:6.2f} {pr(b)[1]:6.2f}")
    res["lift_level"][W] = dict(learned=dict(a, f1=round(f1(a['tp'], a['fp'], a['fn']), 3)), baseline=dict(b, f1=round(f1(b['tp'], b['fp'], b['fn']), 3)))
os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
json.dump(res, open(os.path.join(ROOT, "results", "loo_results.json"), "w"), indent=1)
json.dump(sorted(book, key=lambda r: -r["scheduled_days"]), open(os.path.join(ROOT, "rules", "rulebook_palisades.json"), "w"), indent=1)
print("\nTOP LIFT RULES (inferred, fitted on all winters):")
for r in sorted(book, key=lambda r: -r["scheduled_days"])[:12]:
    print(f"{r['lift']:22} {r['rule']:20} held {r['hold_rate_above']:.0%} of {r['n_above']:4} days above vs {r['hold_rate_below']:.0%} of {r['n_below']:4} below")

# ---------- two-stage lift rule: (1) one day-level wind rule, (2) each lift's own hold rate when that rule fires
YO = os.environ.get("OUTCOME", "held")
print(f"\n[outcome = {YO}]")
print("\nTWO-STAGE (day wind rule, then per-lift sensitivity), leave-one-winter-out, scheduled lift-days:")
print(f"{'held-out winter':16} | {'two-stage F1':>12} {'prec':>6} {'rec':>6} | {'gust>=25 F1':>12} | n lift-days, hold rate")
res["two_stage"] = {}
for W in WINTERS:
    trd = [d for d in D if d["winter"] != W]; s, f, t = fit(trd, "held_wind")
    trl = [r for r in S if r["winter"] != W and r[f] is not None]; fired = [r for r in trl if r[f] >= t]
    sens = {}
    for L in {r["lift"] for r in fired}:
        x = [r for r in fired if r["lift"] == L]
        sens[L] = (sum(r[YO] for r in x) + 0.15 * 2) / (len(x) + 2)   # shrunk toward 15% so tiny samples do not decide
    te = [r for r in S if r["winter"] == W and r[f] is not None]
    pred = lambda r: r[f] >= t and sens.get(r["lift"], 0) >= 0.35
    sc = score(te, pred, YO); bs = score(te, BASE, YO)
    print(f"{W:16} | {sc['f1']:12.2f} {sc['precision'] or 0:6.2f} {sc['recall'] or 0:6.2f} | {bs['f1']:12.2f} | {len(te)}, {sc['base_rate']:.1%}   rule: {f} >= {t}")
    res["two_stage"][W] = dict(rule=f"{f} >= {t}", learned=sc, baseline=bs, lift_sensitivity={k: round(v, 2) for k, v in sorted(sens.items(), key=lambda kv: -kv[1])})
json.dump(res, open(os.path.join(ROOT, "results", "loo_results" + ("" if YO == "held" else "_" + YO) + ".json"), "w"), indent=1)
# observed vs inferred: for hold-days with NO stated cause, does the learned wind rule fire?
s, f, t = fit(D, "held_wind")
unst = [d for d in D if d["held"] and not d["held_wind"]]
print(f"\nOBSERVED vs INFERRED (rule {f} >= {t}, fit on all winters): {sum(d['held_wind'] for d in D)} days with a STATED wind cause (observed); "
      f"{len(unst)} other hold-days, rule fires on {sum(1 for d in unst if d[f] is not None and d[f] >= t)} of them (inferred wind, not stated)")
