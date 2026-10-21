#!/usr/bin/env bash
# Build webapp/dist/index.html: one self-contained page (app.py, spectra and
# wheels inlined) that opens from any host, any folder, or as a local file.
# Needs a Python with pip; the page itself needs no server-side Python.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
rm -rf dist && mkdir -p dist/pkg/data
cp app.py dist/pkg/
cp ../validation/data/C2_pv_flat_silica.txt ../validation/data/C3_pv_cylinders.txt dist/pkg/data/
"$PY" -m pip wheel --no-deps -q -w dist/pkg ..
# openpyxl (read by load_solar) is not part of the Pyodide distribution.
"$PY" -m pip download --no-deps --only-binary=:all: -q -d dist/pkg openpyxl et_xmlfile
"$PY" -m zipfile -l dist/pkg/radcoolpv-*.whl | grep -q "radcoolpv/data/astmg173.xlsx"
"$PY" - <<'EOF'
import base64, glob, json, os
os.chdir("dist/pkg")
files = {f: base64.b64encode(open(f, "rb").read()).decode()
         for f in ["app.py", *sorted(glob.glob("data/*")), *sorted(glob.glob("*.whl"))]}
html = open("../../index.html").read()
tag = '<script id="bundle" type="application/json">{}</script>'
assert html.count(tag) == 1
open("../index.html", "w").write(html.replace(tag, tag.replace("{}", json.dumps(files))))
EOF
rm -rf dist/pkg
echo "webapp/dist/index.html ready ($(du -h dist/index.html | cut -f1))"
