import re, urllib.request, urllib.parse
H={"User-Agent":"Mozilla/5.0"}
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=60) as r: return r.read().decode("utf-8","replace")
    except Exception as e: return ""
base="https://palisadestahoe.westernweathergroup.com"
html=get(base+"/search")
srcs=re.findall(r'src="([^"]+\.js[^"]*)"',html)+re.findall(r"src='([^']+\.js[^']*)'",html)
print("scripts:",len(srcs))
found=set(); 
for s in srcs:
    u=urllib.parse.urljoin(base+"/",s)
    if "devextreme" in u or "jquery" in u or "respond" in u or "excanvas" in u: continue
    js=get(u)
    hits=set(re.findall(r'WesternWeatherGroup\.[A-Za-z.]*DateRange[A-Za-z., ]*',js))|set(re.findall(r'"\$type"\s*:\s*"[^"]*DateRange[^"]*"',js))
    print(u[-70:], len(js), sorted(hits)[:6])
    found|=hits
# inline script blocks in the page
inline=" ".join(re.findall(r'<script[^>]*>(.*?)</script>',html,flags=re.S))
print("inline hits:", sorted(set(re.findall(r'[A-Za-z.]*DateRange[A-Za-z., ]*',inline)))[:20])
print("inline mentions of reports/export:", re.findall(r'/reports/[A-Za-z/]+',inline)[:10])
print("inline mentions of 'Custom':", sorted(set(re.findall(r'.{40}Custom.{60}',inline)))[:6])
