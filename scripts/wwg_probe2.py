import json, re, urllib.request, urllib.parse, base64
H={"User-Agent":"Mozilla/5.0"}; B="https://palisadestahoe.westernweathergroup.com"
def get(path):
    try:
        with urllib.request.urlopen(urllib.request.Request(B+path,headers=H),timeout=120) as x: return x.status, x.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e: return e.code, e.read().decode("utf-8","replace")
ST="BMT,FNT,KT22,OVB,RHB,RHT,SCB,SCT,SHR,SIB,SUM,TLC,YVH"
def q(y1,m1,d1,y2,m2,d2,interval=60,fields="WindSpeed,WindMax,WindDir,Temp,RH"):
    return urllib.parse.urlencode({"reportType":"Tabular","stations":ST,"groups":"","interval":interval,"fields":fields,"dateType":"DateRange",
        "dateStartMonth":m1,"dateStartDay":d1,"dateStartYear":y1,"dateEndMonth":m2,"dateEndDay":d2,"dateEndYear":y2})
for dt in ("DateRange","99"):
    p="/reports/view?"+q(2016,12,1,2016,12,4).replace("dateType=DateRange","dateType="+dt)
    st,html=get(p); print("view",dt,st,len(html), "| csv link:", re.findall(r'(/reports/export/csv\?data=[A-Za-z0-9%_=\-]+)',html)[:1] and "found" or "none", "| title", re.findall(r'<title>(.*?)</title>',html,flags=re.S)[:1])
    m=re.findall(r'(/reports/export/csv\?data=[A-Za-z0-9%_=\-]+)',html)
    if m:
        link=m[0]; spec=json.loads(base64.b64decode(urllib.parse.unquote(link.split("data=")[1]))); print("spec DateRange:",json.dumps(spec.get("DateRange")), "| Interval",spec.get("Interval"))
        st2,csv=get(link); lines=csv.splitlines(); print("csv",st2,"lines",len(lines)); print("\n".join(lines[:4])[:600]); break
    else:
        print(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',html))[:300])
