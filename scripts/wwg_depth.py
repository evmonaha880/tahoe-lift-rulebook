import re, urllib.request, urllib.parse, collections, csv, io
H={"User-Agent":"Mozilla/5.0"}; B="https://palisadestahoe.westernweathergroup.com"
ST="BMT,FNT,KT22,OVB,RHB,RHT,SCB,SCT,SHR,SIB,SUM,TLC,YVH"
def get(path):
    with urllib.request.urlopen(urllib.request.Request(B+path,headers=H),timeout=180) as x: return x.read().decode("utf-8-sig","replace")
def pull(y1,m1,d1,y2,m2,d2,interval,fields,stations=ST):
    p="/reports/view?"+urllib.parse.urlencode({"reportType":"Tabular","stations":stations,"groups":"","interval":interval,"fields":fields,"dateType":"DateRange",
       "dateStartMonth":m1,"dateStartDay":d1,"dateStartYear":y1,"dateEndMonth":m2,"dateEndDay":d2,"dateEndYear":y2})
    html=get(p); m=re.findall(r'(/reports/export/csv\?data=[A-Za-z0-9%_=\-]+)',html)
    return get(m[0]) if m else ""
rows={}
for y in range(2016,2026):
    txt=pull(y,12,15,y,12,16,15,"WindSpeed,WindMax")
    r=list(csv.DictReader(io.StringIO(txt))); c=collections.Counter(x["Station"] for x in r if x.get("Wind Spd (mph)","").strip() not in ("","-"))
    rows[y]=c
names=sorted({s for c in rows.values() for s in c})
print("Dec 15-16 rows with wind speed, 15-minute interval (max 192 per station)")
print("station".ljust(32), *[str(y) for y in range(2016,2026)])
for n in names: print(n.ljust(32), *[str(rows[y].get(n,0)).rjust(4) for y in range(2016,2026)])
t=pull(2023,12,15,2023,12,15,1,"WindSpeed,WindMax",stations="FNT,KT22")
print("1-minute test, FNT+KT22 on 2023-12-15: lines",len(t.splitlines()))
