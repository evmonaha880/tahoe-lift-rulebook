"""Data checks for the parsed events and the lift-day table. Run after every build (scripts/run_all.sh does).
Fails (exit 1) on any hard error; prints warnings for soft ones.  usage: python3 -I scripts/check_data.py"""
import os, sys, json, csv, glob, re, collections
from datetime import date
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(root, "scripts"))
from parse_posts import LIFTS, PARSER_VERSION
D = os.path.join(root, "data", "derived")
errors, warns = [], []
def err(m): errors.append(m)
def warn(m): warns.append(m)
_g = json.load(open(os.path.join(root, "rules", "lift_groups.json")))
DERIVED = {"Alpine Meadow", "Palisades Carpets", "Alpine Carpets"}      # names the parser builds outside its LIFTS table (to be moved into a lift reference file)
LIFT_NAMES = set(LIFTS) | set(_g["palisades"]) | set(_g["alpine"]) | DERIVED
SCOPES = {"ALL", "ALL_PALISADES", "ALL_ALPINE", "ALL_ON_HOLD", "ALL_OTHER", "UPPER_MOUNTAIN", "LOWER_MOUNTAIN"}
TYPES = {"scheduled_opening", "hold_start", "closed_day", "delay", "reopen", "partial", "warning", "parking", "other"}
CAUSES = {None, "wind", "mechanical", "patrol", "weather", "lightning"}
TAGNAMES = {"wind", "avalanche", "snow", "patrol", "mechanical", "ice", "visibility", "lightning", "power", "flood", "rain", "weather", "grooming"}
def winter_of(iso):
    y, m = int(iso[:4]), int(iso[5:7]); return f"{y}-{str(y+1)[2:]}" if m >= 8 else f"{y-1}-{str(y)[2:]}"
# ---- events
liftless = []
nev = collections.Counter(); versions = collections.Counter(); seen_ids = set()
for f in sorted(glob.glob(os.path.join(D, "*_events.json"))):
    name = os.path.basename(f); W = name[:7]
    posts = {p["id"] for sp in ("train", "heldout") if name.startswith(W) for p in json.load(open(os.path.join(D, f"{W}_{sp}.json")))} if False else None
    for e in json.load(open(f)):
        nev[W] += 1; versions[e.get("parser_version", "none")] += 1
        if e["event_type"] not in TYPES: err(f"{name}: bad event_type {e['event_type']}")
        if e.get("cause") not in CAUSES: err(f"{name}: bad cause {e.get('cause')}")
        l = e["lift"]
        if l is not None and l not in LIFT_NAMES and l not in SCOPES: err(f"{name}: unknown lift {l!r}")
        for x in e.get("except", []):
            if x not in LIFT_NAMES: err(f"{name}: unknown lift in except {x!r}")
        for t in e.get("cause_tags", []) or []:
            if t not in TAGNAMES: err(f"{name}: unknown cause tag {t!r}")
        if not re.match(r"\d{4}-\d\d-\d\dT\d\d:\d\d[-+]\d\d:\d\d$", e["start"]): err(f"{name}: bad start {e['start']!r}")
        elif winter_of(e["start"]) != W: err(f"{name}: event dated {e['start'][:10]} is outside winter {W}")
        if e["event_type"] in ("hold_start", "closed_day", "delay", "reopen", "partial") and l is None: liftless.append(e["source_post_id"])
        if e["cause"] is None and e.get("cause_source") == "observed": err(f"{name}: observed cause but cause is empty")
