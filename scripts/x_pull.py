"""Pull one winter of the ops account's original posts (no retweets, no replies) from the X full-archive search.
Costs $0.005 per post read. Raw output goes to data/raw/x/ (git-ignored). Never prints the key.
usage: python3 -I scripts/x_pull.py 2023      (winter starting year: Oct 1 to May 31)"""
import os, sys, json, time, urllib.request, urllib.parse, urllib.error
KEY = open(os.path.expanduser("~/.config/x-api/bearer")).read().strip()
Y = int(sys.argv[1])
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", "x", f"{Y}-{str(Y+1)[2:]}.json")
p = {"query": "from:palisadesops -is:retweet -is:reply", "max_results": "500",
     "tweet.fields": "created_at,conversation_id,referenced_tweets,lang",
     "start_time": f"{Y}-10-01T00:00:00Z", "end_time": f"{Y+1}-06-01T00:00:00Z"}
posts, pages, nxt = [], 0, None
while True:
    if nxt: p["next_token"] = nxt
    r = urllib.request.Request("https://api.x.com/2/tweets/search/all?" + urllib.parse.urlencode(p),
                               headers={"Authorization": "Bearer " + KEY})
    try:
        with urllib.request.urlopen(r, timeout=90) as resp: j = json.load(resp)
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read()[:200]); break
    pages += 1
    posts += j.get("data", [])
    nxt = j.get("meta", {}).get("next_token")
    if not nxt: break
    time.sleep(1.1)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(posts, open(OUT, "w"))
ds = sorted(x["created_at"] for x in posts)
print(f"{len(posts)} posts, {pages} page(s), ~${len(posts)*0.005:.2f}; {ds[0][:10]} to {ds[-1][:10]}" if posts else "no posts")
