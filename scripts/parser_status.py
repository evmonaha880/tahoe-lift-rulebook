"""One table: per winter, posts, events, unmatched posts, and parser agreement with the two blind readers (train / held-out).
Read-only. usage: python3 -I scripts/parser_status.py"""
import os, re, json, subprocess, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
D = os.path.join(ROOT, "data", "derived")
print(f"{'winter':8} {'posts':>6} {'events':>7} {'unmatched':>11} | {'train: par=subq / par=muse':>27} | {'held-out: par=subq / par=muse':>30}")
tot = [0, 0, 0]
for y in range(2018, 2026):
    W = f"{y}-{str(y+1)[2:]}"; n = ev = res = 0; ag = {}
    for sp in ("train", "heldout"):
        n += len(json.load(open(os.path.join(D, f"{W}_{sp}.json"))))
        e = json.load(open(os.path.join(D, f"{W}_{sp}_events.json"))); ev += len(e); res += sum(1 for x in e if x.get("unmatched"))
        out = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "scripts", "agree.py"), str(y), sp], capture_output=True, text=True).stdout
        m = re.search(r"par=subq ([\d.]+)%\s+par=muse ([\d.]+)%", out); ag[sp] = f"{m.group(1)}% / {m.group(2)}%" if m else "n/a"
    tot[0] += n; tot[1] += ev; tot[2] += res
    print(f"{W:8} {n:6,} {ev:7,} {res:4} ({res/n:4.1%}) | {ag['train']:>27} | {ag['heldout']:>30}")
print(f"{'total':8} {tot[0]:6,} {tot[1]:7,} {tot[2]:4} ({tot[2]/tot[0]:4.1%})")
