"""Pull NWS Reno (WFO REV) text products from the Iowa Environmental Mesonet AFOS archive (free, no key): the Area Forecast Discussion (AFDREV, 4+ a day) and Public Information Statements (PNSREV: snowfall and peak-gust reports, some for Palisades and Alpine).
Raw to data/raw/nws_text/<PIL>_<winter>.txt, Oct 1 to May 31, winters 2015-16 to 2025-26. Existing files are not re-downloaded; nothing is written on an error.  usage: python3 -I scripts/pull_nws_text.py"""
import os, subprocess
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw", "nws_text"); os.makedirs(OUT, exist_ok=True)
for pil in ("AFDREV", "PNSREV"):
    for y in range(2015, 2026):
        fn = f"{OUT}/{pil}_{y}-{str(y + 1)[2:]}.txt"
        if os.path.exists(fn): continue
        t = subprocess.run(["curl", "-s", "-m", "300", f"https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?pil={pil}&sdate={y}-10-01&edate={y + 1}-06-01&limit=9999&fmt=text"], capture_output=True, text=True).stdout
        if "KREV" not in t: raise SystemExit(f"{fn}: no products returned ({t[:120]!r}); nothing written")
        open(fn + ".tmp", "w").write(t); os.replace(fn + ".tmp", fn); print(fn, len(t))
