"""Write the opening-progression note (markdown) from data/derived/lift_windows.csv and the blog calendar, for walking through each season's staged openings.
Per season and side: each lift's first and last day with evidence it was running or meant to run (decision 65), with [B] where the blog announced a first run within 3 days. Windows are clamped to each side's season.
usage: python3 -I scripts/progression_note.py "<output.md>" """
import csv, json, re, collections, sys, os, datetime as dt
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
if len(sys.argv) < 2: raise SystemExit('usage: python3 -I scripts/progression_note.py "<output.md>"')
W = list(csv.DictReader(open(os.path.join(ROOT, "data", "derived", "lift_windows.csv"))))
cal = json.load(open(os.path.join(ROOT, "rules", "season_calendar.json")))["events"]
canon = sorted({r["lift"] for r in W}, key=len, reverse=True)
alias = {"squaw one": "Wa She Shu", "squaw creek": "Resort Chair", "aerial tram": "Tram", "gondola": "Base to Base Gondola", "funitel": "Funitel"}
def canon_of(n):
    n = re.sub(r"[^a-z0-9\- ]", "", (n or "").lower())
    for c in canon:
        if c.lower() in n: return c
    for a, c in alias.items():
        if a in n: return c
blog = collections.defaultdict(list)
for e in cal:
    if e["kind"] == "lift_first_run" and e["status"] != "cancelled":
        c = canon_of(e["lift"])
        if c: blog[(e["winter"], c)].append(e["date"])
d = lambda s: dt.date.fromisoformat(s)
by = collections.defaultdict(list)
for r in W: by[(r["winter"], r["side"])].append(r)
out = ["---", "type: reference", "project: Tahoe Rulebook", f"updated: {dt.date.today()}", "---", "", "# Opening progression by season (for the walk-through)", "",
 "**What this is.** The mountain opens in stages as snow builds and closes in stages as it melts. For every season and side, each lift's **first and last day with evidence it was running or meant to run** (named on a roster, reopened, run partially, delayed, or put on hold), from the ops tweets. `[B]` = the operations blog announced a first run within 3 days of that date; `[B date]` = the blog's date differs (a blog date can also be a reopening after a storm). These windows decide which lifts a whole-side closure applies to (decision 65).", "",
 "**How far to trust a side-winter.** *trusted* = at least 20 days that winter with a roster naming 3 or more of that side's lifts. *THIN* = mostly count-only schedule posts, so first days run late and last days early; closure rows there keep the old expansion and are flagged. Squaw Valley = the Palisades side before Sept 2021; Alpine Meadows = Alpine.", ""]
for w in sorted({r["winter"] for r in W}):
    out.append(f"## {w}")
    for side in ("palisades", "alpine", "link"):
        rows = by.get((w, side))
        if not rows: continue
        tr = rows[0]["side_trusted"] == "1" or side == "link"
        fd = sorted(r["first_day"] for r in rows); n = len(fd)
        spread = f", 90% of lifts running {(d(fd[max(int(n * .9) - 1, 0)]) - d(fd[0])).days} days after the first" if tr and n >= 5 else ""
        out += [f"**{side.capitalize()}** ({n} lifts{spread}) - {'trusted' if tr else 'THIN: treat dates as approximate'}", "| First day | Lifts (last day) |", "|---|---|"]
        g = collections.defaultdict(list)
        for r in sorted(rows, key=lambda r: (r["first_day"], r["lift"])):
            b = blog.get((w, r["lift"])); tag = ""
            if b:
                near = [x for x in b if abs((d(x) - d(r["first_day"])).days) <= 3]
                tag = " [B]" if near else f" [B {min(b)}]"
            g[r["first_day"]].append(f"{r['lift']} (to {r['last_day'][5:]}){tag}")
        for f in sorted(g): out.append(f"| {f} | {', '.join(g[f])} |")
        out.append("")
open(sys.argv[1], "w").write("\n".join(out) + "\n"); print(len(out), "lines ->", sys.argv[1])
