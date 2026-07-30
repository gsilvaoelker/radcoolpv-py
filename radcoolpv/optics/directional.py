"""Reduce directional S4 results to spectral optical properties.

Ports ``normalPropsFunc.m`` and ``hemisphPropsFunc.m``. The raw input is the
reflectance/transmittance/absorptance/silicon-absorptance for each wavelength,
direction, and polarization. It can come from a live S4 sweep or a historical
MATLAB/S4 folder used for parity testing.

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
    """Per-(wavelength, direction) optical fluxes.

    Each optical field is shape ``(n_lambda, n_direction)``. A field is
    ``None`` when that polarization was not requested.
    """

    theta_deg: np.ndarray
    phi_deg: np.ndarray
    direction_weight: np.ndarray
    lambda_um: np.ndarray
    ref_te: Optional[np.ndarray] = None
    tran_te: Optional[np.ndarray] = None
    abs_te: Optional[np.ndarray] = None
    abs_si_te: Optional[np.ndarray] = None
    ref_tm: Optional[np.ndarray] = None
    tran_tm: Optional[np.ndarray] = None
    abs_tm: Optional[np.ndarray] = None
    abs_si_tm: Optional[np.ndarray] = None
    mode: str = "normal"
    polarization: str = "unpolarized"

    @property
    def n_directions(self) -> int:
        return len(self.theta_deg)

    @property
    def n_theta(self) -> int:
        """Historical alias used by the MATLAB parity fixtures."""
        return self.n_directions

    @property
    def n_lambda(self) -> int:
        return len(self.lambda_um)


# --- helpers shared by the RCWA backends -----------------------------------
#
# Both backends run the same (angle, polarisation, wavelength) sweep and pack
# the same accumulator into RawOptics. Keeping that here means a new backend
# cannot silently disagree with an existing one about TE/TM conventions or
# about when TM is computed at all.

def polarisations(names):
    """Return S4 excitation tuples for the requested polarization names."""
    available = {
        "te": ("te", 1.0, 0.0),
        "tm": ("tm", 0.0, 1.0),
    }
    return [available[name] for name in names]


def new_accumulator(pols, n_lambda: int, n_theta: int):
    """Zeroed ``{pol: {quantity: (n_lambda, n_theta) array}}`` accumulator."""
    return {p[0]: {k: np.zeros((n_lambda, n_theta)) for k in
                   ("ref", "tran", "abs", "abs_si")} for p in pols}


def pack_raw(out, theta_deg: np.ndarray, phi_deg: np.ndarray,
             direction_weight: np.ndarray, lambda_grid: np.ndarray,
             mode: str, polarization: str) -> "RawOptics":
    """Turn a backend accumulator into a :class:`RawOptics`."""
    raw = RawOptics(
        theta_deg=np.asarray(theta_deg, dtype=float),
        phi_deg=np.asarray(phi_deg, dtype=float),
        direction_weight=np.asarray(direction_weight, dtype=float),
        lambda_um=np.asarray(lambda_grid, dtype=float),
        mode=mode,
        polarization=polarization,
    )
    for pol in out:
        for quantity in ("ref", "tran", "abs", "abs_si"):
            setattr(raw, f"{quantity}_{pol}", out[pol][quantity])
    return raw


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
        theta_deg=theta_deg, phi_deg=np.zeros_like(theta_deg),
        direction_weight=np.zeros_like(theta_deg), lambda_um=lambda_um,
        ref_te=te[:, :, 2].T, tran_te=te[:, :, 3].T,
        abs_te=te[:, :, 4].T, abs_si_te=te[:, :, 5].T,
        mode="normal" if len(theta_deg) == 1 and np.isclose(theta_deg[0], 0.0)
        else "hemispherical",
        polarization="unpolarized",
    )
    tm_path = os.path.join(path, "OUTPUTS4-TM.txt")
    if os.path.isfile(tm_path) and os.path.getsize(tm_path) > 0:
        tm = _read_output_file(tm_path, n_lambda)
        raw.ref_tm = tm[:, :, 2].T
        raw.tran_tm = tm[:, :, 3].T
        raw.abs_tm = tm[:, :, 4].T
        raw.abs_si_tm = tm[:, :, 5].T
    if raw.mode == "normal":
        raw.direction_weight[:] = 1.0
    else:
        theta_rad = np.deg2rad(theta_deg)
        dtheta = theta_rad[1] - theta_rad[0]
        # Preserve the MATLAB polar-only quadrature for the read-only historical
        # fixtures. New live hemispherical runs use normalized theta-phi
        # Gauss-Legendre weights from SimulationConfig.directions().
        raw.direction_weight = 2.0 * np.cos(theta_rad) * np.sin(theta_rad) * dtheta
    return raw


def from_reduced_file(path: str, atmosphere_path: str,
                      angles: str = "hemispherical",
                      emittance_column: Optional[int] = None) -> OpticsResult:
    """Load a previously reduced normal or hemispherical optical spectrum.

    With ``emittance_column``, the selected zero-based column is treated as
    hemispherical emittance for an opaque surface. Otherwise, accepted columns
    are either the five-column ``HEMSIPH`` form
    ``lambda, R, T, emit, abs_si`` or the seven-column ``PVcode`` form
    ``lambda, emit, emit_normal, R, R_normal, abs_si, abs_si_normal``.
    These files retain no directional information, so their atmospheric term
    uses the same angle-independent approximation as free-form optics.
    """
    data = np.loadtxt(path)
    if data.ndim == 1:
        data = data[None, :]
    lam = data[:, 0]
    if emittance_column is not None:
        if emittance_column >= data.shape[1]:
            raise ValueError(
                f"{path}: emittance column {emittance_column} is outside "
                f"the {data.shape[1]}-column table.")
        emit = data[:, emittance_column]
        ref, tran, abs_si = 1.0 - emit, np.zeros_like(emit), np.zeros_like(emit)
        ref_norm = emit_norm = abs_si_norm = None
    elif data.shape[1] == 5:
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
        angles=angles,
    )


def _selected(raw: RawOptics, quantity: str) -> np.ndarray:
    """Return the requested polarization, averaging TE/TM if unpolarized."""
    if raw.polarization.lower() == "unpolarized":
        te = getattr(raw, f"{quantity}_te")
        tm = getattr(raw, f"{quantity}_tm")
        if te is None or tm is None:
            raise ValueError("Unpolarized reduction requires both TE and TM data.")
        return 0.5 * (te + tm)
    value = getattr(raw, f"{quantity}_{raw.polarization.lower()}")
    if value is None:
        raise ValueError(
            f"{raw.polarization} reduction requested but its data are absent.")
    return value


def reduce(raw: RawOptics, atmosphere_path: str,
           lambda_grid: Optional[np.ndarray] = None) -> OpticsResult:
    """Reduce directional data to selected or hemispherical spectra.

    ``lambda_grid`` is the canonical simulation wavelength grid
    (``linspace(min, max, n)``). MATLAB uses this exact grid for the atmospheric
    interpolation and the band averages, while the per-angle values come from
    the (slightly round-tripped) S4 output; passing it here reproduces that.
    If omitted, the raw file wavelengths are used.
    """
    lam = raw.lambda_um if lambda_grid is None else np.asarray(lambda_grid, dtype=float)
    theta_deg = raw.theta_deg
    atm = load_atmosphere(atmosphere_path, lam)   # atmospheric transmittance
    ref_dir = _selected(raw, "ref")
    tran_dir = _selected(raw, "tran")
    emit_dir = _selected(raw, "abs")
    abs_si_dir = _selected(raw, "abs_si")

    if raw.mode != "hemispherical":
        if raw.n_directions != 1:
            raise ValueError(
                "Normal/specific reduction requires exactly one direction.")
        ref = ref_dir[:, 0]
        tran = tran_dir[:, 0]
        emit = emit_dir[:, 0]
        abs_si = abs_si_dir[:, 0]
        cos_t = np.cos(np.deg2rad(theta_deg[0]))
        emit_atm = 1.0 - atm ** (1.0 / cos_t)
        product = emit_atm * emit
        return OpticsResult(
            lambda_um=lam, ref=ref, tran=tran, emit=emit, abs_silicon=abs_si,
            emit_atm=emit_atm, emitt_spec_times_emit_atm=product,
            angles=raw.mode, polarization=raw.polarization,
        )

    # The weights integrate cos(theta) dOmega / pi and therefore sum to one for
    # new live runs. The explicit normal probe has zero weight.
    weights = raw.direction_weight
    ref = np.sum(ref_dir * weights[None, :], axis=1)
    tran = np.sum(tran_dir * weights[None, :], axis=1)
    emit = np.sum(emit_dir * weights[None, :], axis=1)
    abs_si = np.sum(abs_si_dir * weights[None, :], axis=1)

    cos_t = np.cos(np.deg2rad(theta_deg))
    emit_atm_2d = 1.0 - atm[:, None] ** (1.0 / cos_t[None, :])
    emit_atm = np.sum(emit_atm_2d * weights[None, :], axis=1)
    product = np.sum(
        emit_atm_2d * emit_dir * weights[None, :], axis=1)

    normal = np.where(np.isclose(theta_deg, 0.0))[0]
    if normal.size == 0:
        raise ValueError(
            "Hemispherical data require an explicit normal-incidence probe.")
    i0 = normal[0]
    ref_norm = ref_dir[:, i0]
    emit_norm = emit_dir[:, i0]
    abs_si_norm = abs_si_dir[:, i0]

    return OpticsResult(
        lambda_um=lam, ref=ref, tran=tran, emit=emit, abs_silicon=abs_si,
        emit_atm=emit_atm, emitt_spec_times_emit_atm=product,
        ref_norm=ref_norm, emit_norm=emit_norm, abs_silicon_norm=abs_si_norm,
        angles="hemispherical", polarization=raw.polarization,
    )
