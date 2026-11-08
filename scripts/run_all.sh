#!/bin/sh
# Rebuild everything in order and run the checks. usage: scripts/run_all.sh   (needs a Python with numpy; set PY to override)
set -e
cd "$(dirname "$0")/.."
PY="${PY:-$HOME/DataLake/.venv/bin/python}"; [ -x "$PY" ] || PY=python3
$PY -c "import numpy" 2>/dev/null || { echo "numpy missing: pip install -r requirements.txt"; exit 1; }
for y in 2018 2019 2020 2021 2022 2023 2024 2025; do for sp in train heldout; do $PY -I scripts/parse_posts.py $y $sp > /dev/null; done; done
$PY -I tests/golden.py | tail -1
$PY -I scripts/pull_nws.py > /dev/null 2>&1 || echo "note: pull_nws skipped (offline); using saved alerts"
$PY -I scripts/build_dataset.py 2018 2019 2020 2021 2022 2023 2024 2025 | tail -1
for s in recover_rules baselines infer_causes closure_conditions build_app_model; do $PY -I scripts/$s.py > /dev/null; done
$PY -I scripts/check_app_model.py | tail -1
$PY -I scripts/check_data.py | tail -3
$PY -I scripts/manifest.py