if set(versions) - {PARSER_VERSION}: warn(f"events carry parser versions {dict(versions)}; current is {PARSER_VERSION} (re-run parse_posts.py)")
lim = json.load(open(os.path.join(root, "results", "baseline_metrics.json"))).get("liftless_status_events", 10**9) if os.path.exists(os.path.join(root, "results", "baseline_metrics.json")) else 10**9
if len(liftless) > lim: err(f"{len(liftless)} status events have no lift (baseline {lim}); the parser matched a pattern but found no lift")
else: warn(f"{len(liftless)} status events have no lift (baseline {lim}); they carry no information and are listed for triage in the parser plan")
# ---- lift-day table
rows = list(csv.DictReader(open(os.path.join(D, "lift_days.csv"))))
keys = collections.Counter((r["date"], r["lift"]) for r in rows)
dups = [k for k, n in keys.items() if n > 1]
if dups: err(f"lift_days: {len(dups)} duplicate (date, lift) rows, e.g. {dups[:3]}")
FEATS = json.load(open(os.path.join(root, "rules", "features.json")))["columns"]
_cols = list(rows[0].keys())
if [c for c in _cols if c not in FEATS]: err(f"lift_days columns with no entry in rules/features.json (role, as-of, unit): {[c for c in _cols if c not in FEATS]}")
if [c for c in FEATS if c not in _cols]: err(f"rules/features.json describes columns that are not in lift_days: {[c for c in FEATS if c not in _cols]}")
fnum = lambda x: float(x) if x not in ("", None) else None
bywinter = collections.Counter()
for r in rows:
    bywinter[r["winter"]] += 1
    if winter_of(r["date"]) != r["winter"]: err(f"lift_days: {r['date']} labelled {r['winter']}")
    if r["lift"] not in LIFT_NAMES and r["lift"] not in ("(all other lifts)", "ALL_ON_HOLD"): err(f"lift_days: unknown lift {r['lift']!r}")
    if r["held"] not in ("0", "1"): err(f"lift_days: held={r['held']!r}")
    if r["held"] == "0" and any(r[k] == "1" for k in ("held_wind", "held_patrol", "held_mech", "held_weather", "held_unstated")): err(f"lift_days: cause flag set but held=0 ({r['date']} {r['lift']})")
    if r["held"] == "1" and not any(r[k] == "1" for k in ("held_wind", "held_patrol", "held_mech", "held_weather", "held_unstated")): err(f"lift_days: held=1 with no cause flag ({r['date']} {r['lift']})")
    if r["closed_all"] == "1" and r["held"] != "1": err(f"lift_days: closed_all without held ({r['date']} {r['lift']})")
    g = fnum(r["day_gust"])
    if g is not None and not (0 <= g <= 250): err(f"lift_days: day_gust {g} on {r['date']}")
    h = fnum(r["sib_h60"])
    if h is not None and not (0 <= h <= 24): err(f"lift_days: sib_h60 {h} on {r['date']}")
    hm = fnum(r["hold_minutes"])
    if hm is not None and not (0 <= hm <= 1440): err(f"lift_days: hold_minutes {hm} on {r['date']} {r['lift']}")
    a = fnum(r["avy"])
    if a is not None and a not in (1, 2, 3, 4, 5): err(f"lift_days: avy {a} on {r['date']}")
    if r["scheduled"] not in ("True", "False"): err(f"lift_days: scheduled={r['scheduled']!r}")
    if r["reopen_posted"] == "1" and r["held"] != "1" : err(f"lift_days: reopen_posted without held ({r['date']} {r['lift']})")
base = os.path.join(root, "results", "baseline_metrics.json")
if os.path.exists(base):
    b = json.load(open(base))
    for k, lab in (("lift_days", "lift-day rows"),):
        now = len(rows)
        if abs(now - b[k]) / b[k] > 0.15: warn(f"{lab}: {now} now vs {b[k]} at baseline (>15% change)")
print(f"events: {sum(nev.values())} in {len(nev)} winter files | lift-days: {len(rows)} | parser versions: {dict(versions)}")
for w in warns: print("WARN ", w)
for e in errors[:40]: print("ERROR", e)
if len(errors) > 40: print(f"... {len(errors) - 40} more errors")
print("PASS" if not errors else f"FAIL: {len(errors)} errors"); sys.exit(1 if errors else 0)
