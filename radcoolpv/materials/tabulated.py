"""Generic tabulated (lambda, n, k) permittivity loader.

Reproduces the MATLAB pattern shared by every tabulated model file: linearly
interpolate the refractive index ``n`` and extinction coefficient ``k`` versus
wavelength, then return the complex permittivity ``(n + i k)**2``. MATLAB used
``interp1qr`` (linear); ``numpy.interp`` is the equivalent.
"""

from __future__ import annotations

from io import StringIO
from typing import Callable, Dict, Tuple

import numpy as np
import yaml

_CACHE: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}


def load_table(csv_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load and cache a ``lambda_um,n,k`` CSV as ascending arrays."""
    if csv_path not in _CACHE:
        data = np.loadtxt(csv_path, delimiter=",", skiprows=1)
        lam, n, k = data[:, 0], data[:, 1], data[:, 2]
        order = np.argsort(lam)
        _CACHE[csv_path] = (lam[order], n[order], k[order])
    return _CACHE[csv_path]


def make_tabulated(csv_path: str) -> Callable[[np.ndarray], np.ndarray]:
    """Return ``eps(lambda_um) -> complex`` for a tabulated model CSV."""
    lam_t, n_t, k_t = load_table(csv_path)

    def eps(lambda_um) -> np.ndarray:
        lam = np.asarray(lambda_um, dtype=float)
        if np.any(lam < lam_t[0]) or np.any(lam > lam_t[-1]):
            raise ValueError(
                f"{csv_path}: requested wavelength outside tabulated range "
                f"{lam_t[0]:g}-{lam_t[-1]:g} um.")
        n = np.interp(lam, lam_t, n_t)
        k = np.interp(lam, lam_t, k_t)
        return (n + 1j * k) ** 2

    return eps


def make_lossless(csv_path: str) -> Callable[[np.ndarray], np.ndarray]:
    """Use a tabulated refractive index while setting its extinction to zero."""
    lam_t, n_t, _ = load_table(csv_path)

    def eps(lambda_um) -> np.ndarray:
        lam = np.asarray(lambda_um, dtype=float)
        if np.any(lam < lam_t[0]) or np.any(lam > lam_t[-1]):
            raise ValueError(
                f"{csv_path}: requested wavelength outside tabulated range "
                f"{lam_t[0]:g}-{lam_t[-1]:g} um.")
        return np.interp(lam, lam_t, n_t) ** 2

    return eps


def make_refractiveindex_info(yaml_path: str) -> Callable[[np.ndarray], np.ndarray]:
    """Load an unmodified refractiveindex.info ``tabulated nk`` YAML record."""
    with open(yaml_path, "r") as fh:
        record = yaml.safe_load(fh)
    tables = [
        item for item in record.get("DATA", [])
        if item.get("type") == "tabulated nk"
    ]
    if len(tables) != 1:
        raise ValueError(
            f"{yaml_path}: expected exactly one tabulated nk dataset.")
    data = np.loadtxt(StringIO(tables[0]["data"]))
    lam_t, n_t, k_t = data[:, 0], data[:, 1], data[:, 2]

    def eps(lambda_um) -> np.ndarray:
        lam = np.asarray(lambda_um, dtype=float)
        if np.any(lam < lam_t[0]) or np.any(lam > lam_t[-1]):
            raise ValueError(
                f"{yaml_path}: requested wavelength outside tabulated range "
                f"{lam_t[0]:g}-{lam_t[-1]:g} um.")
        n = np.interp(lam, lam_t, n_t)
        k = np.interp(lam, lam_t, k_t)
        return (n + 1j * k) ** 2

    return eps
