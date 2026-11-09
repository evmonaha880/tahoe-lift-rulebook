"""Replay one day: every post in order, what the parser read from it, and how each lift ended up in the dataset.
usage: python3 -I scripts/replay_day.py 2024-12-21 [--rows]     (posts are read from data/derived, never printed to a file)"""
import os, sys, json, csv, collections
from datetime import datetime, timedelta
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I mode does not put the script folder on the path
from config import LA
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "derived")
day = sys.argv[1]; y = int(day[:4]); W = f"{y}-{str(y+1)[2:]}" if int(day[5:7]) >= 8 else f"{y-1}-{str(y)[2:]}"
posts, ev = {}, collections.defaultdict(list)
for sp in ("train", "heldout"):
    for p in json.load(open(os.path.join(R, f"{W}_{sp}.json"))): p["split"] = sp; posts[p["id"]] = p
    for e in json.load(open(os.path.join(R, f"{W}_{sp}_events.json"))): ev[e["source_post_id"]].append(e)
def local(p):  # the parser's own local time is on its events; fall back to UTC-8
    es = ev.get(p["id"]); return es[0]["start"] if es else datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")).astimezone(LA).strftime("%Y-%m-%dT%H:%M")
day_posts = sorted([p for p in posts.values() if local(p)[:10] == day], key=lambda p: local(p))
print(f"=== {day}  ({W})  {len(day_posts)} posts ===")
for p in day_posts:
    print(f"\n[{local(p)[11:16]}] {p['split']}\n    " + p["text"].replace("&amp;", "&").replace("\n", "\n    "))
    g = collections.defaultdict(list)
    for e in ev.get(p["id"], []): g[(e["event_type"], e.get("cause"), e["lift"] if e["lift"] and e["lift"].startswith("ALL") else None, tuple(e.get("except", [])))].append(e["lift"])
    for (t, c, scope, exc), lifts in g.items():
        who = f"{scope} except {list(exc)}" if scope else ", ".join(l or "-" for l in lifts)
        print(f"      -> {t}{' ('+c+')' if c else ''}: {who}")
if "--rows" in sys.argv or True:
    rows = [r for r in csv.DictReader(open(os.path.join(R, "lift_days.csv"))) if r["date"] == day]
    print("\n--- dataset rows for the day (what the model is graded on) ---")
    for r in sorted(rows, key=lambda r: (r["side"], r["lift"])):
        print(f"  {r['side'][:3]:3s} {r['lift']:22s} sched={r['scheduled'][0]} held={r['held']} cause={'wind' if r['held_wind']=='1' else 'unst' if r['held_unstated']=='1' else '-'} reopened={r['reopen_posted']} mins={r['hold_minutes']}")
