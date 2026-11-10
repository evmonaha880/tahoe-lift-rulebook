"""Pull one winter (Oct 1 to May 31) of ORIGINAL posts (no retweets, no replies) from any account through the X full-archive search. $0.005 per post read. Raw to data/raw/x_<account>/<winter>.json (git-ignored).
Compare with the count you expect first (scripts/x_count.py style); a pull far from the count is reported. Never prints the key. Nothing is written on an HTTP error.
usage: python3 -I scripts/x_pull_account.py TahoeWeather 2015 [expected_count]"""
import os, sys, json, time, urllib.request, urllib.parse, urllib.error
KEY = open(os.path.join(os.environ.get("KEY_DIR", os.path.expanduser("~/.config")), "x-api", "bearer")).read().strip()
acct, Y = sys.argv[1], int(sys.argv[2]); exp = int(sys.argv[3]) if len(sys.argv) > 3 else None
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", f"x_{acct.lower()}", f"{Y}-{str(Y + 1)[2:]}.json")
if os.path.exists(OUT): raise SystemExit(f"{OUT} exists; not pulling again (no double spend)")
p = {"query": f"from:{acct} -is:retweet -is:reply", "max_results": "500", "tweet.fields": "created_at,conversation_id,referenced_tweets,lang,attachments,public_metrics",
     "start_time": f"{Y}-10-01T00:00:00Z", "end_time": f"{Y + 1}-06-01T00:00:00Z"}
posts, pages, nxt = [], 0, None
while True:
    if nxt: p["next_token"] = nxt
    r = urllib.request.Request("https://api.x.com/2/tweets/search/all?" + urllib.parse.urlencode(p), headers={"Authorization": "Bearer " + KEY})
    try:
        with urllib.request.urlopen(r, timeout=90) as resp: j = json.load(resp)
    except urllib.error.HTTPError as e: print("FAILED: HTTP", e.code, e.read()[:200], "- nothing written"); sys.exit(1)
    pages += 1; posts += j.get("data", []); nxt = j.get("meta", {}).get("next_token")
    if not nxt: break
    time.sleep(1.1)
if not posts: print("no posts - nothing written"); sys.exit(2)
os.makedirs(os.path.dirname(OUT), exist_ok=True); json.dump(posts, open(OUT + ".tmp", "w")); os.replace(OUT + ".tmp", OUT)
ds = sorted(x["created_at"] for x in posts)
print(f"{acct} {Y}-{str(Y + 1)[2:]}: {len(posts)} posts, {pages} page(s), ~${len(posts) * 0.005:.2f}; {ds[0][:10]} to {ds[-1][:10]}" + (f"; expected {exp}" + ("" if abs(len(posts) - exp) <= max(5, exp // 20) else "  <-- DIFFERS") if exp else ""))
