"""Write results/build_manifest.json: what produced the current data. Kept small on purpose."""
import os, sys, json, glob, hashlib, subprocess, platform
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."); sys.path.insert(0, os.path.join(root, "scripts"))
from parse_posts import PARSER_VERSION
sh = lambda *a: subprocess.run(a, cwd=root, capture_output=True, text=True).stdout.strip()
def h(paths):
    m = hashlib.sha256()
    for p in sorted(paths): m.update(open(p, "rb").read())
    return m.hexdigest()[:16]
try: import numpy; npv = numpy.__version__
except Exception: npv = None
out = {"parser_version": PARSER_VERSION, "git_commit": sh("git", "rev-parse", "--short", "HEAD"), "git_dirty": bool(sh("git", "status", "--porcelain", "--", "scripts", "rules", "tests")),
       "python": platform.python_version(), "numpy": npv,
       "events_sha": h(glob.glob(os.path.join(root, "data/derived/*_events.json"))), "lift_days_sha": h([os.path.join(root, "data/derived/lift_days.csv")]),
       "raw_inputs_sha": {d: h([p for p in glob.glob(os.path.join(root, "data/raw", d, "**", "*"), recursive=True) if os.path.isfile(p)]) for d in sorted(os.listdir(os.path.join(root, "data/raw")))}}
json.dump(out, open(os.path.join(root, "results", "build_manifest.json"), "w"), indent=1); print("manifest:", out["parser_version"], out["git_commit"], "dirty" if out["git_dirty"] else "clean")
