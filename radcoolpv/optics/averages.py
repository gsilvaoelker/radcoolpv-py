"""Spectral band averages.

* :func:`band_average` — plain trapezoidal mean of one spectrum over one band.
* :func:`pv_band_averages` — the solar- and blackbody-weighted averages from
  ``averagePropsFunc.m`` used by the energy-balance log.

Both integrate exactly the band asked for, interpolating the two endpoints onto
the wavelength grid. A band average therefore never depends on whether a grid
point happens to land on an edge, which is what lets the wavelength range be
chosen freely. A band the grid does not cover returns ``None`` rather than a
zero that would be reported as though it were a result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .._compat import trapz
from ..constants import CLIGHT, HPLANCK, KBOLTZ, MICRON, MTOMICRON

#: Band limits in micrometres. ``LAMBDA_GAP`` is the nominal silicon band-gap
#: wavelength used to split the solar bands from the sub-gap ones.
SOLAR_MIN = 0.3
LAMBDA_GAP = 1.12
IR_MIN = 4.0
WINDOW = (8.0, 13.0)


def _band_grid(lam: np.ndarray, lo: float, hi: float) -> Optional[np.ndarray]:
    """Wavelengths spanning exactly ``[lo, hi]``, or None if the grid misses it."""
    if hi <= lo or lam[0] > lo or lam[-1] < hi:
        return None
    return np.concatenate(([lo], lam[(lam > lo) & (lam < hi)], [hi]))


def band_average(lam: np.ndarray, values: np.ndarray,
                 lo: float, hi: float) -> Optional[float]:
    """Trapezoidal mean of ``values`` over the exact ``[lo, hi]`` band (um).

    Returns None when the grid does not span the band.
    """
    x = _band_grid(lam, lo, hi)
    if x is None:
        return None
    return float(trapz(np.interp(x, lam, values), x) / (hi - lo))


@dataclass
class PVAverages:
    solar_abs: Optional[float]     # solar-weighted Si absorption, 0.3 -> gap (%)
    subgap_ref: Optional[float]    # solar-weighted reflectance, gap -> 4 um (%)
    emit_window1: Optional[float]  # blackbody-weighted emittance, 8 -> 13 um (%)
    emit_broad: Optional[float]    # blackbody-weighted emittance, broad band (%)
    solar_ref: Optional[float]     # solar-weighted reflectance, 0.3 -> gap (%)


def pv_band_averages(lam: np.ndarray, abs_silicon: np.ndarray, ref: np.ndarray,
                     emiss: np.ndarray, solar_per_um: np.ndarray,
                     emit_temp: float) -> PVAverages:
    """Solar- and blackbody-weighted band averages (port of averagePropsFunc.m)."""

    def wavg(num, den, lo, hi):
        x = _band_grid(lam, lo, hi)
        if x is None:
            return None
        weight = trapz(np.interp(x, lam, den), x)
        if weight == 0:
            return None
        return 100.0 * trapz(np.interp(x, lam, num), x) / weight

    solar_lo = max(lam[0], SOLAR_MIN)
    solar_abs = wavg(abs_silicon * solar_per_um, solar_per_um, solar_lo, LAMBDA_GAP)
    solar_ref = wavg(ref * solar_per_um, solar_per_um, solar_lo, LAMBDA_GAP)
    subgap_ref = wavg(ref * solar_per_um, solar_per_um, LAMBDA_GAP, IR_MIN)

    # Blackbody spectral irradiance at the emitter temperature (J/s / um^3).
    irrad = _blackbody_irradiance(lam, emit_temp)
    emit_w1 = wavg(emiss * irrad, irrad, *WINDOW)
    # Broadband emittance runs from the infrared edge to the end of the grid,
    # which run.json records as optics.wavelength_range_um.
    emit_broad = wavg(emiss * irrad, irrad, IR_MIN, float(lam[-1]))

    return PVAverages(solar_abs, subgap_ref, emit_w1, emit_broad, solar_ref)


def _blackbody_irradiance(lam: np.ndarray, temp: float) -> np.ndarray:
    """Spectral irradiance of a blackbody at ``temp`` (matches averagePropsFunc.m)."""
    photon_flux = (2 * np.pi * CLIGHT * MTOMICRON / lam ** 4) / (
        np.exp(HPLANCK * CLIGHT / (lam * MICRON * KBOLTZ * temp)) - 1.0)
    return photon_flux * HPLANCK * CLIGHT * MTOMICRON / (lam * np.pi)
