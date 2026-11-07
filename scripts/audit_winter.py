"""Deep audit of one winter's TRAINING posts: (1) template inventory with what the parser did, (2) every case where BOTH blind readers
disagree with the parser. Never touches the held-out file. usage: python3 -I scripts/audit_winter.py 2023 [shapes|dis] [limit]"""
import os, sys, re, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_posts import parse_post
Y = int(sys.argv[1]); mode = sys.argv[2] if len(sys.argv) > 2 else "dis"; N = int(sys.argv[3]) if len(sys.argv) > 3 else 40
W = f"{Y}-{str(Y+1)[2:]}"; d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "derived")
posts = json.load(open(os.path.join(d, f"{W}_train.json")))
clean = lambda t: " ".join(re.sub(r"https?://\S+", "", t.replace("&amp;", "&")).split())
if mode == "shapes":
    sh = collections.defaultdict(list)
    for p in posts:
        k = re.sub(r"\d+", "N", clean(p["text"]))[:45]; sh[k].append(p)
    print(f"{W}: {len(posts)} train posts, {len(sh)} distinct 45-char openings")
    for k, ps in sorted(sh.items(), key=lambda kv: -len(kv[1]))[:N]:
        ev = parse_post(ps[0]); print(f"{len(ps):3}x  {k:45} -> {sorted({e['event_type'] for e in ev})}")
else:
    sq = json.load(open(os.path.join(d, f"{W}_train_labels_subq.json"))); mu = json.load(open(os.path.join(d, f"{W}_train_labels_muse.json")))
    M = {"hold": "hold_start", "closed": "closed_day", "delay": "delay", "reopen": "reopen", "partial": "partial", "schedule": "scheduled_opening", "parking": "parking"}
    out = []
    for p in posts:
        i = p["id"]
        if "error" in sq.get(i, {"error": 1}) or "error" in mu.get(i, {"error": 1}): continue
        have = {e["event_type"] for e in parse_post(p)}
        for c, t in M.items():
            s, m, par = sq[i][c] > .5, mu[i][c] >= .5, t in have
            if s == m != par: out.append((c, "PARSER MISSED" if s else "PARSER OVER-CLAIMED", clean(p["text"])[:200]))
    cnt = collections.Counter((c, k) for c, k, _ in out)
    print(f"{W}: {len(out)} cases where both readers agree and the parser differs:", dict(cnt))
    shown = collections.Counter()
    for c, k, t in out:
        if shown[(c, k)] < max(2, N // 12): print(f"[{c}/{k}] {t}"); shown[(c, k)] += 1
