"""Models 1 and 2 beside the single wind line, same rows, same leave-one-winter-out split, same by-9am-only inputs.
  Model 1 (flexible ceiling): gradient-boosted trees (sklearn HistGradientBoostingClassifier).
  Model 2 (readable): a decision tree of depth 3 (sklearn DecisionTreeClassifier), printed as if-then rules.
  Baselines on the same rows: best single early_gust line, and the 25 mph rule on early_gust.
Inputs (all known by about 9-10 am): early_gust, early_spd, avy, temp_base, swe24, swe6, prec24s, new_snow24, month, side, lift (one-hot).
Rows: expected lift-days (ruleslib SCHED rows). Views are set by the same environment switches as baselines.py (see ruleslib.py).
usage: python3 -I scripts/models.py   (needs scikit-learn; not part of run_all.sh)  -> results/models{SUF}.json, docs/MODELS{SUF}.md"""
import os, sys, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier, export_text
from ruleslib import *
NUMF = ["early_gust", "early_spd", "avy", "temp_base", "swe24", "swe6", "prec24s", "new_snow24"]
S = [r for r in rows if r["fit_ok"]]
LIFTS = sorted({r["lift"] for r in S})
for r in S:
    r["month"] = int(r["date"][5:7])
COLS = NUMF + ["month", "side_palisades"] + ["lift=" + l for l in LIFTS]
def X(rs):
    out = np.full((len(rs), len(COLS)), np.nan)
    for i, r in enumerate(rs):
        for j, k in enumerate(NUMF): out[i, j] = np.nan if r[k] is None else r[k]
        out[i, len(NUMF)] = r["month"]; out[i, len(NUMF) + 1] = 1.0 if r["side"] == "palisades" else 0.0
        out[i, len(NUMF) + 2 + LIFTS.index(r["lift"])] = 1.0
    return out
def Y(rs): return np.array([r["held"] for r in rs])
def counts(pred, y): return dict(tp=int(((pred == 1) & (y == 1)).sum()), fp=int(((pred == 1) & (y == 0)).sum()), fn=int(((pred == 0) & (y == 1)).sum()))
M = ["model1_boosted_trees", "model2_tree_depth3", "single_early_gust_line", "mph25_early_gust"]
agg = {W: {m: NEW() for m in M} for W in WINTERS}
for W in WINTERS:
    tr = [r for r in S if r["winter"] != W]; te = [r for r in S if r["winter"] == W]
    if not te: continue
    Xtr, ytr, Xte, yte = X(tr), Y(tr), X(te), Y(te)
    keep = [j for j in range(Xtr.shape[1]) if len(np.unique(Xtr[:, j][~np.isnan(Xtr[:, j])])) >= 2]      # drop a column with no variation in these training winters (e.g. a lift absent from them)
    Xtr, Xte = Xtr[:, keep], Xte[:, keep]
    m1 = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.06, max_depth=4, random_state=0).fit(Xtr, ytr)
    m2 = DecisionTreeClassifier(max_depth=3, min_samples_leaf=50, random_state=0).fit(Xtr, ytr)
    b = fit([r for r in tr if r["early_gust"] is not None], "held", ["early_gust"]); line = b[2] if b else None
    g = np.array([np.nan if r["early_gust"] is None else r["early_gust"] for r in te])
    preds = {M[0]: m1.predict(Xte), M[1]: m2.predict(Xte),
             M[2]: (np.nan_to_num(g, nan=-1) >= line).astype(int) if line is not None else np.zeros(len(te), int),
             M[3]: (np.nan_to_num(g, nan=-1) >= 25).astype(int)}
    for m in M:
        c = counts(preds[m], yte)
        for k in c: agg[W][m][k] += c[k]
pooled = {m: NEW() for m in M}
for W in WINTERS:
    for m in M:
        for k in ("tp", "fp", "fn"): pooled[m][k] += agg[W][m][k]
out = {"view": VIEW, "rows": len(S), "winters": WINTERS, "inputs": COLS[:len(NUMF) + 2] + ["lift (one-hot)"],
       "pooled": {m: prf(pooled[m]) for m in M}, "by_winter": {W: {m: prf(agg[W][m]) for m in M} for W in WINTERS}}
final = DecisionTreeClassifier(max_depth=3, min_samples_leaf=50, random_state=0).fit(X(S), Y(S))
out["model2_rules_all_winters"] = export_text(final, feature_names=COLS, max_depth=3)
json.dump(out, open(os.path.join(ROOT, "results", f"models{SUF}.json"), "w"), indent=1)
names = {M[0]: "Model 1: boosted trees (ceiling)", M[1]: "Model 2: tree, depth 3", M[2]: "Single early-gust line (fitted)", M[3]: "25 mph rule on early gust"}
md = [f"# Models 1 and 2 beside the single wind line", "", f"View: {VIEW}. {len(S):,} expected lift-days. Leave-one-winter-out: each model is fitted on the other winters and scored on the one left out; counts are summed.",
      "Every method reads only what is known by about 9-10 am: " + ", ".join(NUMF) + ", month, side, lift. Calls are made at 50% probability (models) or at the fitted line.", "",
      "| Method (pooled) | Precision | Recall | F1 |", "|---|---|---|---|"]
md += [f"| {names[m]} | {out['pooled'][m]['precision']} | {out['pooled'][m]['recall']} | {out['pooled'][m]['f1']} |" for m in M]
md += ["", "## Per winter (F1)", "", "| Winter | " + " | ".join(names[m] for m in M) + " |", "|---|---|---|---|---|"]
md += [f"| {W} | " + " | ".join(str(out["by_winter"][W][m]["f1"]) for m in M) + " |" for W in WINTERS]
md += ["", "## Model 2 as if-then rules (fitted on all winters, for reading only; the scores above come from the left-out folds)", "", "```", out["model2_rules_all_winters"].rstrip(), "```", "",
       "Rows are lift-days where the roster said the lift was meant to run (or a whole-side closure); the same caveats as docs/RESULTS.md apply (selection, began-on-hold rows held by definition)."]
open(os.path.join(ROOT, "docs", f"MODELS{SUF}.md"), "w").write("\n".join(md) + "\n")
print(VIEW); [print(f"  {names[m]:34} P {out['pooled'][m]['precision']} R {out['pooled'][m]['recall']} F1 {out['pooled'][m]['f1']}") for m in M]
