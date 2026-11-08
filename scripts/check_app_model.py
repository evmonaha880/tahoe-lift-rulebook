"""Fails if the app's data file disagrees with the pipeline's results. Run after build_app_model.py.
usage: python3 -I scripts/check_app_model.py   (exit 1 on any mismatch)"""
import os, json, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
s = open(os.path.join(ROOT, "docs", "app", "model.js")).read(); M = json.loads(s[len("window.MODEL = "): s.rindex(";")])
BL = json.load(open(os.path.join(ROOT, "results", "baselines.json"))); bad = []
def eq(name, a, b):
    if a != b: bad.append(f"{name}: app {a} != results {b}")
for W in M["winters"]:
    st = M["proof"]["strata"][W]
    eq(f"{W} day F1", st["score"], BL["day_level"][W]["learned"]["f1"]); eq(f"{W} 25mph F1", st["baseline"], BL["day_level"][W]["mph25"]["f1"]); eq(f"{W} line", st["line"], BL["day_level"][W]["line_mph"])
for m in ("per_lift_called_at_50pct", "per_lift_any_pass", "best_single_wind_line", "mph25"):
    eq(f"pooled lift {m}", M["proof"]["lift"]["pooled"][m], BL["lift_level"]["pooled"][m])
eq("lift winners", M["proof"]["lift"]["winters_won_by_method"], BL["lift_level"]["winters_won_by_method"])
rb = {r["lift"] for r in json.load(open(os.path.join(ROOT, "rules", "rulebook_palisades.json")))}
eq("lifts in app vs rulebook", sorted(M["lifts"]), sorted(rb))
placed = set(M["groups"]["upper"]) | set(M["groups"]["lower"]) | set(M["groups"]["alpine"]) | {"Tram", "Funitel", "Base to Base Gondola"}
other = sorted(set(M["lifts"]) - placed)
print("lifts shown under 'Other':", other)
agree = M["agree"]; print("reader agreement in app:", agree)
for b in bad: print("MISMATCH", b)
print("OK: app numbers equal the pipeline's results" if not bad else f"{len(bad)} mismatches"); sys.exit(1 if bad else 0)
