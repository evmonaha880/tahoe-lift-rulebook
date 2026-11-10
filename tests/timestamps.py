"""Timestamp snapshot test. The golden cases all use one timestamp (a Saturday, 9:01am Pacific), so date logic ("tomorrow", weekday names,
time-of-day reasoning, daylight saving) is barely tested. This runs every golden case at 16 different timestamps and compares a hash of the
full event output with results/parser_timestamp_snapshot.json. It does not say the output is right, only that a refactor left it unchanged.
usage: python3 -I tests/timestamps.py --check | --write"""
import os, sys, json, hashlib
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "scripts")); sys.path.insert(0, here)
from parse_posts import parse_post
from golden import CASES
OUT = os.path.join(here, "..", "results", "parser_timestamp_snapshot.json")
STAMPS = ["2024-01-13T17:01:00.000Z", "2024-01-15T15:30:00.000Z", "2024-01-17T04:10:00.000Z", "2024-01-19T23:45:00.000Z", "2024-02-02T14:00:00.000Z",
          "2024-03-09T08:00:00.000Z", "2024-03-10T17:30:00.000Z", "2024-03-11T16:00:00.000Z", "2024-04-21T19:00:00.000Z", "2024-11-02T16:00:00.000Z",
          "2024-11-03T17:00:00.000Z", "2023-12-31T20:00:00.000Z", "2023-01-01T08:00:00.000Z", "2019-02-14T15:00:00.000Z", "2016-12-03T17:00:00.000Z", "2017-03-26T14:00:00.000Z"]
def snap():
    out = {}
    for i, (text, _m, _n) in enumerate(CASES, 1):
        h = hashlib.sha256()
        for ts in STAMPS:
            ev = parse_post({"id": "t", "created_at": ts, "text": text})
            h.update(json.dumps(sorted(json.dumps(e, sort_keys=True, default=str) for e in ev)).encode())
        out[str(i)] = h.hexdigest()[:12]
    return out
if __name__ == "__main__":
    now = snap(); mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "--write": json.dump(now, open(OUT, "w"), indent=0, sort_keys=True); print(f"recorded {len(now)} cases x {len(STAMPS)} timestamps")
    elif mode == "--check":
        old = json.load(open(OUT)); moved = [k for k in sorted(set(old) | set(now), key=int) if old.get(k) != now.get(k)]
        for k in moved: print("CHANGED golden case #" + k)
        print(f"{len(now) - len(moved)}/{len(old)} cases identical at all {len(STAMPS)} timestamps"); sys.exit(1 if moved else 0)
    else: print(__doc__)
