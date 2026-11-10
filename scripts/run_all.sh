#!/bin/bash
# Rebuild everything in order and run the checks. usage: scripts/run_all.sh   (needs a Python with numpy; set PY to override)
set -eo pipefail   # pipefail: a failing check piped into tail must still stop the build
cd "$(dirname "$0")/.."
PY="${PY:-$HOME/DataLake/.venv/bin/python}"; [ -x "$PY" ] || PY=python3
$PY -c "import numpy" 2>/dev/null || { echo "numpy missing: pip install -r requirements.txt"; exit 1; }
for y in 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025; do for sp in train heldout; do $PY -I scripts/parse_posts.py $y $sp > /dev/null; done; done
$PY -I tests/golden.py | tail -1
$PY -I tests/timestamps.py --check | tail -1
$PY -I scripts/pull_nws.py > /dev/null 2>&1 || echo "note: pull_nws skipped (offline); using saved alerts"
$PY -I scripts/weather_qc.py | tail -1
$PY -I scripts/build_weather_common.py > /dev/null      # before build_dataset: the 2015-18 rows take their early gust from this table
$PY -I scripts/build_dataset.py 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025 | tail -1
for s in recover_rules baselines infer_causes closure_conditions build_app_model; do $PY -I scripts/$s.py > /dev/null; done
$PY -I scripts/check_app_model.py | tail -1
$PY -I scripts/check_data.py | tail -3
$PY -I scripts/check_numbers.py | tail -3
if [ -d data/raw/blog ]; then $PY -I scripts/build_blog_index.py | tail -1; $PY -I scripts/blog_forecast.py | tail -1; fi    # commentary index and forecast numbers from the saved blog; skipped on a clone without it
$PY -I scripts/build_first_run.py > /dev/null
$PY -I scripts/build_winters.py > /dev/null
$PY -I scripts/check_architecture.py      # no pipe: a failure here stops the build
$PY -I scripts/manifest.py
