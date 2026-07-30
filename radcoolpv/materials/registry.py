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

_DERIVED = {
    # Akerboom et al. explicitly model Si as nonabsorbing in the IR.
    "Akerboom_Si_lossless": (
        "SiliconNew.csv", tabulated.make_lossless),
}


def _tabulated_models() -> Dict[str, str]:
    """Map tabulated model name -> data path (discovered from data/)."""
    return {
        os.path.splitext(os.path.basename(p))[0]: p
        for pattern in ("*.csv", "*.yml")
        for p in glob.glob(os.path.join(_DATA_DIR, pattern))
    }


def available() -> Dict[str, str]:
    """Return {model_name: 'analytic' | csv_path} for all known models."""
    out: Dict[str, str] = {name: "analytic" for name in _ANALYTIC}
    out.update({
        name: os.path.join(_DATA_DIR, source)
        for name, (source, _) in _DERIVED.items()
    })
    out.update(_tabulated_models())
    return out


def get(model_name: str) -> Callable:
    """Return ``eps(lambda_um) -> complex`` for a model name."""
    if model_name in _ANALYTIC:
        return _ANALYTIC[model_name]
    if model_name in _DERIVED:
        source, loader = _DERIVED[model_name]
        return loader(os.path.join(_DATA_DIR, source))
    tab = _tabulated_models()
    if model_name in tab:
        path = tab[model_name]
        if path.endswith(".yml"):
            return tabulated.make_refractiveindex_info(path)
        return tabulated.make_tabulated(path)
    raise KeyError(
        f"Unknown material model {model_name!r}. "
        f"Available: {sorted(available())}"
    )
