"""Pull National Weather Service (Reno office) warnings, watches and advisories from the Iowa Environmental Mesonet archive. Free, no key.
Keeps the events for the Greater Lake Tahoe Area zone (CAZ073, which covers Olympic Valley and Alpine Meadows: UNVERIFIED, read from the zone name) and writes data/raw/nws/vtec_REV_<year>.json plus data/derived/nws_alerts.csv (one row per event).
usage: python3 -I scripts/pull_nws.py"""
import os, json, csv, urllib.request
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
os.makedirs(os.path.join(ROOT, "data", "raw", "nws"), exist_ok=True)
ZONES = {"CAZ073"}
out = []
for Y in range(2018, 2027):
    f = os.path.join(ROOT, "data", "raw", "nws", f"vtec_REV_{Y}.json")
    if not os.path.exists(f):
        with urllib.request.urlopen(f"https://mesonet.agron.iastate.edu/json/vtec_events_bywfo.py?wfo=REV&year={Y}", timeout=60) as r: open(f, "wb").write(r.read())
    for e in json.load(open(f))["events"]:
        if e["ugc"] in ZONES: out.append((e["phenomena"], e["significance"], e["issue"], e["expire"], e["eventid"], e["ugc"]))
out.sort(key=lambda x: x[2])
with open(os.path.join(ROOT, "data", "derived", "nws_alerts.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["phenomena", "significance", "issue_utc", "expire_utc", "eventid", "ugc"]); w.writerows(out)
import collections
print(len(out), "events in", ",".join(ZONES)); print(collections.Counter(f"{a}.{b}" for a, b, *_ in out).most_common(14))
