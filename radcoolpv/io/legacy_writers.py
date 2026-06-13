"""Legacy MATLAB-style output files.

Reproduces the text artifacts of the original scripts so existing post-
processing keeps working:

* ``OUTPUTS4-TE.txt`` / ``OUTPUTS4-TM.txt`` — raw per-angle optics
  (theta, lambda, R, T, A, A_silicon), theta-major.
* ``opticalProps-PVcode.txt`` — lambda + hemispherical/normal R/emit/Si-abs.
* ``IV-PVcode.txt`` / ``Power-PVcode.txt`` — I-V and power at the equilibrium
  (and ambient) temperature.
* ``simulParam.log`` / ``simulParamPV.log`` — parameter + results dumps.
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np

from ..config import Config
from ..optics.averages import OpticalAverages, PVAverages
from .results import OpticsResult


def write_raw_optics(folder: str, raw) -> None:
    """Write OUTPUTS4-TE.txt (and -TM.txt if present) from a RawOptics object."""
    def dump(name, ref, tran, abst, abssi):
        rows = []
        for it, theta in enumerate(raw.theta_deg):
            for il in range(raw.n_lambda):
                rows.append((theta, raw.lambda_um[il], ref[il, it],
                             tran[il, it], abst[il, it], abssi[il, it]))
        np.savetxt(os.path.join(folder, name), np.array(rows),
                   fmt="%.10g", delimiter="\t")

    dump("OUTPUTS4-TE.txt", raw.ref_te, raw.tran_te, raw.abs_te, raw.abs_si_te)
    if raw.ref_tm is not None:
        dump("OUTPUTS4-TM.txt", raw.ref_tm, raw.tran_tm, raw.abs_tm, raw.abs_si_tm)


def write_pv_optical_props(folder: str, optics: OpticsResult) -> None:
    """opticalProps-PVcode.txt: lambda, emit, emitNorm, ref, refNorm, absSi, absSiNorm."""
    cols = np.column_stack([
        optics.lambda_um, optics.emit, optics.emit_norm, optics.ref,
        optics.ref_norm, optics.abs_silicon, optics.abs_silicon_norm,
    ])
    np.savetxt(os.path.join(folder, "opticalProps-PVcode.txt"), cols, fmt="%6.6f")


def write_iv(folder: str, thermal) -> None:
    """IV-PVcode.txt: voltage, output current density at equilibrium temperature."""
    iv = thermal.iv
    j = -iv.current_dens[thermal.equil_index, :]
    np.savetxt(os.path.join(folder, "IV-PVcode.txt"),
               np.column_stack([iv.volt, j]), fmt="%6.6f")


def write_power(folder: str, thermal) -> None:
    """Power-PVcode.txt: voltage, power(equilibrium), power(ambient)."""
    iv = thermal.iv
    cols = np.column_stack([
        iv.volt, iv.cell_power[:, thermal.equil_index], iv.cell_power[:, 0],
    ])
    np.savetxt(os.path.join(folder, "Power-PVcode.txt"), cols, fmt="%6.6f")


def write_optical_log(folder: str, cfg: Config, optics: OpticsResult,
                      averages: Optional[OpticalAverages]) -> None:
    g = cfg.geometry
    w = cfg.simulation.wavelength
    lines = [
        f"shape: {g.shape}",
        f"photonic structure material: {g.photonic_material}",
        f"wavelength window: {w.min:.3f} - {w.max:.3f} um",
        f"number of wavelength points: {w.n}",
        f"angles: {cfg.simulation.angles}",
        f"number of modes: {cfg.simulation.rcwa_modes}",
        f"lattice: {g.lattice.type}, x={g.lattice.x} um, y={g.lattice.y} um",
        "layer stack (top to bottom): " + ", ".join(
            f"{l.material}={l.thickness}um" for l in cfg.structure),
        "Column names of output data: theta_inc, lambda (um), R, T, A, A (silicon layer)",
    ]
    if averages is not None:
        lines += [
            "Averages in different parts of the spectrum",
            f"Average silicon absorption between 0.3 and lambda_g: {averages.solar_abs:.4f}",
            f"Average reflectance between lambda_g and 4 um: {averages.subgap_ref:.4f}",
            f"Average emittance between 8 um and 13 um: {averages.emit_window1:.4f}",
            f"Average emittance between 17 um and 24 um: {averages.emit_window2:.4f}",
            f"Average emittance between 4 um and 30 um: {averages.emit_broad:.4f}",
        ]
    _write_lines(os.path.join(folder, "simulParam.log"), lines)


def write_pv_log(folder: str, cfg: Config, thermal, averages: Optional[PVAverages]) -> None:
    t = thermal
    lines = [
        f"Si PV cell thickness: {cfg.thick_si():.3f} um",
        f"Voltage range: {cfg.thermal.voltage.min:.3f} - {cfg.thermal.voltage.max:.3f} V",
        f"Ambient temperature: {cfg.thermal.ambient_temperature:.3f} K",
        f"Convection coefficient: {cfg.thermal.convection_coefficient:.3f} W/m2 K",
        f"calculation: {t.optics.angles}",
        f"Solar power absorbed by the structure: {t.solar_power:.3f} W/m2",
        f"Solar power AM1.5G: {t.solar_power_am15:.3f} W/m2",
        f"Short circuit current: {t.isc:.3f} A/m2",
        f"MPP at ambient temperature: {t.mpp_amb:.3f} W/m2",
        f"MPP at emitter temperature: {t.mpp_equil:.3f} W/m2",
        f"FF at ambient temperature: {t.ff_amb:.3f}",
        f"FF at emitter temperature: {t.ff_equil:.3f}",
        f"Atmospheric power: {t.atm_power:.3f} W/m2",
        f"Temperature coefficient: {t.beta_p:.3f} perc/K",
        f"Equilibrium temperature: {t.equil_temp:.3f} K",
        f"MPP voltage: {t.vmpp:.4f} V",
        f"Solar cell efficiency: {t.efficiency_equil:.4f}",
        f"Voc at equilibrium: {t.voc_equil:.3f} V",
        f"equilibrium mode: {cfg.thermal.equilibrium}",
    ]
    if averages is not None:
        lines.append(
            "Aver. props. perc. (A[0.3,1.1]; R[1.1,4]; E[4,30]; R[0.3,1.1]): "
            f"{averages.solar_abs:.4f} {averages.subgap_ref:.4f} "
            f"{averages.emit_broad:.4f} {averages.solar_ref:.4f}")
    _write_lines(os.path.join(folder, "simulParamPV.log"), lines)


def _write_lines(path: str, lines) -> None:
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
