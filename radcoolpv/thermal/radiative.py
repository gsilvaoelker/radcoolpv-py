"""Planck-weighted radiated power.

Port of ``RadTermFunc.m``. Returns the spectral-emissivity-weighted radiance
integrated over wavelength (W/m^2/sr). The energy balance multiplies the result
by ``pi`` to integrate the cosine-weighted solid angle over the hemisphere, so
``pi * rad_power(lam, ones, T)`` over a broad band equals ``sigma * T**4``.
"""

from __future__ import annotations

import numpy as np

from .._compat import trapz
from ..constants import CLIGHT, HPLANCK, KBOLTZ


def rad_power(lambda_um: np.ndarray, emit: np.ndarray, temperature: float) -> float:
    """Integral of ``emit(lambda) * B_lambda(T)`` over wavelength (um grid)."""
    lam = np.asarray(lambda_um, dtype=float)
    emit = np.asarray(emit, dtype=float)
    # Planck spectral radiance per micrometre (factor 1e24 folds the um->m units).
    planck = (2.0 * HPLANCK * CLIGHT ** 2 * 1e24 / lam ** 5) / (
        np.exp(HPLANCK * CLIGHT / (lam * KBOLTZ * temperature * 1e-6)) - 1.0)
    return float(trapz(emit * planck, lam))
