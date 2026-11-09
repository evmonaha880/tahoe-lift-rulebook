"""Sensitivity run: days whose schedule post gives only a lift COUNT (no names). Infer the schedule from the typical roster of nearby days,
accept a day only when the stated count is within 2 of the inferred roster, refit the per-lift rules on the augmented table in a scratch copy,
and report how far the thresholds and scores move. Never replaces the main numbers.   usage: python3 -I scripts/sensitivity_rosters.py"""
import os, csv, json, re, shutil, subprocess, collections
from datetime import date, datetime, timedelta
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PY = os.environ.get("PY", os.path.expanduser("~/DataLake/.venv/bin/python"))
rows = list(csv.DictReader(open(os.path.join(root, "data/derived/lift_days.csv")))); cols = list(rows[0].keys())
by = collections.defaultdict(list)
for r in rows:
    if r["side"] in ("palisades", "alpine"): by[(r["date"], r["side"])].append(r)
# stated counts, per day and side, from the posts
cnt, cnt_any = {}, {}
for y in range(2018, 2026):
    W = f"{y}-{str(y+1)[2:]}"
    for sp in ("train", "heldout"):
        for p in json.load(open(os.path.join(root, f"data/derived/{W}_{sp}.json"))):
            d = (datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")) - timedelta(hours=8)).date().isoformat(); t = re.sub(r"#\w+|https?://\S+", " ", p["text"])
            for m in re.finditer(r"(\d{1,2})\s+(?:\w+\s+)?lifts?\b", t, re.I):
                ctx = t[max(0, m.start() - 60):m.end() + 40].lower(); n = int(m.group(1))
                if not re.search(r"schedul|spinning|9a|9 ?am|on the schedule|operat", ctx) or not 3 <= n <= 45: continue
                a = "alpine" in ctx and "palisades" not in ctx; pl = "palisades" in ctx or "squaw" in ctx
                sd = "alpine" if a and not pl else "palisades" if pl and not a else None
                if sd: cnt.setdefault((d, sd), n)
                else: cnt_any.setdefault(d, n)
roster = {k: {r["lift"] for r in rs if r["scheduled"] == "True"} for k, rs in by.items() if any(r["scheduled"] == "True" for r in rs)}
used, extra, skipped = 0, [], collections.Counter()
for k, rs in sorted(by.items()):
    d, sd = k
    r0 = rs[0]
    if k in roster or r0["in_season"] != "1" or r0["covid_era"] != "" or d < "2021-07-01": continue
    near = [s for (e, sd2), s in roster.items() if sd2 == sd and abs((date.fromisoformat(e) - date.fromisoformat(d)).days) <= 30]
    if len(near) < 5: skipped["too few nearby roster days"] += 1; continue
    c = collections.Counter(l for s in near for l in s); typ = {l for l, n in c.items() if n / len(near) >= .5}
    n = cnt.get(k); tot = None
    if n is None and d in cnt_any:                                               # 'N lifts on schedule' with no side named: a resort-wide count or one side's count
        other = "alpine" if sd == "palisades" else "palisades"
        nearo = [s for (e, sd2), s in roster.items() if sd2 == other and abs((date.fromisoformat(e) - date.fromisoformat(d)).days) <= 30]
        co = collections.Counter(l for s in nearo for l in s); typo = {l for l, m in co.items() if nearo and m / len(nearo) >= .5}
        a_ = cnt_any[d]
        if nearo and abs(a_ - (len(typ) + len(typo))) <= 3: n = len(typ)            # count matches the whole resort's typical roster
        elif abs(a_ - len(typ)) <= 2: n = a_                                      # count matches this side's roster alone
    if n is None: skipped["no stated count"] += 1; continue
    if abs(n - len(typ)) > 2: skipped["count not within 2 of the typical roster"] += 1; continue
    used += 1
    have = {r["lift"]: r for r in rs}; tmpl = rs[0]
    for r in rs: r["scheduled"] = "True"                                   # a lift with an event was on the schedule
    for l in typ - set(have):
        nr = dict(tmpl); nr.update({"lift": l, "scheduled": "True", "held": "0", "held_wind": "0", "held_patrol": "0", "held_mech": "0", "held_weather": "0", "held_unstated": "0",
                                   "hold_minutes": "", "reopen_posted": "", "closed_all": "0", "first_event": "", "in_heldout_posts": "0"}); extra.append(nr)
scratch = "/tmp/sens_repo"; shutil.rmtree(scratch, ignore_errors=True)
shutil.copytree(root, scratch, ignore=shutil.ignore_patterns("raw", ".git", "__pycache__"))
os.makedirs(os.path.join(scratch, "data/derived"), exist_ok=True)
with open(os.path.join(scratch, "data/derived/lift_days.csv"), "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows + extra)
for s in ("recover_rules", "baselines"): subprocess.run([PY, "-I", f"scripts/{s}.py"], cwd=scratch, capture_output=True)
main = {r["lift"]: r for r in json.load(open(os.path.join(root, "rules/rulebook_palisades.json")))}
sens = {r["lift"]: r for r in json.load(open(os.path.join(scratch, "rules/rulebook_palisades.json")))}
def num(rule): m = re.search(r">= ([\d.]+)", rule); return float(m.group(1)) if m else None
moves = []
for l, r in main.items():
    s = sens.get(l)
    if s and num(r["rule"]) is not None and num(s["rule"]) is not None and r["rule"].split()[0] == s["rule"].split()[0]: moves.append((l, r["rule"], s["rule"], round(num(s["rule"]) - num(r["rule"]), 1)))
    elif s: moves.append((l, r["rule"], s["rule"], "feature changed"))
bm, bs = json.load(open(os.path.join(root, "results/baselines.json"))), json.load(open(os.path.join(scratch, "results/baselines.json")))
out = [f"# Sensitivity: days with no named schedule", "", "Generated by `python3 -I scripts/sensitivity_rosters.py`. **Sensitivity only**; the main numbers never use these inferred rosters.", "",
       f"- Method: for a day whose schedule post gives only a lift count, take the lifts scheduled on at least half of nearby (within 30 days) days of that side with a named roster; use the day only when the stated count is within 2 of that roster; 2021-22 to 2025-26, non-COVID, in season.",
       f"- Days used: {used}. Lift rows added: {len(extra)}. Days skipped: {dict(skipped)}.", "",
       "| Lift | Main rule | With inferred rosters | Threshold change (mph) |", "|---|---|---|---|"]
big = 0
for l, a, b, d in sorted(moves, key=lambda x: -(abs(x[3]) if isinstance(x[3], float) else 99)):
    out.append(f"| {l} | {a} | {b} | {d} |")
    if (isinstance(d, float) and abs(d) > 10) or d == "feature changed": big += 1
out += ["", f"- Lifts whose rule moves by more than 10 mph or changes feature: {big} of {len(moves)}."]
json.dump({"days_used": used, "rows_added": len(extra), "lifts_moved_big": big, "lifts": len(moves)}, open(os.path.join(root, "results/sensitivity_rosters.json"), "w"), indent=1)
open(os.path.join(root, "docs/SENSITIVITY.md"), "w").write("\n".join(out) + "\n"); print(out[4]); print(out[-1])
