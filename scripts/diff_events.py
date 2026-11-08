"""Compare two sets of parsed events and show what changed, grouped by post. Ignores bookkeeping fields (parser_version, note, confidence).
usage: python3 -I scripts/diff_events.py <old_derived_dir | results/baseline_events.json.gz> [<new_derived_dir=data/derived>] [--show N]
Exit 0 always; read the output. Use after every parser change: only the posts you meant to change should appear."""
import os, sys, json, glob, gzip, collections
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
_argv = sys.argv[1:]; _sv = _argv[_argv.index("--show") + 1] if "--show" in _argv else None
args = [a for a in _argv if not a.startswith("--") and a != _sv]
old_dir = args[0]; new_dir = args[1] if len(args) > 1 else os.path.join(root, "data", "derived")
show = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 15
key = lambda e: (e["source_post_id"], e["event_type"], e["lift"], e.get("cause"), tuple(e.get("except", [])))
added, removed = collections.defaultdict(list), collections.defaultdict(list)
OLD = json.load(gzip.open(old_dir, "rt")) if old_dir.endswith(".gz") else None
for f in sorted(glob.glob(os.path.join(new_dir, "*_events.json"))):
    o = os.path.join(old_dir, os.path.basename(f)) if OLD is None else None
    if OLD is None and not os.path.exists(o): print("missing in old:", os.path.basename(f)); continue
    A = collections.Counter(map(key, OLD[os.path.basename(f)] if OLD is not None else json.load(open(o)))); B = collections.Counter(map(key, json.load(open(f))))
    for k, n in (A - B).items(): removed[k[0]].append(f"{k[1]}:{k[2]}({k[3]})")
    for k, n in (B - A).items(): added[k[0]].append(f"{k[1]}:{k[2]}({k[3]})")
posts = sorted(set(added) | set(removed))
print(f"{len(posts)} posts changed; {sum(map(len, added.values()))} events added, {sum(map(len, removed.values()))} removed")
for pid in posts[:show]: print(pid, "\n   -", "; ".join(removed.get(pid, []))[:200], "\n   +", "; ".join(added.get(pid, []))[:200])
if len(posts) > show: print(f"... {len(posts) - show} more (use --show N)")
