"""Material model registry: model name -> callable ``eps(lambda_um) -> complex``.

Tabulated models are auto-discovered from the CSVs in ``materials/data`` (their
filename is the model name). Analytic models are registered explicitly. Adding a
new material is a one-liner: drop a CSV in ``data/`` or add an entry below.
"""

from __future__ import annotations

import glob
import os
from typing import Callable, Dict

from . import analytic, tabulated

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Analytic (formula-based) models.
_ANALYTIC: Dict[str, Callable] = {
    "Vacuum": analytic.vacuum,
    "DrudeSi3N4": analytic.drude_si3n4,
}


def _tabulated_models() -> Dict[str, str]:
    """Map tabulated model name -> CSV path (discovered from data/)."""
    return {
        os.path.splitext(os.path.basename(p))[0]: p
        for p in glob.glob(os.path.join(_DATA_DIR, "*.csv"))
    }


def available() -> Dict[str, str]:
    """Return {model_name: 'analytic' | csv_path} for all known models."""
    out: Dict[str, str] = {name: "analytic" for name in _ANALYTIC}
    out.update(_tabulated_models())
    return out


def get(model_name: str) -> Callable:
    """Return ``eps(lambda_um) -> complex`` for a model name."""
    if model_name in _ANALYTIC:
        return _ANALYTIC[model_name]
    tab = _tabulated_models()
    if model_name in tab:
        return tabulated.make_tabulated(tab[model_name])
    raise KeyError(
        f"Unknown material model {model_name!r}. "
        f"Available: {sorted(available())}"
    )
