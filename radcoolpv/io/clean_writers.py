"""Clean CSV outputs and a reproducibility manifest."""

from __future__ import annotations

import csv
from dataclasses import asdict
import hashlib
import json
import os
import platform
import subprocess
import sys
from typing import Optional

import numpy as np

from ..config import Config
from .results import OpticsResult


def _write_csv(folder: str, name: str, cols: np.ndarray, header: str) -> None:
    """One format for every clean CSV: comma-separated, bare header, %.8g."""
    np.savetxt(os.path.join(folder, name), cols, delimiter=",",
               header=header, comments="", fmt="%.8g")


def write_optics_csv(folder: str, optics: OpticsResult) -> None:
    cols = np.column_stack([
        optics.lambda_um, optics.ref, optics.tran, optics.emit, optics.abs_silicon,
        optics.emit_atm, optics.ref_norm, optics.emit_norm, optics.abs_silicon_norm,
    ])
    _write_csv(folder, "optics.csv", cols,
               "lambda_um,ref,tran,emit,abs_silicon,emit_atm,"
               "ref_norm,emit_norm,abs_silicon_norm")


def write_optics_export(path: str, optics: OpticsResult) -> None:
    """Write the spectrum in the five-column form ``optics_results`` reads.

    ``optics.csv`` cannot serve this purpose: it is comma-separated with a text
    header, while the resume reader uses whitespace-separated numeric columns.
    Columns are ``lambda_um R T emit abs_si``, matching that reader exactly, so
    an optics run and a later thermal run chain with no conversion step.
    """
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    cols = np.column_stack([optics.lambda_um, optics.ref, optics.tran,
                            optics.emit, optics.abs_silicon])
    np.savetxt(path, cols, fmt="%.6e",
               header="lambda_um   R           T           emit        abs_si\n"
                      f"radcoolpv optics export ({optics.angles} spectrum)")


def write_directional_csv(folder: str, raw) -> None:
    """Write every S4 direction and polarization without MATLAB conventions."""
    path = os.path.join(folder, "optics_directional.csv")
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "lambda_um", "polar_angle_deg", "azimuth_angle_deg",
            "polarization", "angular_weight", "ref", "tran", "abs",
            "abs_silicon",
        ])
        for pol in ("te", "tm"):
            ref = getattr(raw, f"ref_{pol}")
            if ref is None:
                continue
            tran = getattr(raw, f"tran_{pol}")
            absorb = getattr(raw, f"abs_{pol}")
            absorb_si = getattr(raw, f"abs_si_{pol}")
            for direction, (theta, phi, weight) in enumerate(zip(
                    raw.theta_deg, raw.phi_deg, raw.direction_weight)):
                for wavelength, lam in enumerate(raw.lambda_um):
                    writer.writerow([
                        f"{lam:.10g}", f"{theta:.10g}", f"{phi:.10g}",
                        pol.upper(), f"{weight:.10g}",
                        f"{ref[wavelength, direction]:.10g}",
                        f"{tran[wavelength, direction]:.10g}",
                        f"{absorb[wavelength, direction]:.10g}",
                        f"{absorb_si[wavelength, direction]:.10g}",
                    ])


def write_iv_csv(folder: str, thermal) -> None:
    cols = np.column_stack([thermal.iv.volt, -thermal.current_equil])
    _write_csv(folder, "iv.csv", cols, "voltage_V,current_density_A_per_m2")


def write_power_csv(folder: str, thermal) -> None:
    iv = thermal.iv
    cols = np.column_stack([iv.volt, thermal.power_equil, iv.cell_power[:, 0]])
    _write_csv(folder, "power.csv", cols,
               "voltage_V,power_equilibrium_W_per_m2,power_ambient_W_per_m2")


def write_cooling_curve_csv(folder: str, thermal) -> None:
    """Cooling power versus emitter temperature for PV-free runs."""
    cols = np.column_stack([thermal.emit_temp, thermal.cool_power])
    _write_csv(folder, "cooling_power.csv", cols,
               "temperature_K,cooling_power_W_per_m2")


def write_run_json(folder: str, cfg: Config, optics: Optional[OpticsResult],
                   thermal) -> None:
    """Write the resolved case, input hashes, runtime, and scalar results."""
    record = {
        "resolved_config": asdict(cfg),
        "provenance": _provenance(cfg),
    }
    if optics is not None:
        record["optics"] = {
            "angles": optics.angles,
            "polarization": optics.polarization,
            "n_lambda": int(len(optics.lambda_um)),
        }
    if thermal is not None:
        record["thermal_results"] = {
            "equilibrium_temperature_K": thermal.equil_temp,
            "temperature_reduction_K": thermal.temperature_reduction,
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


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_value(repo: str, *args: str) -> Optional[str]:
    result = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def _provenance(cfg: Config) -> dict:
    package_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", ".."))
    paths = {
        "config": cfg.config_path,
        "solar_spectrum": cfg.resolve_data(cfg.data.solar_spectrum),
        "atmosphere": cfg.resolve_data(cfg.data.atmosphere),
        "iqe": cfg.resolve_data(cfg.thermal.pv.iqe_file),
        "optics_results": cfg.resolve_data(cfg.run.optics_results),
    }
    if cfg.geometry.source == "freeform":
        paths["freeform"] = cfg.resolve_data(
            cfg.geometry.freeform.get("file"))
    inputs = {
        name: {"path": path, "sha256": _sha256(path)}
        for name, path in paths.items()
        if path and os.path.isfile(path)
    }
    s4 = None
    if cfg.run.optics and cfg.geometry.source == "s4":
        import S4
        s4 = {
            "module_path": S4.__file__,
            "sha256": _sha256(S4.__file__),
        }
    dirty = _git_value(package_root, "status", "--porcelain",
                       "--untracked-files=no", "--", ".")
    record = {
        "python": sys.version,
        "platform": platform.platform(),
        "git_commit": _git_value(package_root, "rev-parse", "HEAD"),
        "git_dirty": bool(dirty),
        "inputs": inputs,
        "s4": s4,
    }
    return record
