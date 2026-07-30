"""Silicon PV cell electrical model.

Port of the PV / I-V block of ``mainEnergyBalancePV_v11.m``: temperature-
dependent bandgap, short-circuit current (IQE x absorption x solar photon flux),
dark/saturation current, Auger recombination, the series/shunt-resistance I-V
solved with ``fsolve``, and the maximum-power-point / Voc / fill-factor reporting.

All spectral integrals run up to the band-gap wavelength ``lambda_g``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
from scipy.optimize import fsolve

from .._compat import trapz
from ..constants import (CLIGHT, ECHARGE, HPLANCK, KBOLTZ, MICRON,
                         MICRON2TOM2, MTOMICRON)
from ..io.results import OpticsResult

# Auger recombination coefficient vs temperature (cm^6/s); from the source paper.
_AUGER_T = np.array([195.0, 252.0, 294.0, 333.0, 372.0])
_AUGER_A = np.array([3.03e-31, 3.51e-31, 3.88e-31, 4.15e-31, 4.55e-31])

_N_TEMP = 151  # standard PV sweep: T_amb .. T_amb + 150 K


@dataclass
class IVResult:
    emit_temp: np.ndarray         # (nT,) emitter temperatures, K
    volt: np.ndarray              # (nV,) applied voltages, V
    current_dens: np.ndarray      # (nT, nV) diode current density, A/m^2
    cell_power: np.ndarray        # (nV, nT) output power, -J*V, W/m^2
    max_power_point: np.ndarray   # (nT,) max over V, W/m^2
    isc: float                    # short-circuit current density, A/m^2
    current_sat: np.ndarray       # (nT,) saturation current, A/m^2
    auger_current: np.ndarray     # (nT, nV), A/m^2
    lam_eg_index: int             # 0-based inclusive upper index for lambda_g
    iqe: np.ndarray               # (nLambda,) internal quantum efficiency
    abs_pv: np.ndarray            # (nLambda,) silicon absorptance (hemispherical)
    abs_pv_norm: np.ndarray       # (nLambda,) silicon absorptance (normal)


def load_iqe(path: str, lambda_um: np.ndarray) -> np.ndarray:
    """Interpolate the measured internal quantum efficiency onto the grid (0 out of range)."""
    data = np.loadtxt(path)
    iqe = np.interp(lambda_um, data[:, 0], data[:, 1], left=np.nan, right=np.nan)
    return np.nan_to_num(iqe, nan=0.0)


def _bandgap_wavelength_um(emit_temp: np.ndarray, eg0: float, alpha: float, beta: float) -> float:
    """Band-gap wavelength (um). Reproduces the MATLAB scalar mrdivide reduction.

    MATLAB computes ``Eg0 - alpha*T.^2/(T+beta)`` with ``/`` (matrix right
    division) on row vectors, which collapses to a single scalar
    ``dot(T^2, T+beta) / dot(T+beta, T+beta)``. We keep that exact behaviour so
    ``lambda_g`` (and the integration cut-off) matches.
    """
    t = np.asarray(emit_temp, dtype=float)
    eg = eg0 - alpha * np.dot(t ** 2, t + beta) / np.dot(t + beta, t + beta)
    return HPLANCK * CLIGHT / (eg * ECHARGE) / MICRON


def _photon_flux_blackbody(lam: np.ndarray, temp: float) -> np.ndarray:
    """Blackbody photon flux, photons/(s um^3) (lambda in um)."""
    return (2 * np.pi * CLIGHT * MTOMICRON / lam ** 4) / (
        np.exp(HPLANCK * CLIGHT / (lam * MICRON * KBOLTZ * temp)) - 1.0)


def solve_iv(cfg, optics: OpticsResult, photon_flux_sun: np.ndarray) -> IVResult:
    """Solve the temperature- and voltage-dependent I-V and derived quantities."""
    lam = optics.lambda_um
    n_lambda = len(lam)
    lambda_delta = lam[1] - lam[0]
    thick_si = cfg.thick_si()
    volt = cfg.thermal.voltage.array()
    rs = cfg.thermal.pv.series_resistance
    rsh = cfg.thermal.pv.shunt_resistance
    bg = cfg.thermal.pv.bandgap

    emit_temp = cfg.thermal.ambient_temperature + np.arange(_N_TEMP, dtype=float)

    # Band-gap wavelength and its grid index (inclusive upper bound for integrals).
    lam_eg = _bandgap_wavelength_um(emit_temp, bg.eg0, bg.alpha, bg.beta)
    hits = np.where((lam > lam_eg - lambda_delta / 2) & (lam < lam_eg + lambda_delta / 2))[0]
    eg_idx = int(hits[0]) if hits.size else int(np.argmin(np.abs(lam - lam_eg)))
    eg = slice(0, eg_idx + 1)

    iqe = load_iqe(cfg.resolve_data(cfg.thermal.pv.iqe_file), lam)
    abs_pv = optics.abs_silicon
    abs_pv_norm = optics.abs_silicon_norm

    # Short-circuit current (A/m^2): IQE * absorption * solar photon flux up to lambda_g.
    jsc_spectral = iqe[eg] * abs_pv[eg] * photon_flux_sun[eg]
    isc = ECHARGE * trapz(jsc_spectral, lam[eg]) * MICRON

    current_dens = np.zeros((_N_TEMP, len(volt)))
    cell_power = np.zeros((len(volt), _N_TEMP))
    max_power_point = np.zeros(_N_TEMP)
    current_sat = np.zeros(_N_TEMP)
    auger_current = np.zeros((_N_TEMP, len(volt)))

    for it, temp in enumerate(emit_temp):
        # Intrinsic carrier concentration (m^-3) and Auger coefficient (m^6/s).
        ni = 5.29e19 * (temp / 300.0) ** 2.54 * np.exp(-6726.0 / temp) * 1e6
        a_auger = np.interp(temp, _AUGER_T, _AUGER_A) * 1e-12

        auger = (ECHARGE * 2 * a_auger * ni ** 3 * thick_si * MICRON
                 * np.exp(3 * ECHARGE * volt / (2 * KBOLTZ * temp)))
        auger_current[it, :] = auger

        pf_bb = _photon_flux_blackbody(lam[eg], temp)
        sat_spectral = iqe[eg] * abs_pv[eg] * pf_bb
        j0 = ECHARGE * trapz(sat_spectral, lam[eg]) / MICRON2TOM2
        current_sat[it] = j0

        # I-V with series + shunt resistance: solve f(Id) = 0 per voltage,
        # warm-starting from the previous solution (continuation).
        id0 = isc
        for iv, v in enumerate(volt):
            a_v = auger[iv]

            def f(idn, v=v, a_v=a_v):
                vd = v - idn * rs
                return (-idn + vd / rsh
                        + j0 * (np.exp(ECHARGE * vd / (KBOLTZ * temp)) - 1.0)
                        + a_v - isc)

            idn = fsolve(f, id0, full_output=False)[0]
            current_dens[it, iv] = idn
            id0 = idn

        cell_power[:, it] = -current_dens[it, :] * volt
        max_power_point[it] = refine_peak(volt, cell_power[:, it])[1]

    return IVResult(
        emit_temp=emit_temp, volt=volt, current_dens=current_dens, cell_power=cell_power,
        max_power_point=max_power_point, isc=isc, current_sat=current_sat,
        auger_current=auger_current, lam_eg_index=eg_idx, iqe=iqe,
        abs_pv=abs_pv, abs_pv_norm=abs_pv_norm,
    )


def non_thermal_power(iv: IVResult, optics: OpticsResult, vmpp: float) -> np.ndarray:
    """Luminescence (non-thermal radiation) emitted by the cell vs temperature, W/m^2.

    Depends on the MPP voltage ``vmpp`` (the fixed-point variable).
    """
    lam = optics.lambda_um
    eg = slice(0, iv.lam_eg_index + 1)
    out = np.zeros_like(iv.emit_temp)
    for it, temp in enumerate(iv.emit_temp):
        pf_bb = _photon_flux_blackbody(lam[eg], temp)
        irrad = pf_bb * HPLANCK * CLIGHT * MTOMICRON / (lam[eg] * np.pi)
        spectral = iv.iqe[eg] * iv.abs_pv_norm[eg] * irrad
        out[it] = (np.pi * trapz(spectral, lam[eg])
                   * np.exp(ECHARGE * vmpp / (KBOLTZ * temp)) / MICRON2TOM2)
    return out


def refine_peak(x: np.ndarray, y: np.ndarray) -> tuple:
    """Sub-grid maximum of ``y(x)`` by a parabola through the peak and its
    neighbours, returning ``(x_peak, y_peak)``.

    ``max()`` over a sampled curve reports the largest *sample*, not the peak,
    so both Pmpp and Vmpp would otherwise inherit the resolution of
    ``thermal.voltage``. The power curve is smooth and near-parabolic around
    the maximum, so three points recover it to well below the grid step.

    Falls back to the raw sample when the maximum sits on a boundary or the
    three points are collinear. Assumes locally uniform spacing, which holds -
    the voltage grid is a linspace.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    i = int(np.argmax(y))
    if i == 0 or i == len(y) - 1:
        return float(x[i]), float(y[i])

    y0, y1, y2 = y[i - 1], y[i], y[i + 1]
    denom = y0 - 2.0 * y1 + y2
    if denom == 0.0:
        return float(x[i]), float(y[i])

    delta = 0.5 * (y0 - y2) / denom            # in grid steps, within [-0.5, 0.5]
    step = x[i + 1] - x[i]
    return float(x[i] + delta * step), float(y1 - 0.25 * (y0 - y2) * delta)


