"""Probe every data source for depth, detail and cost before the full pull.
Prints status only. Never prints tokens."""
import json, os, sys, urllib.request, urllib.parse, urllib.error, collections, datetime as dt

def get(url, headers=None, timeout=60):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "tahoe-lift-rulebook/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}", b""

def synoptic_probe():
    tok = open(os.path.expanduser("~/.config/synoptic/token")).read().strip()
    print("== Synoptic (weather stations)")
    for stid, start, end in [("SIBSV","201612150000","201612160000"),("SIBSV","201812150000","201812160000"),
                             ("SIBSV","202312150000","202312160000"),("RHBAM","201612150000","201612160000"),
                             ("OVBOW","202502200000","202502210000")]:
        q = urllib.parse.urlencode({"token":tok,"stid":stid,"start":start,"end":end,
             "vars":"wind_speed,wind_gust,wind_direction,air_temp,snow_depth","units":"english","obtimezone":"local"})
        st, body = get("https://api.synopticdata.com/v2/stations/timeseries?"+q)
        try:
            j = json.loads(body); s = j.get("SUMMARY",{}); sta = j.get("STATION") or []
            n = 0; step = None; keys = []
            if sta:
                o = sta[0]["OBSERVATIONS"]; keys = sorted(k for k in o if k!="date_time")
                dts = o.get("date_time",[]); n = len(dts)
                if n>2:
                    a = dt.datetime.fromisoformat(dts[0].replace("Z","+00:00")); b = dt.datetime.fromisoformat(dts[1].replace("Z","+00:00"))
                    step = int((b-a).total_seconds()//60)
            print(stid, start[:8], "http",st, "| code",s.get("RESPONSE_CODE"), (s.get("RESPONSE_MESSAGE") or "")[:80], "| obs",n, "| step_min",step, "| vars",keys)
        except Exception as e:
            print(stid, start[:8], "http",st, "non-JSON", body[:120])

def snotel_probe():
    print("== SNOTEL 784")
    base = "https://wcc.sc.egov.usda.gov/reportGenerator/view_csv/customSingleStationReport/{iv}/784:CA:SNTL%7Cid=%22%22%7Cname/{a},{b}/{els}"
    for iv,a,b,els in [("hourly","2023-12-15","2023-12-16","WTEQ::value,SNWD::value,TOBS::value,WSPDV::value,WSPDX::value,WDIRV::value"),
                       ("hourly","2009-01-15","2009-01-16","WSPDV::value,WSPDX::value,WDIRV::value,TOBS::value"),
                       ("daily","1980-01-15","1980-01-20","WTEQ::value,TOBS::value")]:
        st, body = get(base.format(iv=iv,a=a,b=b,els=els))
        lines = [l for l in body.decode("utf-8","replace").splitlines() if l and not l.startswith("#")]
        print(iv, a, "http",st, "| rows",max(len(lines)-1,0), "| header", (lines[0][:150] if lines else None), "| sample", (lines[1][:120] if len(lines)>1 else None))

def enso_probe():
    print("== ENSO indices")
    for name,url in [("ONI","https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"),("RONI","https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt")]:
        st, body = get(url); t = body.decode("utf-8","replace").splitlines()
        print(name,"http",st,"| lines",len(t),"| first",t[1][:60] if len(t)>1 else None,"| last",t[-1][:60] if t else None)

def x_counts():
    print("== X API counts (@palisadesops), all-counts $0.01/request")
    bearer = open(os.path.expanduser("~/.config/x-api/bearer")).read().strip()
    h = {"Authorization":"Bearer "+bearer,"User-Agent":"tahoe-lift-rulebook/0.1"}
    q = urllib.parse.urlencode({"query":"from:palisadesops","granularity":"day","start_time":"2015-10-01T00:00:00Z","end_time":"2026-06-01T00:00:00Z"})
    tot = collections.Counter(); pages=0; nxt=None
    while pages < 14:
        url = "https://api.x.com/2/tweets/counts/all?"+q+(("&next_token="+nxt) if nxt else "")
        st, body = get(url, h)
        if st != 200: print("http",st, body[:200]); break
        j = json.loads(body); pages+=1
        for d in j.get("data",[]):
            y = d["start"][:7]; tot[y] += d["tweet_count"]
        nxt = (j.get("meta") or {}).get("next_token")
        if not nxt: break
    print("pages",pages,"| months with posts",len(tot))
    wint = collections.Counter()
    for ym,c in tot.items():
        y,m = int(ym[:4]),int(ym[5:])
        w = y if m>=7 else y-1
        wint[f"{w}-{str(w+1)[2:]}"] += c
    for w in sorted(wint): print(" winter",w,"posts",wint[w],"~$%.2f"%(wint[w]*0.005))
    print(" TOTAL posts",sum(wint.values()),"~$%.2f"%(sum(wint.values())*0.005))

if __name__ == "__main__":
    for f in (synoptic_probe, snotel_probe, enso_probe, x_counts):
        try: f()
        except Exception as e: print(f.__name__,"FAILED",type(e).__name__,e)
