"""Blind second reader: an independent model labels posts WITHOUT seeing the parser's output.
usage: python3 -I scripts/blind_label.py <subq|muse> 2023 <train|heldout> [max_posts]
Writes data/derived/<winter>_<split>_labels_<provider>.json  {post_id: {class: prob_or_0/1}}. Never prints keys."""
import os, sys, json, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
prov, Y, split = sys.argv[1], int(sys.argv[2]), sys.argv[3]
N = int(sys.argv[4]) if len(sys.argv) > 4 else None
W = f"{Y}-{str(Y+1)[2:]}"; root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "derived")
posts = json.load(open(os.path.join(root, f"{W}_{split}.json")))[:N]
Q = {
 "hold": "Does the post say a ski lift is on hold (stopped, or not starting) or is about to go on hold?",
 "closed": "Does the post say a ski lift is closed or off the schedule for the day or the rest of the day?",
 "delay": "Does the post say a ski lift is opening late or is delayed?",
 "reopen": "Does the post say a ski lift is now open, has reopened, or is back up and running?",
 "partial": "Does the post say a lift has limited operation (downloads only, mid-station only, one side only, reduced speed)?",
 "schedule": "Is the post a morning plan listing which lifts will run and their hours?",
 "parking": "Is the post about parking lot status?",
}
def key(n): return open(os.path.join(os.environ.get("KEY_DIR", os.path.expanduser("~/.config")), n, "key")).read().strip()
def call(url, body, k):
    for attempt in range(3):
        try:
            r = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Authorization": "Bearer " + k, "Content-Type": "application/json"})
            with urllib.request.urlopen(r, timeout=120) as resp: return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 2: time.sleep(2 + attempt * 3); continue
            return {"error": e.code}
        except Exception as e: return {"error": str(e)[:80]}
    return {"error": "retries"}
def subq(p):
    qs = {c: {"type": "noul", "instructions": q, "criteria": {"true": "Yes, the post says this", "false": "No"}} for c, q in Q.items()}
    j = call("https://api.subq.ai/v1/systemone", {"model": "subq-snap-1.1", "state": p["text"], "questions": qs}, K)
    if "answers" not in j: return p["id"], {"error": str(j)[:100]}
    return p["id"], {c: j["answers"][c]["noul"] for c in Q}
def muse(p):
    prompt = ("You label one tweet from a ski resort lift-operations account. Answer ONLY a JSON object with these boolean keys:\n" +
              "\n".join(f'"{c}": {q}' for c, q in Q.items()) + "\n\nTweet:\n" + p["text"])
    j = call("https://api.meta.ai/v1/chat/completions", {"model": "muse-spark-1.3", "max_tokens": 2000, "reasoning_effort": "low",
             "messages": [{"role": "user", "content": prompt}]}, K)
    try:
        c = j["choices"][0]["message"]["content"]; c = c[c.index("{"):c.rindex("}") + 1]; d = json.loads(c)
        return p["id"], {k: (1.0 if d.get(k) else 0.0) for k in Q}
    except Exception: return p["id"], {"error": str(j)[:100]}
K = key("subq" if prov == "subq" else "meta"); fn = subq if prov == "subq" else muse
with ThreadPoolExecutor(6) as ex: out = dict(ex.map(fn, posts))
errs = sum("error" in v for v in out.values())
json.dump(out, open(os.path.join(root, f"{W}_{split}_labels_{prov}.json"), "w"))
print(f"{prov}: {len(out)-errs} labelled, {errs} errors"); 
if errs: print(next(v for v in out.values() if "error" in v))
