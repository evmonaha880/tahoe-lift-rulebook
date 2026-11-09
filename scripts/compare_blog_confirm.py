"""Check the third blog reader's (C) after-the-fact first-run statements and compare them with data/derived/first_run.csv.
Each quote must occur in its post (first 8 words, punctuation ignored); events that fail are dropped. Then each event is matched to the first-run record for the same winter and lift.
usage: python3 -I scripts/compare_blog_confirm.py   -> prints counts and data/derived/blog_confirm_C/compare.csv"""
import os, re, json, csv, glob, html, collections, datetime
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ns = {}; exec("\n".join(open(os.path.join(ROOT, "scripts", "parse_posts.py")).read().split("\n")[:93]), ns); find = ns["find_lifts"]
def squash(t):
    t = html.unescape(re.sub(r"<[^>]+>", " ", t)).lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()
POSTS = {}
for cat in ("operations", "general"):
    for r in json.load(open(os.path.join(ROOT, "data", "raw", "blog", cat + ".json"))): POSTS[r["id"]] = squash(r["content"]["rendered"] + " " + r["title"]["rendered"])
fr = {(r["winter"], r["lift"]): r for r in csv.DictReader(open(os.path.join(ROOT, "data", "derived", "first_run.csv")))}
out = []; bad = 0
for p in sorted(glob.glob(os.path.join(ROOT, "data", "derived", "blog_confirm_C", "out_C_*.json"))):
    w = os.path.basename(p)[6:13]
    for e in json.load(open(p))["events"]:
        q = " ".join(squash(e.get("quote") or "").split()[:8])
        if not (q and q in POSTS.get(e["post_id"], "") or q and q in POSTS.get(int(e["post_id"]) if str(e["post_id"]).isdigit() else -1, "")): bad += 1; continue
        for l in find(e["lift"] or "") or [e["lift"]]:
            r = fr.get((w, l)); d = e.get("date")
            if not r: res = "no_record"
            elif not d: res = "undated"
            else:
                gap = (datetime.date.fromisoformat(d) - datetime.date.fromisoformat(r["first_run"])).days
                res = "same_day" if gap == 0 else f"within_3d" if abs(gap) <= 3 else "later_restart_or_reopen" if gap > 0 else "earlier_than_ours"
            out.append(dict(winter=w, lift=l, c_date=d, c_status=e["status"], first_time=e.get("first_time"), ours=r["first_run"] if r else "", our_confidence=r["confidence"] if r else "", result=res, quote=e["quote"][:100]))
with open(os.path.join(ROOT, "data", "derived", "blog_confirm_C", "compare.csv"), "w", newline="") as fh:
    wr = csv.DictWriter(fh, list(out[0])); wr.writeheader(); wr.writerows(out)
print("quotes failing the check (dropped):", bad, "; events kept:", len(out))
print(collections.Counter(o["result"] for o in out)); print(collections.Counter(o["c_status"] for o in out))
print("by our confidence:", collections.Counter((o["our_confidence"].split("+")[0], o["result"]) for o in out))
