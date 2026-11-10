"""Architecture checks: do the sources, raw files, hashes, frozen samples, clocks and layers agree with each other? Run after a build (scripts/run_all.sh does).
Hard errors exit 1; warnings print. What it guards: (1) every raw folder is in the source registry (rules/sources.json) and every registry source has its pull script; (2) the raw inventory hashes still match the files (nothing in data/raw changed unrecorded);
(3) frozen validation samples are intact, disjoint, from held-out posts only, and 40 per winter; (4) the held-out split is still the deterministic hash; (5) the blog's site clock is Pacific; (6) forecast as-of flags are recomputed, quotes are within 25 words;
(7) COMMENTARY IS NEVER FITTED: no fitting or build script reads commentary files; (8) the lift-day table holds observed and weather columns only (no model-read forecast columns); (9) the winter registry is fresh.   usage: python3 -I scripts/check_architecture.py"""
import os, sys, re, json, csv, glob, hashlib, subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT = os.environ.get("ARCH_ROOT") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")      # ARCH_ROOT lets the failure tests run on a scratch copy
P = lambda *a: os.path.join(ROOT, *a)
errors, warns, notes = [], [], []
err, warn = errors.append, warns.append
# ---- 1 registry
reg = json.load(open(P("rules", "sources.json"))); S = reg["sources"]
ROLES = {"OUTCOME", "FEATURE", "CALENDAR", "FORECAST", "COMMENTARY", "CHECK", "REFERENCE"}
need = ("id", "role", "what", "raw", "winters", "as_of", "clock", "cost", "redistribution", "status")
ids = [s["id"] for s in S]
if len(ids) != len(set(ids)): err("sources.json: duplicate source ids")
claimed = set()
for s in S:
    for k in need:
        if k not in s: err(f"sources.json: {s.get('id')} lacks '{k}'")
    for r in (s["role"], s.get("also_role")):
        if r and r not in ROLES: err(f"sources.json: {s['id']} has unknown role {r}")
    claimed.add(s["raw"].split("/")[0])
    for scr in re.findall(r"scripts/[\w.]+\.py", s.get("pull", "")):
        if not os.path.exists(P(scr)): err(f"sources.json: {s['id']} names {scr}, which does not exist")
    for w in s["winters"]:
        if w not in reg["winters_all"]: err(f"sources.json: {s['id']} lists unknown winter {w}")
raw_dirs = sorted(d for d in os.listdir(P("data", "raw")) if os.path.isdir(P("data", "raw", d)))
claimed |= {"x_review"}                                  # sampled accounts, registered as x_review
import fnmatch
pats = [s_["raw"] for s_ in S] + ["x_review", "x_review/*"]
for d in raw_dirs:
    if d not in claimed: err(f"data/raw/{d} is not in rules/sources.json")
for f_ in glob.glob(P("data", "raw", "**", "*"), recursive=True):             # file level: every raw file must match some source's raw path or pattern
    if os.path.isfile(f_):
        rel = os.path.relpath(f_, P("data", "raw"))
        if not any(fnmatch.fnmatch(rel, pt) or rel.startswith(pt.rstrip("*").rstrip("/") + "/") for pt in pats) and not rel.endswith(("manifest.json", ".log")):      # pull logs are bookkeeping, not data
            err(f"data/raw/{rel} is not covered by any source in rules/sources.json"); break
# ---- 2 inventory hashes
inv = open(P("docs", "RAW_INVENTORY.md")).read()
for d in raw_dirs:
    m = re.search(rf"\| {re.escape(d)} \| (\d+) \| [\d.]+ \| [\d-]* \| ([0-9a-f]{{16}}) \|", inv)
    if not m: err(f"docs/RAW_INVENTORY.md has no row for data/raw/{d}; run scripts/raw_inventory.py"); continue
    fs = sorted(p for p in glob.glob(P("data", "raw", d, "**", "*"), recursive=True) if os.path.isfile(p)); h = hashlib.sha256()
    for p in fs: h.update(open(p, "rb").read())
    if h.hexdigest()[:16] != m.group(2) or len(fs) != int(m.group(1)): err(f"data/raw/{d} changed since the inventory ({len(fs)} files vs {m.group(1)} recorded, hash differs); raw must not change without a new inventory")
# ---- 3 frozen samples
allsets = {}; heldout = {}; train = {}
for w in reg["winters_all"]:
    for sp, store in (("heldout", heldout), ("train", train)):
        f = P("data", "derived", f"{w}_{sp}.json")
        if os.path.exists(f): store[w] = {p["id"] for p in json.load(open(f))}
for fn in sorted(glob.glob(P("results", "validation_sample_ids*.json"))):
    d = json.load(open(fn)); by = d["ids_by_winter"]; flat = [i for v in by.values() for i in v]; name = os.path.basename(fn)
    if len(flat) != d["n"]: err(f"{name}: n says {d['n']} but holds {len(flat)} ids")
    okh = any(hashlib.sha256(j.encode()).hexdigest() == d["ids_sha256"] for j in (",".join(sorted(flat)), "\n".join(sorted(flat)), ",".join(flat)))
    if not okh: err(f"{name}: ids no longer match their recorded hash (the frozen sample was altered)")
    for w, v in by.items():
        if len(v) != 40: err(f"{name}: {w} has {len(v)} ids, expected 40")
        if len(set(v)) != len(v): err(f"{name}: {w} repeats an id")
        if w in heldout and not set(v) <= heldout[w]: err(f"{name}: {w} has ids outside the held-out split")
        if w in train and set(v) & train[w]: err(f"{name}: {w} has ids that are training posts")
        for i in v:
            if i in allsets: err(f"{name}: id {i} is also in {allsets[i]}")
            allsets[i] = name
