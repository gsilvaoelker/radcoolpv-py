#!/usr/bin/env bash
# Assemble webapp/dist/, the folder to upload to public_html/radcoolpv/.
# Needs a Python with pip; the page itself needs no server-side Python.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
rm -rf dist && mkdir -p dist/data
cp index.html app.py dist/
cp ../validation/data/C2_pv_flat_silica.txt ../validation/data/C3_pv_cylinders.txt dist/data/
"$PY" -m pip wheel --no-deps -q -w dist ..
# openpyxl (read by load_solar) is not part of the Pyodide distribution.
"$PY" -m pip download --no-deps --only-binary=:all: -q -d dist openpyxl et_xmlfile
"$PY" -m zipfile -l dist/radcoolpv-*.whl | grep -q "radcoolpv/data/astmg173.xlsx"
cd dist
"$PY" -c "import glob, json; json.dump({'wheels': sorted(glob.glob('*.whl')), 'data': sorted(glob.glob('data/*'))}, open('files.json', 'w'))"
echo "webapp/dist ready:" && ls
