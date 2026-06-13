#!/usr/bin/env python3
"""Extract tabulated (lambda, n, k) permittivity models from the MATLAB
``permittivityDataBase/*.m`` files into CSV files.

Each MATLAB model has the form::

    function ep = Name(lambda)
    A=[ l1 n1 k1
        l2 n2 k2
        ... ];
    ...
    ep = (n + 1i*k)^2;

We pull the numeric ``A=[...]`` block (skipping ``%`` comments and any trailing
columns) and write ``lambda_um,n,k``. Analytic models (Drude/Lorentz) are NOT
handled here — port those by hand into ``radcoolpv/materials/analytic.py``.

Usage:
    python scripts/convert_permittivity.py SRC.m [SRC2.m ...] --out-dir DIR
    python scripts/convert_permittivity.py --db /path/to/permittivityDataBase \
        PalikKitamura_SiO2 SiliconNew --out-dir radcoolpv/materials/data
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import List, Optional, Tuple

NUM = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def extract_table(text: str) -> List[Tuple[float, float, float]]:
    """Return the (lambda, n, k) rows from the first ``A=[...]`` block."""
    start = text.find("A=[")
    if start < 0:
        start = text.find("A =[")
    if start < 0:
        raise ValueError("no 'A=[' table found")
    # Region from the '[' to the matching ']'.
    open_br = text.find("[", start)
    close_br = text.find("]", open_br)
    if close_br < 0:
        raise ValueError("unterminated table (no ']')")
    block = text[open_br + 1:close_br]

    rows: List[Tuple[float, float, float]] = []
    for line in block.splitlines():
        line = line.split("%", 1)[0]  # strip MATLAB comments
        nums = NUM.findall(line)
        if len(nums) < 3:
            continue
        lam, n, k = (float(nums[0]), float(nums[1]), float(nums[2]))
        rows.append((lam, n, k))
    if not rows:
        raise ValueError("table parsed but contained no numeric rows")
    return rows


def convert_file(src: str, out_dir: str) -> str:
    with open(src, "r", errors="replace") as fh:
        text = fh.read()
    rows = extract_table(text)
    name = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(out_dir, f"{name}.csv")
    os.makedirs(out_dir, exist_ok=True)
    with open(out, "w") as fh:
        fh.write("lambda_um,n,k\n")
        for lam, n, k in rows:
            fh.write(f"{lam:.10g},{n:.10g},{k:.10g}\n")
    print(f"{name}: {len(rows)} rows -> {out}")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("models", nargs="+",
                   help="Either .m file paths, or bare model names used with --db.")
    p.add_argument("--db", default=None,
                   help="permittivityDataBase directory (when passing bare names).")
    p.add_argument("--out-dir", default="radcoolpv/materials/data")
    args = p.parse_args(argv)

    ok = True
    for m in args.models:
        src = m if m.endswith(".m") else os.path.join(args.db or ".", f"{m}.m")
        try:
            convert_file(src, args.out_dir)
        except Exception as exc:  # keep going, report at end
            print(f"FAILED {m}: {exc}", file=sys.stderr)
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
