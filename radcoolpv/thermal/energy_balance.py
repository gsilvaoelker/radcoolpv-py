"""Assemble the energy balance, solve the equilibrium temperature, report PV.

Port of the energy-balance assembly of ``mainEnergyBalancePV_v11.m``. The old
code required a manual two-step ritual (run, read the equilibrium temperature
and MPP voltage off a plot, paste them back, re-run). Here that is replaced by
an automatic fixed-point iteration (``thermal.equilibrium: auto``); a ``manual``
mode reproduces the exact MATLAB values when needed for validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .._compat import trapz
from ..io.results import OpticsResult
from . import pv
from .radiative import rad_power
from .spectra import SolarSpectrum

_TEST_SOLAR_POWER = 620.0   # W/m^2, absorbed-solar override for the Perrakis Fig.2 test


@dataclass
class ThermalResult:
    emit_temp: np.ndarray
    rad_power: np.ndarray
    atm_power: float
    conv_power: np.ndarray
    solar_power: float            # absorbed solar, W/m^2
    solar_power_am15: float       # total AM1.5, W/m^2
    max_power_point: np.ndarray   # (nT,), zeros in PV-free test mode
    non_thermal_power: np.ndarray
    cool_power: np.ndarray
    equil_temp: float
    vmpp: float
    isc: float = 0.0
    mpp_amb: float = 0.0
    mpp_equil: float = 0.0
    voc_amb: float = 0.0
    voc_equil: float = 0.0
    ff_amb: float = 0.0
    ff_equil: float = 0.0
    beta_p: float = 0.0
    efficiency_equil: float = 0.0
    rad_power_equil: float = 0.0
    current_equil: Optional[np.ndarray] = None
    power_equil: Optional[np.ndarray] = None
    iv: Optional[pv.IVResult] = None
    optics: Optional[OpticsResult] = None


def _zero_crossing(x: np.ndarray, y: np.ndarray) -> tuple:
    """First x where y crosses from negative to non-negative (linear interp)."""
    if y[0] >= 0:
        return float(x[0]), 0
    idx = np.where(y >= 0)[0]
    if idx.size == 0:
        return float(x[-1]), len(x) - 1          # never cools; clamp to hottest
    i = idx[0]
    x0, x1, y0, y1 = x[i - 1], x[i], y[i - 1], y[i]
    xc = x0 + (x1 - x0) * (0.0 - y0) / (y1 - y0)
    nearest = int(np.argmin(np.abs(x - xc)))
    return float(xc), nearest


def _at_equilibrium(values: np.ndarray, temperatures: np.ndarray,
                    equil_temp: float, axis: int = -1) -> np.ndarray:
    """Linearly interpolate a temperature-indexed quantity to ``equil_temp``."""
    values = np.asarray(values)
    if values.ndim == 1:
        return np.interp(equil_temp, temperatures, values)
    moved = np.moveaxis(values, axis, -1)
    out = np.array([np.interp(equil_temp, temperatures, row) for row in moved.reshape(-1, len(temperatures))])
    return out.reshape(moved.shape[:-1])


def run(cfg, optics: OpticsResult, solar: SolarSpectrum) -> ThermalResult:
    lam = optics.lambda_um
    t_amb = cfg.thermal.ambient_temperature
    h = cfg.thermal.convection_coefficient
    is_test = (cfg.run.mode == "test")
    is_cooling_curve = (cfg.run.mode == "cooling_curve")

    emit_temp = (cfg.thermal.cooling_temperature.array() if is_cooling_curve
                 else t_amb + np.arange(pv._N_TEMP, dtype=float))
    atm_power = np.pi * rad_power(lam, optics.emitt_spec_times_emit_atm, t_amb)
    rad_p = np.array([np.pi * rad_power(lam, optics.emit, t) for t in emit_temp])
    conv_p = h * (emit_temp - t_amb)

    if is_test:
        solar_power = _TEST_SOLAR_POWER
    else:
        solar_power = float(trapz(optics.emit * solar.irradiance_per_um, lam))
        if is_cooling_curve and cfg.thermal.solar_irradiance is not None:
            solar_power *= cfg.thermal.solar_irradiance / solar.total_am15

    # --- PV-free cooling curve -------------------------------------------- #
    if is_test or is_cooling_curve:
        cool = rad_p - atm_power + conv_p - solar_power
        equil_temp, _ = _zero_crossing(emit_temp, cool)
        return ThermalResult(
            emit_temp=emit_temp, rad_power=rad_p, atm_power=atm_power, conv_power=conv_p,
            solar_power=solar_power, solar_power_am15=solar.total_am15,
            max_power_point=np.zeros_like(emit_temp), non_thermal_power=np.zeros_like(emit_temp),
            cool_power=cool, equil_temp=equil_temp, vmpp=0.0,
            rad_power_equil=float(_at_equilibrium(rad_p, emit_temp, equil_temp)),
            optics=optics,
        )

    # --- full PV path ----------------------------------------------------- #
    iv = pv.solve_iv(cfg, optics, solar.photon_flux)

    def assemble(vmpp):
        ntp = pv.non_thermal_power(iv, optics, vmpp)
        cool = rad_p - atm_power + conv_p - solar_power + iv.max_power_point + ntp
        return ntp, cool

    if cfg.thermal.equilibrium == "manual":
        vmpp = cfg.thermal.vmpp
        ntp, cool = assemble(vmpp)
        equil_temp = cfg.thermal.emit_temp
    else:
        # Fixed point: Vmpp -> non-thermal power -> equilibrium T -> Vmpp(T_eq).
        vmpp = 0.65
        equil_temp = t_amb
        for _ in range(50):
            ntp, cool = assemble(vmpp)
            equil_temp, _ = _zero_crossing(emit_temp, cool)
            power_equil = _at_equilibrium(iv.cell_power, emit_temp, equil_temp, axis=1)
            vmpp_new = float(iv.volt[np.argmax(power_equil)])
            if abs(vmpp_new - vmpp) < 1e-4:
                vmpp = vmpp_new
                break
            vmpp = vmpp_new
        ntp, cool = assemble(vmpp)

    # Report every equilibrium quantity at the same interpolated temperature.
    mpp_amb = float(iv.cell_power[:, 0].max())
    power_equil = _at_equilibrium(iv.cell_power, emit_temp, equil_temp, axis=1)
    current_equil = _at_equilibrium(iv.current_dens, emit_temp, equil_temp, axis=0)
    mpp_equil = float(power_equil.max())
    voc_amb = pv.open_circuit_voltage(iv.current_dens[0, :], iv.volt)
    voc_equil = pv.open_circuit_voltage(current_equil, iv.volt)
    ff_amb = mpp_amb / (iv.isc * voc_amb) if (iv.isc and voc_amb) else 0.0
    ff_equil = mpp_equil / (iv.isc * voc_equil) if (iv.isc and voc_equil) else 0.0
    denom = (t_amb - equil_temp)
    beta_p = ((mpp_amb - mpp_equil) / denom * (100.0 / mpp_amb)) if (denom and mpp_amb) else 0.0
    efficiency_equil = mpp_equil / solar.total_am15
    rad_power_equil = float(_at_equilibrium(rad_p, emit_temp, equil_temp))

    return ThermalResult(
        emit_temp=emit_temp, rad_power=rad_p, atm_power=atm_power, conv_power=conv_p,
        solar_power=solar_power, solar_power_am15=solar.total_am15,
        max_power_point=iv.max_power_point, non_thermal_power=ntp, cool_power=cool,
        equil_temp=equil_temp, vmpp=vmpp, isc=iv.isc,
        mpp_amb=mpp_amb, mpp_equil=mpp_equil, voc_amb=voc_amb, voc_equil=voc_equil,
        ff_amb=ff_amb, ff_equil=ff_equil, beta_p=beta_p, efficiency_equil=efficiency_equil,
        rad_power_equil=rad_power_equil, current_equil=current_equil, power_equil=power_equil,
        iv=iv, optics=optics,
    )
