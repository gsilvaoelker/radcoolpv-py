"""Spectral band averages.

* :func:`band_average` — a plain mean of one spectrum over one wavelength band.
* :func:`optical_band_averages` — the simple trapezoidal band averages printed
  to ``simulParam.log`` by ``mainOpticalMatlabS4_v11.m``.
* :func:`pv_band_averages` — the solar- and blackbody-weighted averages from
  ``averagePropsFunc.m`` used by the energy-balance log.

The latter two reproduce the MATLAB ``find(...)`` band-edge selection (first
matching index within a tolerance) so the numbers match; :func:`band_average`
selects by value instead and is the general-purpose helper.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .._compat import trapz
from ..constants import CLIGHT, HPLANCK, KBOLTZ, MICRON, MTOMICRON


def _find_first(lam: np.ndarray, center: float, tol: float) -> Optional[int]:
    """0-based index of the first wavelength within ``center +/- tol``, or None."""
    hits = np.where((lam > center - tol) & (lam < center + tol))[0]
    return int(hits[0]) if hits.size else None


def band_average(lam: np.ndarray, values: np.ndarray,
                 lo: float, hi: float) -> float:
    """Trapezoidal mean of ``values`` over the ``[lo, hi]`` micrometre band.

    Selects the band by wavelength value, not by the MATLAB ``find()`` index
    convention used by the two functions below, so it is safe on any grid. Used
    for window averages such as the 8-13 um atmospheric window.
    """
    m = (lam >= lo) & (lam <= hi)
    return float(trapz(values[m], lam[m]) / (hi - lo))


@dataclass
class OpticalAverages:
    solar_abs: float       # silicon absorption 0.3 -> lambda_g (%)
    subgap_ref: float      # reflectance lambda_g -> 4 um (%)
    emit_window1: float    # emittance 8 -> 13 um (%)
    emit_window2: float    # emittance 17 -> 24 um (%)
    emit_broad: float      # emittance 4 -> 30 um (%)


def optical_band_averages(lam: np.ndarray, ref: np.ndarray, emiss: np.ndarray,
                          abs_silicon: np.ndarray) -> OpticalAverages:
    """Simple trapezoidal band averages (port of the inline block in the
    optical main script). Bands that fall outside the wavelength range return 0.
    """
    eps = 1e-2
    lambda_gap = 1.12
    gp = _find_first(lam, lambda_gap, 1.2 * eps)
    esp = _find_first(lam, 4.0, 1.5 * eps)
    w1 = _find_first(lam, 8.0, 1.49 * eps)
    w2 = _find_first(lam, 13.0, 1.49 * eps)
    w3 = _find_first(lam, 17.0, 1.49 * eps)
    w4 = _find_first(lam, 24.0, 1.49 * eps)

    def band(x_idx, y_idx, lo, hi, data):
        if x_idx is None or y_idx is None:
            return 0.0
        sl = slice(x_idx, y_idx + 1)
        return 100.0 * trapz(data[sl], lam[sl]) / (hi - lo)

    solar_abs = band(0, gp, 0.3, lambda_gap, abs_silicon) if gp is not None else 0.0
    subgap_ref = band(gp, esp, lambda_gap, 4.0, ref) if (gp is not None and esp is not None) else 0.0
    emit_w1 = band(w1, w2, 8.0, 13.0, emiss)
    emit_w2 = band(w3, w4, 17.0, 24.0, emiss)
    emit_broad = (100.0 * trapz(emiss[esp:], lam[esp:]) / (30.0 - 4.0)
                  if esp is not None else 0.0)

    return OpticalAverages(solar_abs, subgap_ref, emit_w1, emit_w2, emit_broad)


@dataclass
class PVAverages:
    solar_abs: float       # solar-weighted silicon absorption 0.3 -> lambda_g (%)
    subgap_ref: float      # solar-weighted reflectance lambda_g -> 4 um (%)
    emit_window1: float    # blackbody-weighted emittance 8 -> 13 um (%)
    emit_window2: float    # (kept 0, as in averagePropsFunc.m)
    emit_broad: float      # blackbody-weighted emittance 4 -> 30 um (%)
    solar_ref: float       # solar-weighted reflectance 0.3 -> lambda_g (%)


def pv_band_averages(lam: np.ndarray, abs_silicon: np.ndarray, ref: np.ndarray,
                     emiss: np.ndarray, solar_per_um: np.ndarray,
                     emit_temp: float) -> PVAverages:
    """Solar- and blackbody-weighted band averages (port of averagePropsFunc.m)."""
    eps = 1e-2
    lambda_gap = 1.12
    gp = _find_first(lam, lambda_gap, 1.2 * eps)
    esp = _find_first(lam, 4.0, 1.5 * eps)
    w1 = _find_first(lam, 8.0, 1.49 * eps)
    w2 = _find_first(lam, 13.0, 1.49 * eps)

    def wavg(num, den, sl):
        d = trapz(den[sl], lam[sl])
        return 100.0 * trapz(num[sl], lam[sl]) / d if d != 0 else 0.0

    sl_solar = slice(0, (gp + 1) if gp is not None else 0)
    solar_abs = wavg(abs_silicon * solar_per_um, solar_per_um, sl_solar)
    solar_ref = wavg(ref * solar_per_um, solar_per_um, sl_solar)

    if gp is not None and esp is not None:
        sl_sub = slice(gp, esp + 1)
        subgap_ref = wavg(ref * solar_per_um, solar_per_um, sl_sub)
    else:
        subgap_ref = 0.0

    # Blackbody spectral irradiance at the emitter temperature (J/s / um^3).
    irrad = _blackbody_irradiance(lam, emit_temp)
    emit_w1 = (wavg(emiss * irrad, irrad, slice(w1, w2 + 1))
               if (w1 is not None and w2 is not None) else 0.0)
    emit_broad = (wavg(emiss * irrad, irrad, slice(esp, len(lam)))
                  if esp is not None else 0.0)

    return PVAverages(solar_abs, subgap_ref, emit_w1, 0.0, emit_broad, solar_ref)


def _blackbody_irradiance(lam: np.ndarray, temp: float) -> np.ndarray:
    """Spectral irradiance of a blackbody at ``temp`` (matches averagePropsFunc.m)."""
    photon_flux = (2 * np.pi * CLIGHT * MTOMICRON / lam ** 4) / (
        np.exp(HPLANCK * CLIGHT / (lam * MICRON * KBOLTZ * temp)) - 1.0)
    return photon_flux * HPLANCK * CLIGHT * MTOMICRON / (lam * np.pi)
