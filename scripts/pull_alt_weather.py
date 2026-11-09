"""Pull the second-source weather used to fill gaps and cross-check (free, no key). Raw files go to data/raw/ (git-ignored); existing files are never re-downloaded.
 1. Open-Meteo archive, ERA5 reanalysis at the Palisades ridge point (39.18N, -120.27W): hourly 10 m gust, 10 m speed, temperature, Oct 1 - May 31, winters 2015-16 to 2025-26 -> data/raw/openmeteo/era5_<winter>.json
    (pressure-level winds came back empty and are not used). Plus snowfall, precipitation, surface pressure at the Alpine base point for 2015-16 to 2025-26 (2015-18 added 2026-11-08) -> era5snow_<winter>.json.
    MODELLED, not measured: a gridded reanalysis (about 25 km) under-reads crest gusts; used only as a flagged stand-in (docs: Data Widening Plan section 9).
 2. Iowa Environmental Mesonet ASOS, Truckee-Tahoe airport (TRK): temperature, wind, gust with the time zone STATED (America/Los_Angeles) -> data/raw/iem_asos/TRK_<winter>.csv. A valley site, used for clock checks, not as a crest-wind source.
Open-Meteo needs HTTP/1.1 from curl (its HTTP/2 connection failed here).   usage: python3 -I scripts/pull_alt_weather.py"""
import os, json, time, subprocess
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "raw")
def curl(url, http11=False): return subprocess.run(["curl", "-s", "-m", "180"] + (["--http1.1"] if http11 else []) + [url], capture_output=True, text=True).stdout
os.makedirs(f"{ROOT}/openmeteo", exist_ok=True); os.makedirs(f"{ROOT}/iem_asos", exist_ok=True)
for y in range(2015, 2026):
    W = f"{y}-{str(y + 1)[2:]}"
    jobs = [(f"{ROOT}/openmeteo/era5_{W}.json", f"https://archive-api.open-meteo.com/v1/archive?latitude=39.18&longitude=-120.27&start_date={y}-10-01&end_date={y + 1}-05-31&hourly=wind_gusts_10m,wind_speed_10m,wind_speed_700hPa,wind_speed_800hPa,temperature_2m&wind_speed_unit=mph&temperature_unit=fahrenheit&timezone=America%2FLos_Angeles&models=era5")]
    if True: jobs.append((f"{ROOT}/openmeteo/era5snow_{W}.json", f"https://archive-api.open-meteo.com/v1/archive?latitude=39.19&longitude=-120.27&start_date={y}-10-01&end_date={y + 1}-05-31&hourly=snowfall,precipitation,surface_pressure,freezing_level_height&precipitation_unit=inch&timezone=America%2FLos_Angeles&models=era5"))
    for fn, url in jobs:
        if os.path.exists(fn): continue
        j = json.loads(curl(url, True))
        if "hourly" not in j: raise SystemExit(f"{fn}: {str(j)[:200]}; nothing written")
        json.dump(j, open(fn + ".tmp", "w")); os.replace(fn + ".tmp", fn); print(fn); time.sleep(3)
    if y >= 2016:
        fn = f"{ROOT}/iem_asos/TRK_{W}.csv"
        if not os.path.exists(fn):
            t = curl(f"https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=TRK&data=tmpf&data=sknt&data=gust&year1={y}&month1=10&day1=1&year2={y + 1}&month2=6&day2=1&tz=America%2FLos_Angeles&format=onlycomma&missing=M&report_type=3&report_type=4")
            if not t.startswith("station,valid"): raise SystemExit(f"{fn}: unexpected reply; nothing written")
            open(fn + ".tmp", "w").write(t); os.replace(fn + ".tmp", fn); print(fn); time.sleep(2)
