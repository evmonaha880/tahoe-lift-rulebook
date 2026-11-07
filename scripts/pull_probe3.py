import json, os, re, base64, urllib.request, urllib.parse, urllib.error
def get(url, headers=None, timeout=60):
    req = urllib.request.Request(url, headers=headers or {"User-Agent":"Mozilla/5.0 tahoe-lift-rulebook/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
    except Exception as e: return f"ERR {e}", b""
# A. WWG: decode the export link structure
data="eyJTdGF0aW9ucyI6WyJTSUIiLCJCTVQiLCJGTlQiLCJLVDIyIiwiT1ZCIl0sIkdyb3VwcyI6W10sIkZpZWxkcyI6WyJUZW1wIiwiV2luZENoaWxsIiwiUkgiLCJXZXRCdWxiVGVtcCIsIkRld1BvaW50IiwiV2luZERpciIsIldpbmRTcGVlZCIsIldpbmRNYXgiLCJUZW1wTWluRGF5IiwiVGVtcE1heERheSIsIldpbmRNYXhEYXkiLCJZZXN0VGVtcE1pbiIsIlllc3RUZW1wTWF4IiwiWWVzdFdpbmRNYXgiXSwiRGVsdGFzIjpbIlRlbXAiLCJXaW5kQ2hpbGwiLCJSSCIsIldldEJ1bGJUZW1wIiwiRGV3UG9pbnQiLCJXaW5kU3BlZWQiLCJXaW5kTWF4IiwiVGVtcE1pbkRheSIsIlRlbXBNYXhEYXkiLCJXaW5kTWF4RGF5Il0sIkludGVydmFsIjoxNSwiVHlwZSI6IlRhYnVsYXIiLCJEYXRlUmFuZ2UiOnsiJHR5cGUiOiJXZXN0ZXJuV2VhdGhlckdyb3VwLkxhdGVzdE9ic2VydmF0aW9uUmVwb3J0RGF0ZVJhbmdlLCBXZXN0ZXJuV2VhdGhlckdyb3VwLkNvcmUifSwiRGF0ZURlc2NyaXB0aW9uIjoiTGF0ZXN0IE9ic2VydmF0aW9uIiwiVGl0bGUiOiJMYXRlc3QgKE9WKSBPYnNlcnZhdGlvbnMiLCJTdWJ0aXRsZSI6Ik9seW1waWMgVmFsbGV5In0="
print("== WWG export spec:", json.dumps(json.loads(base64.b64decode(data)))[:700])
st, body = get("https://palisadestahoe.westernweathergroup.com/search")
html = body.decode("utf-8","replace"); print("search page http",st,"bytes",len(html))
for pat in [r"[A-Za-z.]*DateRange[A-Za-z.,]*", r"/reports/[a-z/]+", r"Start[A-Za-z]*", r"2016|2017"]:
    print(pat, sorted(set(re.findall(pat, html)))[:12])
scripts = re.findall(r'src="([^"]+\.js[^"]*)"', html); print("scripts", scripts[:6])
# B. Does the Synoptic token work for ANY station history (Heavenly)?
tok = open(os.path.expanduser("~/.config/synoptic/token")).read().strip()
q = urllib.parse.urlencode({"token":tok,"stid":"HVRSK","start":"202501150000","end":"202501160000","vars":"wind_speed,wind_gust","units":"english"})
st, body = get("https://api.synopticdata.com/v2/stations/timeseries?"+q); j=json.loads(body); print("== Synoptic HVRSK 2025-01:", j["SUMMARY"].get("RESPONSE_CODE"), j["SUMMARY"].get("RESPONSE_MESSAGE","")[:90], "obs", len((j.get("STATION") or [{}])[0].get("OBSERVATIONS",{}).get("date_time",[])))
# C. X counts: the two most recent winters, full Oct-May windows
bearer = open(os.path.expanduser("~/.config/x-api/bearer")).read().strip(); h={"Authorization":"Bearer "+bearer,"User-Agent":"tahoe-lift-rulebook/0.1"}
for y in (2024,2025):
    q=urllib.parse.urlencode({"query":"from:palisadesops","granularity":"day","start_time":f"{y}-10-01T00:00:00Z","end_time":f"{y+1}-06-01T00:00:00Z"})
    tot=0; pages=0; nxt=None
    while pages<14:
        st, body = get("https://api.x.com/2/tweets/counts/all?"+q+(("&next_token="+nxt) if nxt else ""), h)
        if st!=200: print(y,"http",st,body[:100]); break
        j=json.loads(body); pages+=1; tot+=sum(d["tweet_count"] for d in j.get("data",[])); nxt=(j.get("meta") or {}).get("next_token")
        if not nxt: break
    print(f"== winter {y}-{str(y+1)[2:]}: {tot} posts (pages {pages}) ~${tot*0.005:.2f}")