def open_circuit_voltage(current_dens_row: np.ndarray, volt: np.ndarray) -> float:
    """Voltage where the output current ``-J`` crosses zero.

    The MATLAB original used ``find`` and returned the last grid point *before*
    the crossing, which quantises Voc to the voltage grid and biases it low by
    up to one step (7 mV on the default 0.1-0.8 V, n=100 sweep). This
    interpolates the crossing instead, so Voc no longer depends on how finely
    ``thermal.voltage`` happens to be sampled.

    Raises if the sweep does not bracket Voc. The previous behaviour returned
    ``volt[-1]`` in that case, which is silently wrong in both directions: too
    low when Voc lies above the sweep, and wildly too high when it lies below
    (it returned the maximum voltage for a cell already past open circuit).
    """
    out = -np.asarray(current_dens_row, dtype=float)
    volt = np.asarray(volt, dtype=float)

    if out[0] < 0.0:
        raise ValueError(
            f"Output current is already negative at the lowest swept voltage "
            f"({volt[0]:g} V), so Voc lies below the sweep. Lower "
            f"thermal.voltage.min."
        )
    neg = np.where(out < 0.0)[0]
    if neg.size == 0:
        raise ValueError(
            f"Output current never crosses zero within {volt[0]:g}-{volt[-1]:g} V, "
            f"so Voc lies above the sweep. Raise thermal.voltage.max."
        )

    i = int(neg[0])
    y0, y1 = out[i - 1], out[i]
    return float(volt[i - 1] + (volt[i] - volt[i - 1]) * y0 / (y0 - y1))
