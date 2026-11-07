"""Pull Palisades Tahoe / Alpine Meadows weather-station history from the Western Weather Group public report builder.
No login. Polite: sequential, 1 s pause, resumable. Output: data/raw/wwg/<interval>/<winter>_<month>.csv
usage: python3 -I scripts/pull_wwg.py test | run <interval_minutes> [first_winter last_winter]"""
import os, sys, json, time, base64, calendar, urllib.request, urllib.parse
H={"User-Agent":"Mozilla/5.0 tahoe-lift-rulebook (research, hackathon)"}; B="https://palisadestahoe.westernweathergroup.com"
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data","raw","wwg")
STATIONS=["BMT","FNT","KT22","OVB","RHB","RHT","SCB","SCT","SHR","SIB","SUM","TLC","YVH"]
def http(path, data=None, timeout=300):
    d=urllib.parse.urlencode(data).encode() if data is not None else None
    with urllib.request.urlopen(urllib.request.Request(B+path,data=d,headers=H),timeout=timeout) as r: return r.read()
def all_fields(interval):
    fs=[]
    for s in STATIONS:
        j=json.loads(http("/reportbuilderapi/fields?oid=",{"reportType":"Tabular","stationIds":s,"groupIds":"","interval":str(interval)}))
        for c in j["choices"]:
            if c["value"] not in fs: fs.append(c["value"])
        time.sleep(0.3)
    return fs
def export_url(start,end,interval,fields):
    spec={"Stations":STATIONS,"Groups":[],"Fields":fields,"Deltas":[],"Interval":interval,"Type":"Tabular",
          "DateRange":{"$type":"WesternWeatherGroup.CustomReportDateRange, WesternWeatherGroup.Core","Start":start,"End":end},
          "DateDescription":f"{start} to {end}","Title":"export","Subtitle":"Palisades Tahoe"}
    return "/reports/export/csv?data="+urllib.parse.quote(base64.b64encode(json.dumps(spec,separators=(",",":")).encode()).decode())
def month_ranges(winter_start_year):
    for y,m in [(winter_start_year,10),(winter_start_year,11),(winter_start_year,12)]+[(winter_start_year+1,k) for k in range(1,6)]:
        yield f"{y}-{m:02d}-01", f"{y}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}", f"{y}-{m:02d}"
if __name__=="__main__":
    mode=sys.argv[1]
    if mode=="test":
        f=all_fields(60); print("union fields",len(f),f)
        t0=time.time(); b=http(export_url("2023-12-01","2023-12-31",60,f)); lines=b.decode("utf-8-sig","replace").splitlines()
        print("direct export ok: lines",len(lines),"bytes",len(b),"secs",round(time.time()-t0,1)); print(lines[0][:400]); print(lines[1][:300] if len(lines)>1 else "")
    else:
        interval=int(sys.argv[2]); y0=int(sys.argv[3]) if len(sys.argv)>3 else 2016; y1=int(sys.argv[4]) if len(sys.argv)>4 else 2025
        d=os.path.join(OUT,f"{interval}min"); os.makedirs(d,exist_ok=True); fields=all_fields(interval); print("fields",len(fields),flush=True)
        for w in range(y0,y1+1):
            for a,b_,tag in month_ranges(w):
                fn=os.path.join(d,f"{tag}.csv")
                if os.path.exists(fn) and os.path.getsize(fn)>200: continue
                try:
                    body=http(export_url(a,b_,interval,fields)); open(fn,"wb").write(body); print(tag,"lines",body.count(b"\n"),"bytes",len(body),flush=True)
                except Exception as e: print(tag,"FAILED",type(e).__name__,e,flush=True)
                time.sleep(1.0)
