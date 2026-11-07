import json, re, urllib.request, urllib.parse
H={"User-Agent":"Mozilla/5.0"}; B="https://palisadestahoe.westernweathergroup.com"
def req(path, data=None):
    d = urllib.parse.urlencode(data).encode() if data is not None else None
    r = urllib.request.Request(B+path, data=d, headers=H, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(r, timeout=90) as x: return x.status, x.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e: return e.code, e.read().decode("utf-8","replace")
st,b=req("/reportbuilderapi/stations?oid="); print("stations",st,b[:300])
st,b=req("/reportbuilderapi/groups?oid="); print("groups",st,b[:300])
st,b=req("/reportbuilderapi/intervals?oid=", {"reportType":"Tabular","stationIds":"FNT,KT22","groupIds":""}); print("intervals",st,b[:500])

st,b=req("/reportbuilderapi/fields?oid=", {"reportType":"Tabular","stationIds":"FNT,KT22","groupIds":"","interval":"60"})
try:
    j=json.loads(b); fl=j.get("fields") or j; print("fields keys",list(j)[:6] if isinstance(j,dict) else type(j))
    print(json.dumps(fl)[:1800])
except Exception as e: print("fields",st,b[:300])
st,b=req("/reportbuilderapi/datetypes?oid=", {"reportType":"Tabular","stationIds":"FNT","groupIds":"","interval":"60"}); print("datetypes",st,b[:400])
