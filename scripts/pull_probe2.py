import json, os, urllib.request, urllib.parse, urllib.error, collections, datetime as dt
def get(url, headers=None, timeout=60):
    req = urllib.request.Request(url, headers=headers or {"User-Agent":"tahoe-lift-rulebook/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
    except Exception as e: return f"ERR {e}", b""

# 1. Synoptic: does a recent window work, what is the reading interval and which vars come back?
tok = open(os.path.expanduser("~/.config/synoptic/token")).read().strip()
for stid, s, e in [("SIBSV","202601150000","202601160000"),("SIBSV","202511150000","202511160000"),("SIBSV","202511010000","202511020000")]:
    q = urllib.parse.urlencode({"token":tok,"stid":stid,"start":s,"end":e,"vars":"wind_speed,wind_gust,wind_direction,air_temp,snow_depth","units":"english","obtimezone":"local"})
    st, body = get("https://api.synopticdata.com/v2/stations/timeseries?"+q); j = json.loads(body); sm=j["SUMMARY"]; sta=j.get("STATION") or []
    if sta:
        o=sta[0]["OBSERVATIONS"]; d=o["date_time"]; a=dt.datetime.fromisoformat(d[0].replace("Z","+00:00")); b=dt.datetime.fromisoformat(d[1].replace("Z","+00:00"))
        print(stid,s[:8],"OK obs",len(d),"step_min",int((b-a).total_seconds()//60),"vars",sorted(k for k in o if k!="date_time"))
    else: print(stid,s[:8],sm.get("RESPONSE_CODE"),sm.get("RESPONSE_MESSAGE"))
# 2. X counts per winter (Oct 1 - May 31), 2016-17 .. 2023-24
bearer = open(os.path.expanduser("~/.config/x-api/bearer")).read().strip()
h = {"Authorization":"Bearer "+bearer,"User-Agent":"tahoe-lift-rulebook/0.1"}
spent = 0
print("== @palisadesops posts per winter (Oct-May)")
for y in range(2016, 2024):
    q = urllib.parse.urlencode({"query":"from:palisadesops","granularity":"day","start_time":f"{y}-10-01T00:00:00Z","end_time":f"{y+1}-06-01T00:00:00Z"})
    tot=0; pages=0; nxt=None; first=None
    while pages<14:
        st, body = get("https://api.x.com/2/tweets/counts/all?"+q+(("&next_token="+nxt) if nxt else ""), h)
        if st!=200: print(y,"http",st,body[:120]); break
        j=json.loads(body); pages+=1; spent+=0.01
        for d in j.get("data",[]):
            tot+=d["tweet_count"]
            if d["tweet_count"] and (first is None or d["start"]<first): first=d["start"][:10]
        nxt=(j.get("meta") or {}).get("next_token")
        if not nxt: break
    print(f" winter {y}-{str(y+1)[2:]}: {tot} posts, first post day {first}, pages {pages}, ~${tot*0.005:.2f} to pull")
print("sizing spent about $%.2f"%spent)
