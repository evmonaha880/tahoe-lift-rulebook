"""Pull the free sources in full: SNOTEL 784 hourly (Oct 1 - May 31, every winter) and the ENSO indices."""
import os, urllib.request, urllib.error, csv, io, time
RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
def get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": "tahoe-lift-rulebook/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()
for name, url in [("oni.txt","https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"),("roni.txt","https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt")]:
    open(os.path.join(RAW,"enso",name),"wb").write(get(url)); print("enso", name)
els = "WTEQ::value,SNWD::value,PREC::value,TOBS::value,WSPDV::value,WSPDX::value,WDIRV::value"
base = "https://wcc.sc.egov.usda.gov/reportGenerator/view_csv/customSingleStationReport/hourly/784:CA:SNTL%7Cid=%22%22%7Cname/{a},{b}/{e}"
print("winter, rows, wind_avg_nonblank, depth_nonblank, temp_nonblank")
for y in range(2008, 2026):
    try:
        body = get(base.format(a=f"{y}-10-01", b=f"{y+1}-05-31", e=els)).decode("utf-8","replace")
    except Exception as e:
        print(f"{y}-{str(y+1)[2:]}", "FAILED", e); continue
    open(os.path.join(RAW,"snotel",f"784_hourly_{y}-{str(y+1)[2:]}.csv"),"w").write(body)
    rows = list(csv.reader(l for l in body.splitlines() if l and not l.startswith("#")))
    hdr, data = rows[0], rows[1:]
    def nb(col):
        i = [k for k,h in enumerate(hdr) if h.startswith(col)]
        return sum(1 for r in data if i and len(r)>i[0] and r[i[0]].strip()) if i else None
    print(f"{y}-{str(y+1)[2:]}", len(data), nb("Wind Speed Average"), nb("Snow Depth"), nb("Air Temperature"))
    time.sleep(0.5)
