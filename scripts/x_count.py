"""Size X posts for one winter with the counts endpoint ($0.01 per request). Prints totals only, never the key.
usage: python3 -I scripts/x_count.py 2023                      (winter starting year, 3 queries)
       python3 -I scripts/x_count.py 2023 2023-10-01 2023-12-15   (originals only, custom window; end exclusive)"""
import os, sys, json, urllib.request, urllib.parse
KEY = open(os.path.expanduser("~/.config/x-api/bearer")).read().strip()
Y = int(sys.argv[1])
START = sys.argv[2] if len(sys.argv) > 3 else f"{Y}-10-01"
END = sys.argv[3] if len(sys.argv) > 3 else f"{Y+1}-06-01"
QUERIES = {
    "all (incl replies, retweets)": "from:palisadesops",
    "originals + replies (-is:retweet)": "from:palisadesops -is:retweet",
    "originals only (-is:retweet -is:reply)": "from:palisadesops -is:retweet -is:reply",
}
if len(sys.argv) > 3: QUERIES = {k: v for k, v in QUERIES.items() if "originals only" in k}
for label, q in QUERIES.items():
    p = {"query": q, "granularity": "day", "start_time": f"{START}T00:00:00Z", "end_time": f"{END}T00:00:00Z"}
    total, reqs, nxt = 0, 0, None
    while True:
        if nxt: p["next_token"] = nxt
        r = urllib.request.Request("https://api.x.com/2/tweets/counts/all?" + urllib.parse.urlencode(p),
                                   headers={"Authorization": "Bearer " + KEY})
        with urllib.request.urlopen(r, timeout=60) as resp: j = json.load(resp)
        reqs += 1
        total += sum(d["tweet_count"] for d in j.get("data", []))
        nxt = j.get("meta", {}).get("next_token")
        if not nxt: break
    print(f"{label}: {total} posts, {reqs} request(s), pull cost ~${total*0.005:.2f}")
