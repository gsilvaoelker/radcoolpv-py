"""Reduce directional S4 results to spectral optical properties.

Ports ``normalPropsFunc.m`` and ``hemisphPropsFunc.m``. The raw input is the
reflectance/transmittance/absorptance/silicon-absorptance for each wavelength,
direction, and polarization from a live S4 sweep. :func:`from_file` is the
other way in: a spectrum computed or measured elsewhere.

Output is an :class:`~radcoolpv.io.results.OpticsResult`: the hemispherical (or
normal) spectral properties plus the normal-incidence copies the thermal stage
needs for the luminescence term, and the atmospheric emissivity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..io.results import OpticsResult
from ..thermal.spectra import load_atmosphere
from .averages import LAMBDA_GAP


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


# --- sweep helpers used by the S4 engine -----------------------------------
#
# The (angle, polarisation, wavelength) sweep and the accumulator that packs it
# into RawOptics live here rather than in the engine, so the TE/TM conventions
# and the rule for when TM is computed stay in one place.

def polarisations(names):
    """Return S4 excitation tuples for the requested polarization names."""
    available = {
        "te": ("te", 1.0, 0.0),
        "tm": ("tm", 0.0, 1.0),
    }
    return [available[name] for name in names]


#: The four fluxes carried per polarization, and the suffixes on RawOptics.
QUANTITIES = ("ref", "tran", "abs", "abs_si")


def new_accumulator(pols, n_lambda: int, n_theta: int):
    """Zeroed ``{pol: {quantity: (n_lambda, n_theta) array}}`` accumulator."""
    return {p[0]: {k: np.zeros((n_lambda, n_theta)) for k in QUANTITIES}
            for p in pols}


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
        for quantity in QUANTITIES:
            setattr(raw, f"{quantity}_{pol}", out[pol][quantity])
    return raw


#: Column order of ``optics.txt``, written by every run and read back by
#: ``optics.file`` when no ``column`` is given.
OPTICS_TXT_COLUMNS = "lambda_um R T emit abs_si emit*emit_atm"


def from_file(path: str, atmosphere_path: str,
              column: Optional[int] = None) -> OpticsResult:
    """Load a spectrum from a table whose column 0 is the wavelength in um.

    With ``column``, that column is the hemispherical emittance of an opaque
    surface (R = 1 - emit, T = 0). Without it the file is a radcoolpv
    ``optics.txt``: ``lambda, R, T, emit, abs_si, <emit * emit_atm>``.

    The sixth column is what lets a stored spectrum reproduce the run that
    wrote it. A hemispherical sweep forms the atmospheric term as the angular
    average of ``emit_atm(lambda, theta) * emit(lambda, theta)``, and no
    averaged spectrum carries enough information to rebuild that; a single
    emittance column falls back to the zenith atmosphere times the emittance.
    """
    data = np.loadtxt(path)
    if data.ndim == 1:
        data = data[None, :]
    lam = data[:, 0]
    atm = load_atmosphere(atmosphere_path, lam)
    if column is not None:
        if column >= data.shape[1]:
            raise ValueError(
                f"{path}: optics.column {column} is outside the "
                f"{data.shape[1]}-column table.")
        emit = data[:, column]
        ref, tran = 1.0 - emit, np.zeros_like(emit)
        # A single emittance column carries no layer-resolved absorptance, so
        # the silicon share is inferred: above the gap essentially everything
        # absorbed is absorbed in the silicon, below it nothing is. pv.py then
        # truncates at its own temperature-dependent lambda_g, which is the
        # stricter cut-off, so this only has to be right about which side of
        # the gap a wavelength falls on.
        abs_si = np.where(lam < LAMBDA_GAP, emit, 0.0)
        product = (1.0 - atm) * emit          # zenith atmosphere: all a column can give
    elif data.shape[1] == 6:
        ref, tran, emit, abs_si, product = data[:, 1:].T
    else:
        raise ValueError(
            f"{path}: expected the six columns of a radcoolpv optics.txt "
            f"({OPTICS_TXT_COLUMNS}), got {data.shape[1]}. For any other table "
            "set optics.column to the emittance column.")
    return OpticsResult(
        lambda_um=lam, ref=ref, tran=tran, emit=emit, abs_silicon=abs_si,
        emitt_spec_times_emit_atm=product,
        angles="file", silicon_from_emittance=column is not None,
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
        product = (1.0 - atm ** (1.0 / cos_t)) * emit
        return OpticsResult(
            lambda_um=lam, ref=ref, tran=tran, emit=emit, abs_silicon=abs_si,
            emitt_spec_times_emit_atm=product,
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
        emitt_spec_times_emit_atm=product,
        ref_norm=ref_norm, emit_norm=emit_norm, abs_silicon_norm=abs_si_norm,
        angles="hemispherical", polarization=raw.polarization,
    )
