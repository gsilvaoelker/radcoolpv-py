"""One-call result reporting, for notebooks and the CLI.

Reads the ``run.json`` a completed run wrote and prints it in reading order:
what was computed, the temperatures and powers, the electrical result, then the
band averages. Quantities a run did not solve for are absent from ``run.json``,
so they are absent here too -- a cooling-curve run shows no efficiency rather
than an efficiency of zero.
"""

from __future__ import annotations

import glob
import json
import os

_UNITS = [("_W_per_m2", "W/m2"), ("_A_per_m2", "A/m2"), ("_perc_per_K", "%/K"),
          ("_K", "K"), ("_V", "V")]


def _label(key: str):
    for suffix, unit in _UNITS:
        if key.endswith(suffix):
            return key[: -len(suffix)].replace("_", " "), unit
    return key.replace("_", " "), ""


def summary(ctx, figures: bool = True) -> None:
    """Print one run's results, then display its figures inline."""
    record = json.load(open(os.path.join(ctx.results_dir, "run.json")))
    optics = record.get("optics", {})

    if optics:
        lo, hi = optics["wavelength_range_um"]
        note = ("  [silicon absorptance inferred from the supplied emittance]"
                if optics.get("silicon_from_emittance") else "")
        print(f"{lo}-{hi} um, {optics['n_lambda']} points, "
              f"{optics['angles']}{note}\n")

    for block in ("thermal_results", "band_averages_percent"):
        rows = {k: v for k, v in record.get(block, {}).items() if v is not None}
        for key, value in rows.items():
            name, unit = _label(key)
            unit = unit or ("%" if block.endswith("percent") else "")
            print(f"  {name:<42} {value:>12.4f}  {unit}")
        if rows:
            print()

    if not figures:
        return
    written = sorted(glob.glob(os.path.join(ctx.results_dir, "figures", "*.png")))
    try:
        from IPython.display import Image, display
    except ImportError:
        # Called from a plain interpreter rather than a notebook: the figures
        # are on disk either way, so say where instead of failing.
        print(f"  {len(written)} figure(s) in {ctx.results_dir}/figures")
        return
    for png in written:
        display(Image(filename=png))
