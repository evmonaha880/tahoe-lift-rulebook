"""Freeze a validation sample for winters added after the first frozen sample (results/validation_sample_ids.json, 320 posts, 8 winters, not touched).
Draws 40 held-out post ids per winter with a fixed seed, writes ids only (never post text) and a hash, BEFORE any parser work or reading of those winters' posts.
Rule: graded once at the end, never re-graded after a parser change, not read while writing rules.
usage: python3 -I scripts/draw_validation_sample.py <n> 2016 2017   -> results/validation_sample_ids_<n>.json  (n = 2 for the first added batch, 3 for the next; refuses to overwrite an existing file)"""
import os, sys, json, random, hashlib, datetime
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "results", f"validation_sample_ids_{sys.argv[1]}.json")
if os.path.exists(OUT): raise SystemExit(f"{OUT} exists; a frozen sample is never redrawn")
SEED = 20261108; by = {}
for y in map(int, sys.argv[2:]):
    W = f"{y}-{str(y + 1)[2:]}"
    ids = sorted(p["id"] for p in json.load(open(os.path.join(ROOT, "data", "derived", f"{W}_heldout.json"))))
    by[W] = sorted(random.Random(f"{SEED}:{W}").sample(ids, 40))
allids = sorted(i for v in by.values() for i in v)
json.dump(dict(drawn=str(datetime.date.today()), seed=SEED, rule="held-out ids of winters added after the first frozen sample, 40 per winter, drawn before any parser work or reading of those posts; graded once at the end",
               n=len(allids), ids_sha256=hashlib.sha256(",".join(allids).encode()).hexdigest(), ids_by_winter=by), open(OUT, "w"), indent=1)
print({w: len(v) for w, v in by.items()}, "total", len(allids))
