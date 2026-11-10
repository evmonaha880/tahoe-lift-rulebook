"""Fingerprint every build output so a cleanup can prove it changed nothing.
usage: python3 -I scripts/fingerprint.py --write    record the current outputs in results/baseline_hashes.json
       python3 -I scripts/fingerprint.py --check    compare the current outputs with the recorded ones (exit 1 on any difference)
Run scripts/run_all.sh first. A behaviour-preserving change must leave --check clean; a behaviour-changing one must list which files moved."""
import os, sys, json, glob, hashlib, re
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(root, "results", "baseline_hashes.json")
PATTERNS = ["data/derived/*_events.json", "data/derived/lift_days.csv", "data/derived/lift_days_11w.csv", "data/derived/lift_windows.csv", "data/derived/first_run.csv",
            "data/derived/weather_common.csv", "data/derived/blog_forecast.csv", "data/derived/cause_inferred.csv", "data/derived/weather_qc.csv",
            "results/baselines.json", "results/baselines_11w.json", "docs/RESULTS_11w.md", "results/baselines_10w.json", "docs/RESULTS_10w.md", "results/baselines_named.json", "docs/RESULTS_named.md", "results/loo_results.json", "results/weather_common.json", "results/forecast_value.json",
            "rules/rulebook_palisades.json", "rules/winters.json", "docs/RESULTS.md", "docs/CAUSES.md", "docs/CLOSURES.md", "docs/app/model.js"]
def current():
    files = sorted({p for pat in PATTERNS for p in glob.glob(os.path.join(root, pat))})
    def body(p):
        b = open(p, "rb").read()
        return re.sub(rb'"(built|commit)": ?"[^"]*"', rb'"\1":""', b) if p.endswith("model.js") else b   # the app model stamps its build time and the git commit; ignore only those two fields
    return {os.path.relpath(p, root): hashlib.sha256(body(p)).hexdigest()[:16] for p in files}
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    now = current()
    if mode == "--write":
        json.dump(now, open(OUT, "w"), indent=0, sort_keys=True); print(f"recorded {len(now)} files in results/baseline_hashes.json")
    elif mode == "--check":
        old = json.load(open(OUT)); moved = [f for f in sorted(set(old) | set(now)) if old.get(f) != now.get(f)]
        for f in moved: print("CHANGED" if f in old and f in now else ("NEW" if f in now else "MISSING"), f)
        print(f"{len(now) - len(moved)} of {len(old)} recorded files identical" if moved else f"IDENTICAL: all {len(old)} recorded files match"); sys.exit(1 if moved else 0)
    else: print(__doc__)
