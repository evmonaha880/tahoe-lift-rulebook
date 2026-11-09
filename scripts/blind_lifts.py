"""Blind check of WHICH lifts and WHAT cause. Muse reads a held-out post cold and lists the lifts that are held/closed/delayed and the cause.
Compared with the parser's hold_start/closed_day/delay events for that post. usage: python3 -I scripts/blind_lifts.py 2023 2024 2025"""
import os, sys, json, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_posts import find_lifts, parse_post
K = open(os.path.expanduser("~/.config/meta/key")).read().strip()
root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "derived")
def ask(text):
    prompt = ("Ski resort lift-operations tweet. List ONLY lifts that this tweet says are on hold, closed, off schedule, or opening late/delayed "
              '(not lifts that are open or scheduled normally). Answer ONLY JSON: {"lifts":[names as written], "cause":"wind|mechanical|patrol|weather|none"}\n\nTweet:\n' + text)
    body = {"model": "muse-spark-1.3", "max_tokens": 2000, "reasoning_effort": "low", "messages": [{"role": "user", "content": prompt}]}
    try:
        r = urllib.request.Request("https://api.meta.ai/v1/chat/completions", data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + K, "Content-Type": "application/json"})
        c = json.load(urllib.request.urlopen(r, timeout=120))["choices"][0]["message"]["content"]; return json.loads(c[c.index("{"):c.rindex("}") + 1])
    except Exception as e: return None
tot = dict(posts=0, lifts_exact=0, jac=0.0, cause_eq=0, cause_n=0, err=0); bad = []
for Y in map(int, sys.argv[1:]):
    W = f"{Y}-{str(Y+1)[2:]}"; posts = json.load(open(os.path.join(root, f"{W}_heldout.json")))
    sel = []
    for p in posts:
        ev = [e for e in parse_post(p) if e["event_type"] in ("hold_start", "closed_day", "delay")]
        if ev: sel.append((p, ev))
    with ThreadPoolExecutor(6) as ex: outs = list(ex.map(lambda x: ask(x[0]["text"]), sel))
    s = dict(posts=0, lifts_exact=0, jac=0.0, cause_eq=0, cause_n=0, err=0)
    for (p, ev), o in zip(sel, outs):
        if o is None: s["err"] += 1; continue
        mine = {e["lift"] for e in ev if e["lift"] not in (None,)}; theirs = set()
        for n in o.get("lifts", []): theirs |= set(find_lifts(str(n)))
        if "ALL" in mine or not theirs and not mine: mine = mine - {"ALL"}
        j = len(mine & theirs) / len(mine | theirs) if mine | theirs else 1.0
        s["posts"] += 1; s["jac"] += j; s["lifts_exact"] += mine == theirs
        pc = {e["cause"] for e in ev if e["cause"]}; mc = o.get("cause", "none")
        if pc or mc != "none": s["cause_n"] += 1; s["cause_eq"] += (mc in pc) if pc else False
        if j < 1 and len(bad) < 400: bad.append((W, p["text"][:160], sorted(mine), sorted(theirs)))
    print(f"{W}: {s['posts']} posts with parser hold/close/delay | same lift set {s['lifts_exact']/s['posts']:.0%} | avg overlap {s['jac']/s['posts']:.0%} | cause agrees {s['cause_eq']}/{s['cause_n']} | reader errors {s['err']}")
    for k in tot: tot[k] += s[k]
print(f"ALL: {tot['posts']} posts | same lift set {tot['lifts_exact']/tot['posts']:.0%} | avg overlap {tot['jac']/tot['posts']:.0%} | cause agrees {tot['cause_eq']}/{tot['cause_n']}")
json.dump(bad, open(os.path.join(root, "lift_disagreements.json"), "w"))
