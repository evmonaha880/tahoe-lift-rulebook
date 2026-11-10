"""Data checks for the parsed events and the lift-day table. Run after every build (scripts/run_all.sh does).
Fails (exit 1) on any hard error; prints warnings for soft ones.  usage: python3 -I scripts/check_data.py"""
import os, sys, json, csv, glob, re, collections
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(root, "scripts"))
from parse_posts import LIFTS, PARSER_VERSION, RID
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
# event-order checks: exact duplicates and implausible hours are errors; repeats and unannounced reopenings are counted for the record
dupes = 0; weird_hour = 0; reopen_no_status = 0; repeat_hold = 0
for f in sorted(glob.glob(os.path.join(D, "*_events.json"))):
    ev = json.load(open(f)); seen = collections.Counter(); byday = collections.defaultdict(list)
    for e in ev:
        seen[(e["source_post_id"], e["event_type"], e["lift"], e.get("cause"), tuple(e.get("except", [])), e["parse_rule_id"])] += 1; byday[(e["start"][:10], e["lift"])].append(e)
        if not 4 <= int(e["start"][11:13]) <= 22: weird_hour += 1
    dupes += sum(n - 1 for n in seen.values() if n > 1)
    for (d, l), es in byday.items():
        es.sort(key=lambda x: x["start"]); state = None
        for e in es:
            if e["event_type"] == "reopen" and state is None: reopen_no_status += 1
            if e["event_type"] == "hold_start" and state == "hold": repeat_hold += 1
            if e["event_type"] in ("hold_start", "delay", "closed_day"): state = "hold"
            elif e["event_type"] in ("reopen", "scheduled_opening"): state = "open"
if dupes: err(f"{dupes} exact duplicate events")
if weird_hour: err(f"{weird_hour} events dated outside 04:00 to 22:59 local")
warn(f"event order: {reopen_no_status} reopenings of a lift with no earlier status that day (late opening or roster-only lifts), {repeat_hold} repeated hold announcements with no reopening between")
if set(versions) - {PARSER_VERSION}: warn(f"events carry parser versions {dict(versions)}; current is {PARSER_VERSION} (re-run parse_posts.py)")
lim = json.load(open(os.path.join(root, "results", "baseline_metrics.json"))).get("liftless_status_events", 10**9) if os.path.exists(os.path.join(root, "results", "baseline_metrics.json")) else 10**9
if len(liftless) > lim: err(f"{len(liftless)} status events have no lift (baseline {lim}); the parser matched a pattern but found no lift")
else: warn(f"{len(liftless)} status events have no lift (baseline {lim}); they carry no information and are listed for triage in the parser plan")
# ---- lift-day tables: the 8 core winters (lift_days.csv, the headline) and all 11 (lift_days_11w.csv) get the same checks
GUST_SRC_EARLY = {"station_15min", "station_hourly", "estimate"}      # 15-minute ridge stations (2018-19 on), hourly Siberia/Belmont (2016-18), ERA5+SNOTEL estimate (2015-16)
core_rows = None
for LD in ("lift_days", "lift_days_11w"):
    rows = list(csv.DictReader(open(os.path.join(D, LD + ".csv"))))
    keys = collections.Counter((r["date"], r["lift"]) for r in rows)
    dups = [k for k, n in keys.items() if n > 1]
    if dups: err(f"{LD}: {len(dups)} duplicate (date, lift) rows, e.g. {dups[:3]}")
    FEATS = json.load(open(os.path.join(root, "rules", "features.json")))["columns"]
    _cols = list(rows[0].keys())
    if [c for c in _cols if c not in FEATS]: err(f"{LD} columns with no entry in rules/features.json (role, as-of, unit): {[c for c in _cols if c not in FEATS]}")
    if [c for c in FEATS if c not in _cols]: err(f"rules/features.json describes columns that are not in {LD}: {[c for c in FEATS if c not in _cols]}")
    fnum = lambda x: float(x) if x not in ("", None) else None
    bywinter = collections.Counter()
    for r in rows:
        bywinter[r["winter"]] += 1
        if winter_of(r["date"]) != r["winter"]: err(f"{LD}: {r['date']} labelled {r['winter']}")
        if r["lift"] not in LIFT_NAMES and r["lift"] not in ("(all other lifts)", "ALL_ON_HOLD"): err(f"{LD}: unknown lift {r['lift']!r}")
        if r["held"] not in ("0", "1"): err(f"{LD}: held={r['held']!r}")
        if r["held"] == "0" and any(r[k] == "1" for k in ("held_wind", "held_patrol", "held_mech", "held_weather", "held_unstated")): err(f"{LD}: cause flag set but held=0 ({r['date']} {r['lift']})")
        if r["held"] == "1" and not any(r[k] == "1" for k in ("held_wind", "held_patrol", "held_mech", "held_weather", "held_unstated")): err(f"{LD}: held=1 with no cause flag ({r['date']} {r['lift']})")
        if r["closed_all"] == "1" and r["held"] != "1": err(f"{LD}: closed_all without held ({r['date']} {r['lift']})")
        g = fnum(r["day_gust"])
        if g is not None and not (0 <= g <= 250): err(f"{LD}: day_gust {g} on {r['date']}")
        h = fnum(r["sib_h60"])
        if h is not None and not (0 <= h <= 24): err(f"{LD}: sib_h60 {h} on {r['date']}")
        hm = fnum(r["hold_minutes"])
        if hm is not None and not (0 <= hm <= 1440): err(f"{LD}: hold_minutes {hm} on {r['date']} {r['lift']}")
        a = fnum(r["avy"])
        if a is not None and a not in (1, 2, 3, 4, 5): err(f"{LD}: avy {a} on {r['date']}")
        if r["scheduled"] not in ("True", "False"): err(f"{LD}: scheduled={r['scheduled']!r}")
        if r["reopen_posted"] == "1" and r["held"] != "1" : err(f"{LD}: reopen_posted without held ({r['date']} {r['lift']})")
    if LD == "lift_days_11w":
        _core = {(r["date"], r["lift"]): r for r in core_rows}
        _cw = {r["winter"] for r in core_rows}
        _in = [r for r in rows if r["winter"] in _cw]
        if len(_in) != len(core_rows): err(f"{LD}: {len(_in)} core-winter rows but lift_days.csv has {len(core_rows)}")
        _bad = next((r for r in _in if _core.get((r["date"], r["lift"])) != r), None)
        if _bad: err(f"{LD}: a core-winter row differs from lift_days.csv ({_bad['date']} {_bad['lift']})")
        for r in rows:
            if r["early_gust"] != "" and r["gust_src_early"] not in GUST_SRC_EARLY: err(f"{LD}: early_gust set but gust_src_early={r['gust_src_early']!r} ({r['date']})"); break
        for r in rows:
            if r["early_gust"] == "" and r["gust_src_early"] != "": err(f"{LD}: gust_src_early set with no early_gust ({r['date']})"); break
    if LD == "lift_days": core_rows = rows