sf = P("results", "validation_seen.json")
if os.path.exists(sf):                                                  # frozen posts that a reviewer has seen: must be real frozen ids, excluded from grading
    seen = json.load(open(sf))["ids"]
    for i in seen:
        if i not in allsets: err(f"validation_seen.json lists {i}, which is not in any frozen sample")
    notes.append(f"{len(seen)} frozen validation posts were seen in review and are excluded from grading (results/validation_seen.json)")
# ---- 4 deterministic held-out split
held = lambda i: int(hashlib.sha256(("held-out-v1:" + i).encode()).hexdigest(), 16) % 5 == 0
for w in reg["winters_all"]:
    f = P("data", "raw", "x", w + ".json"); h = P("data", "derived", f"{w}_heldout.json")
    if os.path.exists(f) and os.path.exists(h):
        raw = {p["id"] for p in json.load(open(f))}
        want = {i for i in raw if held(i)}
        if want != heldout.get(w): err(f"{w}: held-out file does not match the hash rule ({len(want)} expected, {len(heldout.get(w, []))} found)")
        if heldout.get(w, set()) & train.get(w, set()): err(f"{w}: a post is in both train and held-out")
    elif os.path.exists(f): notes.append(f"{w}: raw posts saved, split not made")
# ---- 5 blog clock
bp = P("data", "derived", "blog_posts.csv")
if os.path.exists(bp):
    tz = ZoneInfo("America/Los_Angeles"); bad = 0; n = 0
    for r in csv.DictReader(open(bp)):
        n += 1; loc = datetime.fromisoformat(r["date"]).replace(tzinfo=tz); want = round(-loc.utcoffset().total_seconds() / 3600)
        bad += int(r["tz_offset_h"]) != want
    if bad / max(n, 1) > 0.01: err(f"blog_posts.csv: {bad} of {n} posts have a gmt offset that is not the Pacific offset; the site clock assumption fails")
    elif bad: warn(f"blog_posts.csv: {bad} of {n} posts differ from the Pacific offset by an hour (daylight-saving edge; the assumption holds)")
else: warn("data/derived/blog_posts.csv missing; run scripts/build_blog_index.py")
# ---- 6 forecast as-of and quote length
fp = P("data", "derived", "blog_forecast.csv")
if os.path.exists(fp):
    wrong = 0
    for r in csv.DictReader(open(fp)):
        t = datetime.fromisoformat(r["posted_local"]); ok = int(t.hour < 9 or (t.hour == 9 and t.minute == 0))
        wrong += ok != int(r["asof_by_0900"])
        if r["reader"] != "regex-v1": err("blog_forecast.csv: a row lacks its reader tag")
    if wrong: err(f"blog_forecast.csv: {wrong} rows have a wrong asof_by_0900 flag")
cp = P("rules", "season_calendar.json")
if os.path.exists(cp):
    for e in json.load(open(cp))["events"]:
        if len(e["quote"].split()) > 25: err(f"season_calendar.json: a quote over 25 words (post {e['post_id']})"); break
    if not all("readers" in e and "quote_ok" in e for e in json.load(open(cp))["events"]): err("season_calendar.json: events must carry readers and quote_ok")
# ---- 7 commentary never fitted
FIT = ["parse_posts", "build_dataset", "recover_rules", "baselines", "infer_causes", "closure_conditions", "build_app_model", "sensitivity_rosters", "agree"]
BAN = re.compile(r"blog_text|blog_posts|commentary|x_tahoeweather|x_review|nws_text|AFDREV|PNSREV")
for n_ in FIT:
    f = P("scripts", n_ + ".py")
    if os.path.exists(f) and BAN.search(open(f).read()): err(f"scripts/{n_}.py reads a commentary file; commentary is for spot checks, never fitted")
# ---- 8 lift-day table stays observed + weather
for _n in ("lift_days.csv", "lift_days_11w.csv"):
    lp = P("data", "derived", _n)
    if os.path.exists(lp):
        for c in next(csv.reader(open(lp))):
            if c.startswith(("fc_", "blog_", "tweet_", "afd_")): err(f"{_n} column {c} is model-read or commentary; keep it in its own file")
# ---- 9 winter registry fresh
if subprocess.run([sys.executable, "-I", P("scripts", "build_winters.py"), "--check"]).returncode: err("rules/winters.json is stale; run scripts/build_winters.py")
for m in notes: print("NOTE ", m)
for m in warns: print("WARN ", m)
for m in errors: print("ERROR", m)
print("PASS" if not errors else f"FAIL ({len(errors)} errors)")
sys.exit(1 if errors else 0)
