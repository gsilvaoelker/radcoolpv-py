"""Figures, mirroring the MATLAB plots. All output is gated by ``run.plots``.

Uses a non-interactive backend and writes PNGs into ``<results>/figures``. Which
figures are produced depends on which stages ran (optics and/or thermal) and the
run mode (test/test2 add literature overlays).
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np

from ..io.results import RunContext
from ..validation import references


def make_all(ctx: RunContext, lit_base: str = None) -> list:
    """Create all applicable figures; return the list of file paths written."""
    out_dir = os.path.join(ctx.results_dir, "figures")
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    optics = ctx.optics
    thermal = ctx.thermal

    if ctx.config.run.mode == "spectral_compare":
        return [_spectral_comparison(out_dir, ctx.config)]

    if optics is not None:
        paths.append(_optical_properties(out_dir, optics))

    if thermal is not None:
        paths.append(_cooler_emissivity(out_dir, optics))
        if ctx.config.run.mode == "cooling_curve":
            paths.append(_cooling_power_curve(out_dir, thermal, ctx.config))
        elif ctx.config.run.mode == "test":
            paths.append(_cooling_power_validation(out_dir, thermal, lit_base))
        else:
            paths.append(_energy_balance_terms(out_dir, thermal))
        if thermal.iv is not None:
            paths.append(_iv_curve(out_dir, thermal))
            paths.append(_power_curve(out_dir, thermal))
            paths.append(_efficiency(out_dir, thermal))

    return [p for p in paths if p]


def _save(fig, path):
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return path


def _positive_y_limit(*curves) -> float:
    """Return a first-quadrant upper limit with 10% headroom."""
    largest = max((float(np.nanmax(curve)) for curve in curves), default=0.0)
    return 1.1 * largest if largest > 0.0 else 1.0


def _optical_properties(out_dir, optics):
    fig, ax = plt.subplots(figsize=(7, 4))
    lam = optics.lambda_um
    ax.plot(lam, optics.ref, label="Ref.")
    ax.plot(lam, optics.tran, label="Tran.")
    ax.plot(lam, optics.emit, label="Emiss.")
    ax.plot(lam, optics.abs_silicon, label="Abs. Si")
    ax.set_xlabel(r"Wavelength ($\mu$m)")
    ax.set_ylabel("Absorp., Reflect., Trans.")
    ax.set_xlim(lam[0], lam[-1]); ax.set_ylim(0, 1)
    ax.set_title("Optical properties"); ax.legend(frameon=False)
    return _save(fig, os.path.join(out_dir, "optical_properties.png"))


def _cooler_emissivity(out_dir, optics):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(optics.lambda_um, optics.emit, color="0.35")
    ax.set_xscale("log")
    ax.set_xlabel(r"Wavelength, $\lambda$ ($\mu$m)"); ax.set_ylabel("Emissivity")
    ax.set_ylim(0, 1); ax.set_xlim(0.3, 30)
    ax.set_xticks([0.3, 1.1, 4, 8, 13, 30])
    ax.set_xticklabels(["0.3", "1.1", "4", "8", "13", "30"])
    ax.set_title("Cooler emissivity vs. wavelength")
    return _save(fig, os.path.join(out_dir, "cooler_emissivity.png"))


def _spectral_comparison(out_dir, cfg):
    fig, ax = plt.subplots(figsize=(7, 4))
    for series in cfg.comparison.spectra:
        data = np.loadtxt(cfg.resolve_data(series["file"]))
        kwargs = {"label": series["label"]}
        if "color" in series:
            kwargs["color"] = series["color"]
        ax.plot(data[:, 0], data[:, 1], **kwargs)
    ax.set_xlim(*cfg.comparison.xlim); ax.set_ylim(*cfg.comparison.ylim)
    ax.set_xlabel(cfg.comparison.xlabel)
    ax.set_ylabel(cfg.comparison.ylabel)
    ax.set_title(cfg.comparison.title)
    ax.legend(frameon=False)
    return _save(fig, os.path.join(out_dir, cfg.comparison.output_file))


def _energy_balance_terms(out_dir, t):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(t.emit_temp, t.rad_power, label=r"$P_{rad}$")
    ax.axhline(t.atm_power, ls=":", color="0.5", label=r"$P_{atm}$")
    ax.plot(t.emit_temp, t.cool_power, "-s", ms=4, mfc="white", label=r"$P_{cool}$")
    ax.plot(t.emit_temp, t.conv_power, label=r"$P_{conv}$")
    ax.plot(t.emit_temp, t.max_power_point, label=r"$P_{mpp}$")
    ax.plot(t.emit_temp, t.non_thermal_power, label=r"$P_{nonthermal}$")
    ax.axhline(0.0, color="k", lw=0.8)
    ax.axvline(t.equil_temp, ls="--", color="0.6")
    ax.set_xlabel("Emitter temperature (K)"); ax.set_ylabel(r"Power (W/m$^2$)")
    ax.set_title("Energy-balance terms vs. cooler temperature"); ax.legend(frameon=False, fontsize=8)
    return _save(fig, os.path.join(out_dir, "energy_balance_terms.png"))


def _cooling_power_validation(out_dir, t, lit_base):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(t.emit_temp, t.cool_power, label="This code")
    ref = references.perrakis_fig2(lit_base)
    if ref is not None:
        ax.plot(ref[:, 0], ref[:, 1], "o--", label="Perrakis et al.")
    ax.axhline(0.0, color="k", lw=0.8)
    ax.set_xlabel("Temperature (K)"); ax.set_ylabel(r"Cooling power (W/m$^2$)")
    ax.set_title("Cooling power validation"); ax.legend(frameon=False)
    return _save(fig, os.path.join(out_dir, "cooling_power_validation.png"))


def _cooling_power_curve(out_dir, t, cfg):
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(t.emit_temp, t.cool_power, lw=2, label="radcoolpv")
    path = cfg.resolve_data(cfg.thermal.reference_curve_file)
    if path:
        with open(path) as fh:
            lines = [line for line in fh if not line.startswith("#")]
        data = np.genfromtxt(lines[1:], missing_values="NA", filling_values=np.nan)
        column = cfg.thermal.reference_curve_column
        y = data[:, column]
        valid = np.isfinite(y)
        ax.plot(data[valid, 0], y[valid], "o", ms=3, mfc="white", label="Digitized reference")
    ax.axhline(0.0, color="0.5", lw=0.8)
    ax.axvline(t.equil_temp, ls="--", color="0.5", label=fr"$T_{{eq}}={t.equil_temp:.1f}$ K")
    ax.set_xlabel("Film temperature (K)")
    ax.set_ylabel(r"Cooling power (W/m$^2$)")
    ax.set_title("Cooling power versus film temperature")
    ax.legend(frameon=False)
    return _save(fig, os.path.join(out_dir, "cooling_power_curve.png"))


def _iv_curve(out_dir, t):
    iv = t.iv
    current = -t.current_equil
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(iv.volt, current)
    ax.set_xlabel("Voltage (V)"); ax.set_ylabel(r"Current density (A/m$^2$)")
    ax.set_xlim(left=0.0); ax.set_ylim(0.0, _positive_y_limit(current))
    ax.set_title("Current-voltage characteristic")
    return _save(fig, os.path.join(out_dir, "iv_curve.png"))


def _power_curve(out_dir, t):
    iv = t.iv
    power_equil = t.power_equil
    power_ambient = iv.cell_power[:, 0]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(iv.volt, power_equil, "-s", ms=4, mfc="white",
            label=f"Equilibrium, MPP={t.mpp_equil:.1f}")
    ax.plot(iv.volt, power_ambient, label=f"Ambient, MPP={t.mpp_amb:.1f}")
    ax.set_xlabel("Voltage (V)"); ax.set_ylabel(r"Output power (W/m$^2$)")
    ax.set_xlim(left=0.0); ax.set_ylim(0.0, _positive_y_limit(power_equil, power_ambient))
    ax.set_title("Output power vs. voltage"); ax.legend(frameon=False)
    return _save(fig, os.path.join(out_dir, "power_curve.png"))


def _efficiency(out_dir, t):
    iv = t.iv
    fig, ax = plt.subplots(figsize=(7, 4))
    eff = iv.max_power_point / t.solar_power_am15 * 100.0
    ax.plot(t.emit_temp, eff, "s", ms=4, mfc="white")
    ax.set_xlabel("Emitter temperature (K)"); ax.set_ylabel("Efficiency (%)")
    ax.set_title(f"Efficiency vs. temperature (beta_P={t.beta_p:.2f} %/K)")
    return _save(fig, os.path.join(out_dir, "efficiency.png"))
