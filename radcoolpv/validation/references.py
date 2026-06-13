"""Literature reference data for the test / validation modes.

Loads digitised reference curves bundled in ``radcoolpv/validation/data`` so the
plots can overlay published results (e.g. Perrakis et al., 2020). A different
base directory can be passed to use custom reference data.
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np

_DEFAULT_LIT = os.path.join(os.path.dirname(__file__), "data")


def _load(name: str, base: Optional[str]) -> Optional[np.ndarray]:
    path = os.path.join(base or _DEFAULT_LIT, name)
    if not os.path.isfile(path):
        return None
    return np.loadtxt(path)


def perrakis_fig2(base: Optional[str] = None) -> Optional[np.ndarray]:
    """Cooling power vs temperature (Perrakis et al. 2020, Fig. 2)."""
    return _load("perrakis-h0.dat", base)


def green_iv(base: Optional[str] = None) -> Optional[np.ndarray]:
    """Current-voltage reference (Green, OPEX paper)."""
    return _load("currentVoltageGreenOPEXPaper.txt", base)


def perrakis_power(base: Optional[str] = None) -> Optional[np.ndarray]:
    """Power-voltage reference (Perrakis)."""
    return _load("powerVoltagePerrakis.txt", base)
