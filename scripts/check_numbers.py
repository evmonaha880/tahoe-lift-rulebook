"""Numbers registry check. docs/numbers.json lists, for each headline number, the files that must quote it; this script recomputes the current value
from the data and fails when a listed file does not contain it (a stale copy), or when a retired value still appears.   usage: python3 -I scripts/check_numbers.py"""
import os, sys, re, csv, json, glob, subprocess, collections
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.chdir(root)
reg = json.load(open("docs/numbers.json"))
rows = list(csv.DictReader(open("data/derived/lift_days.csv")))
ev = sum(len(json.load(open(f))) for f in glob.glob("data/derived/*_events.json") if os.path.basename(f)[:4] >= "2018")      # the analysed winters; 2015-18 events are parsed but not counted in the headline yet
tests = int(re.search(r"(\d+)/\d+ golden", subprocess.run([sys.executable, "-I", "tests/golden.py"], capture_output=True, text=True).stdout).group(1))
st = subprocess.run([sys.executable, "-I", "scripts/parser_status.py"], capture_output=True, text=True).stdout.strip().split("\n")[-1]
unmatched = re.search(r"([\d,]+) \(([\d.]+)%\)", st); posts = re.search(r"total\s+([\d,]+)", st).group(1)
bl = json.load(open("results/baselines.json"))
sched_in = sum(r["scheduled"] == "True" and r["in_season"] == "1" for r in rows)
cur = {"events": f"{ev:,}", "posts": posts, "tests": str(tests), "unmatched_posts": unmatched.group(1), "unmatched_pct": unmatched.group(2) + "%", "lift_days": f"{len(rows):,}",
       "scheduled_lift_days": f"{sum(r['scheduled'] == 'True' for r in rows):,}",
       "f1_single_line": f"{bl['lift_level']['pooled']['best_single_wind_line']['f1']:.2f}", "f1_per_lift": f"{bl['lift_level']['pooled']['per_lift_any_pass']['f1']:.2f}",
       "morning_f1": f"{bl['day_level_morning']['pooled']['f1']:.2f}", "full_day_f1": f"{bl['day_level_morning']['full_day_f1']:.2f}",
       "validation_acc": f"{json.load(open('results/validation_results.json'))['majority']['acc']*100:.1f}%",
       "named_share": f"{round(bl['coverage']['named_share'] * 100)}%"}
bad = 0
for key, files in reg["quoted"].items():
    for f in files:
        txt = open(f).read()
        if cur[key] not in txt: print(f"STALE  {f}: expected {key} = {cur[key]}"); bad += 1
for old, files in reg["retired"].items():
    for f in files:
        if old in open(f).read(): print(f"RETIRED value {old!r} still in {f}"); bad += 1
print(("PASS" if not bad else f"FAIL: {bad} stale or retired numbers"), "| current:", {k: cur[k] for k in ("events", "tests", "lift_days", "f1_single_line", "f1_per_lift")})
sys.exit(1 if bad else 0)
