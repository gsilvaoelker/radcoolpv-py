"""Analytic permittivity models (oscillator / Drude-Lorentz forms).

Ported directly from the corresponding ``permittivityDataBase/*.m`` files.
Each function takes wavelength in micrometres (scalar or array) and returns the
complex permittivity. Add further analytic models here and register them in
``registry.py``.
"""

from __future__ import annotations

import numpy as np

_TWO_PI = 2.0 * np.pi
_C0 = 2.99792458e8  # m/s


def vacuum(lambda_um) -> np.ndarray:
    """Vacuum: eps = 1 (epsilon=1, k=0)."""
    return np.ones_like(np.asarray(lambda_um, dtype=float), dtype=complex)


def drude_si3n4(lambda_um) -> np.ndarray:
    """Low-stress silicon nitride, multi-oscillator model.

    Port of ``permittivityDataBase/DrudeSi3N4.m``
    (Cataldo et al., Opt. Lett. 37(20), 2012).
    """
    lam = np.asarray(lambda_um, dtype=float)
    w = _TWO_PI * _C0 / (lam * 1e-6)

    # Oscillator parameters (index 0..4 are the five oscillators; index 5 is the
    # high-frequency tail used by Delta_eps of the last oscillator and eps_inf).
    alpha = np.array([0.0001, 0.3427, 0.0006, 0.0002, 0.0080])
    Gamma = np.array([5.810, 6.436, 2.751, 3.482, 5.948]) * _TWO_PI * 1e12
    omega = np.array([13.913, 15.053, 24.521, 26.440, 31.724]) * _TWO_PI * 1e12
    eps_pj = np.array([7.582, 6.754, 6.601, 5.430, 4.601, 4.562])
    eps_ppj = np.array([0.0, 0.3759, 0.0041, 0.1179, 0.2073, 0.0124])

    eps_inf = eps_pj[5] + 1j * eps_ppj[5]

    total = np.zeros_like(w, dtype=complex)
    for j in range(5):
        delta_eps = (eps_pj[j] + 1j * eps_ppj[j]) - (eps_pj[j + 1] + 1j * eps_ppj[j + 1])
        gamma_p = Gamma[j] * np.exp(-alpha[j] * (omega[j] ** 2 - w ** 2) / (w * Gamma[j]) ** 2)
        total = total + delta_eps * omega[j] ** 2 / ((omega[j] ** 2 - w ** 2) - 1j * w * gamma_p)

    return total + eps_inf