rows = core_rows
base = os.path.join(root, "results", "baseline_metrics.json")
if os.path.exists(base):
    b = json.load(open(base))
    for k, lab in (("lift_days", "lift-day rows"),):
        now = len(rows)
        if abs(now - b[k]) / b[k] > 0.15: warn(f"{lab}: {now} now vs {b[k]} at baseline (>15% change)")
_q = os.path.join(D, "weather_qc.csv")
if os.path.exists(_q):
    _qr = list(csv.DictReader(open(_q))); _c = collections.Counter(r["flag"] for r in _qr)
    if sum(int(r["impossible_values"]) for r in _qr): err("weather_qc: impossible values (gust outside 0-250 or temperature outside -45..110 F) in the weather files")
    warn(f"weather: {len(_qr):,} ridge station-days, {_c['ok']:,} complete, {_c['partial']} partial, {_c['missing']} missing; {sum(int(r['dropout']) for r in _qr)} dropout station-days (blanked in station-specific features)")
else: warn("weather_qc.csv missing (run scripts/weather_qc.py)")
_emitted = {e["parse_rule_id"] for f in glob.glob(os.path.join(D, "*_events.json")) for e in json.load(open(f))}
if _emitted - set(RID): errors.append(f"rule ids emitted by the parser but missing from the RULES ledger in parse_posts.py: {sorted(_emitted - set(RID))}")
print(f"events: {sum(nev.values())} in {len(nev)} winter files | lift-days: {len(rows)} | parser versions: {dict(versions)}")
for w in warns: print("WARN ", w)
for e in errors[:40]: print("ERROR", e)
if len(errors) > 40: print(f"... {len(errors) - 40} more errors")
print("PASS" if not errors else f"FAIL: {len(errors)} errors"); sys.exit(1 if errors else 0)
