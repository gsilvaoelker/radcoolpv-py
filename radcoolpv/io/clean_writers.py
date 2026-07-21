"""Clean, tidy output files: CSV with headers + a JSON run record.

Same physical data as the legacy writers, in formats that are easy to consume
downstream (pandas, plotting, etc.).
"""

from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np

from ..config import Config
from .results import OpticsResult


def write_optics_csv(folder: str, optics: OpticsResult) -> None:
    header = "lambda_um,ref,tran,emit,abs_silicon,emit_atm,ref_norm,emit_norm,abs_silicon_norm"
    cols = np.column_stack([
        optics.lambda_um, optics.ref, optics.tran, optics.emit, optics.abs_silicon,
        optics.emit_atm, optics.ref_norm, optics.emit_norm, optics.abs_silicon_norm,
    ])
    np.savetxt(os.path.join(folder, "optics.csv"), cols, delimiter=",",
               header=header, comments="", fmt="%.8g")


def write_iv_csv(folder: str, thermal) -> None:
    iv = thermal.iv
    cols = np.column_stack([iv.volt, -thermal.current_equil])
    np.savetxt(os.path.join(folder, "iv.csv"), cols, delimiter=",",
               header="voltage_V,current_density_A_per_m2", comments="", fmt="%.8g")


def write_power_csv(folder: str, thermal) -> None:
    iv = thermal.iv
    cols = np.column_stack([
        iv.volt, thermal.power_equil, iv.cell_power[:, 0]])
    np.savetxt(os.path.join(folder, "power.csv"), cols, delimiter=",",
               header="voltage_V,power_equilibrium_W_per_m2,power_ambient_W_per_m2",
               comments="", fmt="%.8g")


def write_cooling_curve_csv(folder: str, thermal) -> None:
    """Cooling power versus emitter temperature for PV-free runs."""
    cols = np.column_stack([thermal.emit_temp, thermal.cool_power])
    np.savetxt(os.path.join(folder, "cooling_power.csv"), cols, delimiter=",",
               header="temperature_K,cooling_power_W_per_m2", comments="", fmt="%.8g")


def write_run_json(folder: str, cfg: Config, optics: Optional[OpticsResult],
                   thermal) -> None:
    """A single JSON record of the run: key inputs + scalar results."""
    record = {
        "run": {"optics": cfg.run.optics, "thermal": cfg.run.thermal,
                "mode": cfg.run.mode},
        "simulation": {
            "wavelength": {"min": cfg.simulation.wavelength.min,
                           "max": cfg.simulation.wavelength.max,
                           "n": cfg.simulation.wavelength.n},
            "angles": cfg.simulation.angles,
            "rcwa_modes": cfg.simulation.rcwa_modes,
        },
        "geometry": {"source": cfg.geometry.source, "shape": cfg.geometry.shape,
                     "photonic_material": cfg.geometry.photonic_material},
    }
    if optics is not None:
        record["optics"] = {"angles": optics.angles, "n_lambda": int(len(optics.lambda_um))}
    if thermal is not None:
        record["thermal"] = {
            "ambient_temperature": cfg.thermal.ambient_temperature,
            "convection_coefficient": cfg.thermal.convection_coefficient,
            "solar_irradiance_W_per_m2": cfg.thermal.solar_irradiance,
            "equilibrium_mode": cfg.thermal.equilibrium,
            "equilibrium_temperature_K": thermal.equil_temp,
            "vmpp_V": thermal.vmpp,
            "short_circuit_current_A_per_m2": thermal.isc,
            "mpp_ambient_W_per_m2": thermal.mpp_amb,
            "mpp_equilibrium_W_per_m2": thermal.mpp_equil,
            "voc_equilibrium_V": thermal.voc_equil,
            "fill_factor_equilibrium": thermal.ff_equil,
            "atmospheric_power_W_per_m2": thermal.atm_power,
            "absorbed_solar_power_W_per_m2": thermal.solar_power,
            "temperature_coefficient_perc_per_K": thermal.beta_p,
            "efficiency_equilibrium": thermal.efficiency_equil,
        }
    with open(os.path.join(folder, "run.json"), "w") as fh:
        json.dump(record, fh, indent=2)
