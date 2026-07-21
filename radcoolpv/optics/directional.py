"""Reduce per-angle S4 results to spectral optical properties.

Ports ``normalPropsFunc.m`` and ``hemisphPropsFunc.m``. The raw input is the
reflectance/transmittance/absorptance/silicon-absorptance for each
(wavelength, angle, polarisation), exactly as written to ``OUTPUTS4-TE.txt`` /
``OUTPUTS4-TM.txt``. It can come from a live S4 sweep (in memory) or from those
files (resume / parity testing).

Output is an :class:`~radcoolpv.io.results.OpticsResult`: the hemispherical (or
normal) spectral properties plus the normal-incidence copies the thermal stage
needs for the luminescence term, and the atmospheric emissivity.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..io.results import OpticsResult
from ..thermal.spectra import load_atmosphere


@dataclass
class RawOptics:
    """Per-(wavelength, angle) optical fluxes, TE always present, TM optional.

    Each field below is shape ``(n_lambda, n_theta)``.
    """

    theta_deg: np.ndarray   # (n_theta,)
    lambda_um: np.ndarray   # (n_lambda,)
    ref_te: np.ndarray
    tran_te: np.ndarray
    abs_te: np.ndarray
    abs_si_te: np.ndarray
    ref_tm: Optional[np.ndarray] = None
    tran_tm: Optional[np.ndarray] = None
    abs_tm: Optional[np.ndarray] = None
    abs_si_tm: Optional[np.ndarray] = None

    @property
    def n_theta(self) -> int:
        return len(self.theta_deg)

    @property
    def n_lambda(self) -> int:
        return len(self.lambda_um)


def _read_output_file(path: str, n_lambda: int) -> np.ndarray:
    """Read an OUTPUTS4 file as (n_theta, n_lambda, 6)."""
    data = np.loadtxt(path)
    if data.ndim == 1:
        data = data[None, :]
    n_rows = data.shape[0]
    if n_rows % n_lambda != 0:
        raise ValueError(
            f"{os.path.basename(path)} has {n_rows} rows, not a multiple of "
            f"n_lambda={n_lambda}."
        )
    n_theta = n_rows // n_lambda
    return data.reshape(n_theta, n_lambda, 6)


def from_folder(path: str, n_lambda: int) -> RawOptics:
    """Load ``OUTPUTS4-TE.txt`` (+ ``-TM.txt`` if present) from a results folder.

    Columns: ``theta_deg, lambda_um, R, T, A, A_silicon``; rows are ordered
    theta-major (all wavelengths for theta 0, then theta 1, ...).
    """
    te = _read_output_file(os.path.join(path, "OUTPUTS4-TE.txt"), n_lambda)
    theta_deg = te[:, 0, 0]
    lambda_um = te[0, :, 1]
    raw = RawOptics(
        theta_deg=theta_deg, lambda_um=lambda_um,
        ref_te=te[:, :, 2].T, tran_te=te[:, :, 3].T,
        abs_te=te[:, :, 4].T, abs_si_te=te[:, :, 5].T,
    )
    tm_path = os.path.join(path, "OUTPUTS4-TM.txt")
    if os.path.isfile(tm_path) and os.path.getsize(tm_path) > 0:
        tm = _read_output_file(tm_path, n_lambda)
        raw.ref_tm = tm[:, :, 2].T
        raw.tran_tm = tm[:, :, 3].T
        raw.abs_tm = tm[:, :, 4].T
        raw.abs_si_tm = tm[:, :, 5].T
    return raw


def from_reduced_file(path: str, atmosphere_path: str) -> OpticsResult:
    """Load a previously hemispherically reduced optical-property spectrum.

    Accepted columns are either the five-column ``HEMSIPH`` form
    ``lambda, R, T, emit, abs_si`` or the seven-column ``PVcode`` form
    ``lambda, emit, emit_normal, R, R_normal, abs_si, abs_si_normal``.
    These files retain no directional information, so their atmospheric term
    uses the same angle-independent approximation as free-form optics.
    """
    data = np.loadtxt(path)
    if data.ndim == 1:
        data = data[None, :]
    lam = data[:, 0]
    if data.shape[1] == 5:
        ref, tran, emit, abs_si = data[:, 1], data[:, 2], data[:, 3], data[:, 4]
        ref_norm = emit_norm = abs_si_norm = None
    elif data.shape[1] == 7:
        emit, emit_norm, ref, ref_norm, abs_si, abs_si_norm = data[:, 1:].T
        tran = 1.0 - ref - emit
    else:
        raise ValueError(
            f"{path}: expected 5-column HEMSIPH or 7-column PVcode reduced optics, "
            f"got {data.shape[1]} columns."
        )

    atm = load_atmosphere(atmosphere_path, lam)
    emit_atm = 1.0 - atm
    return OpticsResult(
        lambda_um=lam, ref=ref, tran=tran, emit=emit, abs_silicon=abs_si,
        emit_atm=emit_atm, emitt_spec_times_emit_atm=emit_atm * emit,
        ref_norm=ref_norm, emit_norm=emit_norm, abs_silicon_norm=abs_si_norm,
        angles="hemispherical",
    )


def reduce(raw: RawOptics, atmosphere_path: str,
           lambda_grid: Optional[np.ndarray] = None) -> OpticsResult:
    """Reduce raw per-angle data to spectral properties (normal or hemispherical).

    ``lambda_grid`` is the canonical simulation wavelength grid
    (``linspace(min, max, n)``). MATLAB uses this exact grid for the atmospheric
    interpolation and the band averages, while the per-angle values come from
    the (slightly round-tripped) S4 output; passing it here reproduces that.
    If omitted, the raw file wavelengths are used.
    """
    lam = raw.lambda_um if lambda_grid is None else np.asarray(lambda_grid, dtype=float)
    theta_deg = raw.theta_deg
    n_theta = raw.n_theta
    atm = load_atmosphere(atmosphere_path, lam)   # atmospheric transmittance

    is_normal = (n_theta == 1) and np.isclose(theta_deg[0], 0.0)

    if is_normal:
        ref = raw.ref_te[:, 0]
        tran = raw.tran_te[:, 0]
        emit = raw.abs_te[:, 0]
        abs_si = raw.abs_si_te[:, 0]
        emit_atm = 1.0 - atm                       # no cosine for normal emissivity
        product = emit_atm * emit
        return OpticsResult(
            lambda_um=lam, ref=ref, tran=tran, emit=emit, abs_silicon=abs_si,
            emit_atm=emit_atm, emitt_spec_times_emit_atm=product, angles="normal",
        )

    # ----- hemispherical integration --------------------------------------- #
    if raw.ref_tm is None:
        raise ValueError("Hemispherical reduction requires TM data (OUTPUTS4-TM.txt).")
    theta_rad = np.deg2rad(theta_deg)
    dtheta = theta_rad[1] - theta_rad[0]
    cos_t = np.cos(theta_rad)
    cs = cos_t * np.sin(theta_rad)                  # (n_theta,) integration weight

    def hemi(te, tm):
        # sum_theta cos*sin*(te+tm) * dtheta  -> (n_lambda,)
        return np.sum(cs[None, :] * (te + tm), axis=1) * dtheta

    ref = hemi(raw.ref_te, raw.ref_tm)
    tran = hemi(raw.tran_te, raw.tran_tm)
    emit = hemi(raw.abs_te, raw.abs_tm)
    abs_si = hemi(raw.abs_si_te, raw.abs_si_tm)

    # Atmospheric emissivity per angle: 1 - tau^(1/cos theta). (n_lambda, n_theta)
    emit_atm_2d = 1.0 - atm[:, None] ** (1.0 / cos_t[None, :])
    emit_atm = np.sum(emit_atm_2d, axis=1) * dtheta          # unweighted (matches MATLAB)
    emis_per_theta = cs[None, :] * (raw.abs_te + raw.abs_tm)  # weighted emissivity per angle
    product = np.sum(emit_atm_2d * emis_per_theta, axis=1) * dtheta

    # Normal-incidence copies (the theta == 0 TE column).
    ref_norm = raw.ref_te[:, 0]
    emit_norm = raw.abs_te[:, 0]
    abs_si_norm = raw.abs_si_te[:, 0]

    return OpticsResult(
        lambda_um=lam, ref=ref, tran=tran, emit=emit, abs_silicon=abs_si,
        emit_atm=emit_atm, emitt_spec_times_emit_atm=product,
        ref_norm=ref_norm, emit_norm=emit_norm, abs_silicon_norm=abs_si_norm,
        angles="hemispherical",
    )
