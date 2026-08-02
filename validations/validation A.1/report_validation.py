"""Generate the Validation A.1 literature-validation report.

The report combines:
  * normal-incidence live-S4 soda-lime optical spectra against the published
    Fig. 3(b) blue normal-incidence columns, and
  * thermal/PV scalars and IV/PV curves from the published hemispherical
    spectrum used for the Table 1 comparison.

By default this reuses ``data/optics/hemisph_sodalime_normal.txt`` so the report
is quick to regenerate. Use ``--run-live`` to rebuild the normal-incidence S4
export before plotting.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from radcoolpv import config as config_module
from radcoolpv import pipeline
from radcoolpv._compat import trapz
from radcoolpv.optics import directional
from radcoolpv.optics.averages import _find_first, band_average, pv_band_averages
from radcoolpv.thermal import energy_balance
from radcoolpv.thermal.spectra import load_solar

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]

OPTICS_YAML = BASE / "optics_hemisph_sodalime.yaml"
PV_YAML = BASE / "pv_hemisph_sodalime.yaml"
LIVE_EXPORT = BASE / "data" / "optics" / "hemisph_sodalime_normal.txt"
REFERENCE = BASE.parent / "validation A" / "data" / "Fig. 3B blue" / "opticalProps-PVcode.txt"

REPORT_DIR = BASE / "report"
FIGURE_DIR = REPORT_DIR / "figures"
DOCS_STATIC = ROOT / "docs" / "site" / "_static" / "validations"

# Seven-column PVcode reference: lambda, emit, emitNorm, ref, refNorm, absSi,
# absSiNorm. Validation A.1 compares the normal-incidence columns.
COL_EMIT_NORM, COL_REF_NORM, COL_ABSSI_NORM = 2, 4, 6

BANDS = [
    {
        "key": "emit_8_13",
        "label": "Emittance 8-13 um",
        "lo": 8.0,
        "hi": 13.0,
        "attr": "emit",
        "ref_col": COL_EMIT_NORM,
    },
    {
        "key": "emit_17_24",
        "label": "Emittance 17-24 um",
        "lo": 17.0,
        "hi": 24.0,
        "attr": "emit",
        "ref_col": COL_EMIT_NORM,
    },
    {
        "key": "emit_4_30",
        "label": "Emittance 4-30 um",
        "lo": 4.0,
        "hi": 30.0,
        "attr": "emit",
        "ref_col": COL_EMIT_NORM,
    },
    {
        "key": "abs_si_0p3_1p12",
        "label": "Si absorptance 0.3-1.12 um",
        "lo": 0.3,
        "hi": 1.12,
        "attr": "abs_silicon",
        "ref_col": COL_ABSSI_NORM,
    },
    {
        "key": "ref_0p3_1p12",
        "label": "Reflectance 0.3-1.12 um",
        "lo": 0.3,
        "hi": 1.12,
        "attr": "ref",
        "ref_col": COL_REF_NORM,
    },
    {
        "key": "ref_1p12_4",
        "label": "Reflectance 1.12-4 um",
        "lo": 1.12,
        "hi": 4.0,
        "attr": "ref",
        "ref_col": COL_REF_NORM,
    },
]

PUBLISHED_TABLE1 = {
    "equilibrium_temperature_K": 319.0,
    "short_circuit_current_A_per_m2": 355.0,
    "mpp_equilibrium_W_per_m2": 222.0,
    "subgap_reflected_power_W_per_m2": 170.0,
    "radiated_power_W_per_m2": 472.0,
    "voc_equilibrium_V": 0.722,
}


def _git_value(repo: Path, *args: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True)
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _s4_provenance() -> Optional[dict]:
    try:
        import S4
    except Exception:
        return None
    module = Path(S4.__file__).resolve()
    source_dir = Path(os.environ.get("S4_SOURCE_DIR", "/home/user/.cache/openclaw/S4"))
    return {
        "module_path": str(module),
        "source_dir": str(source_dir) if source_dir.is_dir() else None,
        "source_commit": (
            _git_value(source_dir, "rev-parse", "HEAD")
            if source_dir.is_dir() else None
        ),
    }


def _style_axes(ax) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, color="#d8dde3", linewidth=0.7, alpha=0.8)
    ax.set_axisbelow(True)


def _save(fig, stem: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        fig.savefig(FIGURE_DIR / f"{stem}.{suffix}", dpi=220, bbox_inches="tight")
    DOCS_STATIC.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIGURE_DIR / f"{stem}.png", DOCS_STATIC / f"validation_a1_{stem}.png")


def _load_live_export():
    if not LIVE_EXPORT.is_file():
        raise FileNotFoundError(
            f"{LIVE_EXPORT} not found. Run this script with --run-live first.")
    cfg = config_module.load(str(OPTICS_YAML))
    atmosphere = cfg.resolve_data(cfg.data.atmosphere)
    return directional.from_reduced_file(str(LIVE_EXPORT), atmosphere, "normal")


def _run_live_export() -> float:
    cfg = config_module.load(str(OPTICS_YAML))
    t0 = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        pipeline.run(cfg)
    return time.time() - t0


def _run_thermal_from_reference():
    cfg = config_module.load(str(PV_YAML))
    optics_path = cfg.resolve_data(cfg.run.optics_results)
    atmosphere = cfg.resolve_data(cfg.data.atmosphere)
    optics = directional.from_reduced_file(
        optics_path, atmosphere, cfg.run.optics_results_angles,
        cfg.run.optics_results_emittance_column)
    solar = load_solar(cfg.resolve_data(cfg.data.solar_spectrum), optics.lambda_um)
    thermal = energy_balance.run(cfg, optics, solar)
    return cfg, optics, solar, thermal


def _band_rows(live_optics, ref_data):
    rows = []
    lam = live_optics.lambda_um
    for band in BANDS:
        computed = band_average(lam, getattr(live_optics, band["attr"]),
                                band["lo"], band["hi"])
        published = band_average(
            lam,
            np.interp(lam, ref_data[:, 0], ref_data[:, band["ref_col"]]),
            band["lo"],
            band["hi"],
        )
        rows.append({
            "key": band["key"],
            "label": band["label"],
            "published": published,
            "computed": computed,
            "diff": computed - published,
            "relative_error_percent": (
                (computed - published) / published * 100.0
                if published else float("nan")
            ),
        })
    return rows


def _emittance_pointwise(live_optics, ref_data):
    lam = live_optics.lambda_um
    ref_emit = np.interp(lam, ref_data[:, 0], ref_data[:, COL_EMIT_NORM])
    out = {}
    for key, lo, hi in [
        ("thermal_4_30um", 4.0, 30.0),
        ("solar_0p3_1p12um", 0.3, 1.12),
    ]:
        mask = (lam >= lo) & (lam <= hi)
        diff = live_optics.emit[mask] - ref_emit[mask]
        out[key] = {
            "rms": float(np.sqrt(np.mean(diff * diff))),
            "max_abs": float(np.max(np.abs(diff))),
        }
    return out


def _table1_rows(thermal, optics, solar):
    lam = optics.lambda_um
    avg = pv_band_averages(
        lam, optics.abs_silicon, optics.ref, optics.emit,
        solar.irradiance_per_um, thermal.equil_temp)
    gp = _find_first(lam, 1.12, 1.2e-2)
    esp = _find_first(lam, 4.0, 1.5e-2)
    reflected_power = None
    if gp is not None and esp is not None:
        reflected_power = float(
            avg.subgap_ref / 100.0
            * trapz(solar.irradiance_per_um[gp:esp + 1], lam[gp:esp + 1])
        )
    values = {
        "equilibrium_temperature_K": thermal.equil_temp,
        "short_circuit_current_A_per_m2": thermal.isc,
        "mpp_equilibrium_W_per_m2": thermal.mpp_equil,
        "subgap_reflected_power_W_per_m2": reflected_power,
        "radiated_power_W_per_m2": thermal.rad_power_equil,
        "voc_equilibrium_V": thermal.voc_equil,
    }
    rows = []
    for key, published in PUBLISHED_TABLE1.items():
        computed = values[key]
        rows.append({
            "key": key,
            "published": published,
            "computed": computed,
            "diff": None if computed is None else computed - published,
            "relative_error_percent": (
                None if computed is None or published == 0
                else (computed - published) / published * 100.0
            ),
        })
    return rows


def _plot_spectral(live_optics, ref_data):
    lam = live_optics.lambda_um
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 8.0), sharex=False)
    published = "#252a32"
    computed = "#1f6fb2"

    axes[0].plot(lam, np.interp(lam, ref_data[:, 0], ref_data[:, COL_EMIT_NORM]),
                 color=published, lw=1.4, label="Published")
    axes[0].plot(lam, live_optics.emit, color=computed, lw=1.2, ls="--",
                 label="radcoolpv S4")
    axes[0].axvspan(8, 13, color="#f0c36a", alpha=0.22, lw=0)
    axes[0].axvspan(17, 24, color="#9bb7d9", alpha=0.20, lw=0)
    axes[0].set_xlim(4, 30)
    axes[0].set_ylim(-0.02, 1.04)
    axes[0].set_ylabel("Emittance")
    axes[0].legend(frameon=False, loc="lower right")

    axes[1].plot(lam, np.interp(lam, ref_data[:, 0], ref_data[:, COL_REF_NORM]),
                 color=published, lw=1.4)
    axes[1].plot(lam, live_optics.ref, color=computed, lw=1.2, ls="--")
    axes[1].axvline(1.12, color="#6b7280", lw=0.9, ls=":")
    axes[1].set_xlim(0.3, 4.0)
    axes[1].set_ylim(-0.02, 1.04)
    axes[1].set_ylabel("Reflectance")

    axes[2].plot(lam, np.interp(lam, ref_data[:, 0], ref_data[:, COL_ABSSI_NORM]),
                 color=published, lw=1.4)
    axes[2].plot(lam, live_optics.abs_silicon, color=computed, lw=1.2, ls="--")
    axes[2].set_xlim(0.3, 1.12)
    axes[2].set_ylim(-0.02, 1.04)
    axes[2].set_ylabel("Si absorptance")
    axes[2].set_xlabel("Wavelength (um)")

    for ax in axes:
        _style_axes(ax)
    fig.suptitle("Validation A.1 normal-incidence spectral comparison", y=0.995)
    fig.tight_layout()
    _save(fig, "spectral_comparison")
    plt.close(fig)


def _plot_band_errors(rows):
    labels = [r["label"] for r in rows]
    err = np.array([r["relative_error_percent"] for r in rows])
    colors = ["#4878a8" if value >= 0 else "#b5654d" for value in err]
    y = np.arange(len(rows))
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.barh(y, err, color=colors, height=0.55)
    ax.axvline(0, color="#252a32", lw=0.9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Relative error (%)")
    _style_axes(ax)
    fig.tight_layout()
    _save(fig, "band_errors")
    plt.close(fig)


def _plot_pv_curves(thermal):
    v = thermal.iv.volt
    current = -thermal.current_equil
    power = thermal.power_equil
    iv_mask = current >= 0.0
    power_mask = power >= 0.0
    v_iv = np.concatenate(([0.0], v[iv_mask]))
    current_iv = np.concatenate(([thermal.isc], current[iv_mask]))
    v_power = np.concatenate(([0.0], v[power_mask]))
    power_pos = np.concatenate(([0.0], power[power_mask]))
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.6))

    axes[0].plot(v_iv, current_iv, color="#1f6fb2", lw=1.7)
    axes[0].axvline(thermal.voc_equil, color="#6b7280", lw=0.9, ls=":")
    axes[0].scatter([0], [thermal.isc], color="#252a32", s=22, zorder=3)
    axes[0].set_xlabel("Voltage (V)")
    axes[0].set_ylabel("Current density (A m$^{-2}$)")
    axes[0].set_xlim(0.0, v.max())
    axes[0].set_ylim(0.0, thermal.isc * 1.08)

    axes[1].plot(v_power, power_pos, color="#b5654d", lw=1.7)
    axes[1].scatter([thermal.vmpp], [thermal.mpp_equil],
                    color="#252a32", s=28, zorder=3)
    axes[1].axvline(thermal.vmpp, color="#6b7280", lw=0.9, ls=":")
    axes[1].set_xlabel("Voltage (V)")
    axes[1].set_ylabel("Power density (W m$^{-2}$)")
    axes[1].set_xlim(0.0, v.max())
    axes[1].set_ylim(0.0, thermal.mpp_equil * 1.18)

    for ax in axes:
        _style_axes(ax)
    fig.tight_layout()
    _save(fig, "pv_curves")
    plt.close(fig)


def _write_summary_md(summary: dict) -> None:
    lines = [
        "# Validation A.1 Report",
        "",
        "Validation A.1 uses the soda-lime hemisphere geometry reported in the "
        "Optics Express paper and compares the rebuilt normal-incidence S4 "
        "optics against the published Fig. 3(b) blue normal-incidence columns. "
        "The thermal/PV stage uses the published hemispherical Fig. 3(b) blue "
        "spectrum to reproduce the Table 1 soda-lime row.",
        "",
        "## Optical Band Averages",
        "",
        "| Band | Published | Computed | Diff | Rel. error |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["optical_band_averages"]:
        lines.append(
            f"| {row['label']} | {row['published']:.4f} | "
            f"{row['computed']:.4f} | {row['diff']:+.4f} | "
            f"{row['relative_error_percent']:+.2f}% |"
        )
    lines.extend([
        "",
        "## Thermal/PV Table 1 Comparison",
        "",
        "| Quantity | Published | Computed | Diff | Rel. error |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for row in summary["table1_comparison"]:
        computed = "n/a" if row["computed"] is None else f"{row['computed']:.6g}"
        diff = "n/a" if row["diff"] is None else f"{row['diff']:+.6g}"
        rel = "n/a" if row["relative_error_percent"] is None else f"{row['relative_error_percent']:+.2f}%"
        lines.append(
            f"| {row['key']} | {row['published']:.6g} | {computed} | "
            f"{diff} | {rel} |"
        )
    lines.extend([
        "",
        "## Figures",
        "",
        "- `figures/spectral_comparison.png`",
        "- `figures/band_errors.png`",
        "- `figures/pv_curves.png`",
    ])
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "summary.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-live", action="store_true",
        help="rerun live S4 normal-incidence optics before reporting")
    args = parser.parse_args()

    if not REFERENCE.is_file():
        raise SystemExit(f"reference spectrum not found: {REFERENCE}")

    live_seconds = None
    if args.run_live or not LIVE_EXPORT.is_file():
        live_seconds = _run_live_export()

    live_optics = _load_live_export()
    ref_data = np.loadtxt(REFERENCE)
    _, pv_optics, solar, thermal = _run_thermal_from_reference()

    optical_rows = _band_rows(live_optics, ref_data)
    summary = {
        "validation": "A.1",
        "description": "Hemispherical soda-lime PV radiative-cooling validation",
        "paths": {
            "live_s4_export": str(LIVE_EXPORT.relative_to(ROOT)),
            "reference_spectrum": str(REFERENCE.relative_to(ROOT)),
            "report_dir": str(REPORT_DIR.relative_to(ROOT)),
        },
        "provenance": {
            "git_commit": _git_value(ROOT, "rev-parse", "HEAD"),
            "git_dirty": bool(_git_value(ROOT, "status", "--porcelain",
                                          "--untracked-files=no", "--", ".")),
            "python": sys.version,
            "s4": _s4_provenance(),
            "live_s4_elapsed_seconds": live_seconds,
        },
        "optical_band_averages": optical_rows,
        "pointwise_emittance_difference": _emittance_pointwise(live_optics, ref_data),
        "thermal_pv": {
            "equilibrium_temperature_K": thermal.equil_temp,
            "vmpp_V": thermal.vmpp,
            "short_circuit_current_A_per_m2": thermal.isc,
            "mpp_equilibrium_W_per_m2": thermal.mpp_equil,
            "voc_equilibrium_V": thermal.voc_equil,
            "fill_factor_equilibrium": thermal.ff_equil,
            "efficiency_equilibrium": thermal.efficiency_equil,
            "radiated_power_W_per_m2": thermal.rad_power_equil,
        },
        "table1_comparison": _table1_rows(thermal, pv_optics, solar),
        "figures": {
            "spectral_comparison": str((FIGURE_DIR / "spectral_comparison.png").relative_to(ROOT)),
            "band_errors": str((FIGURE_DIR / "band_errors.png").relative_to(ROOT)),
            "pv_curves": str((FIGURE_DIR / "pv_curves.png").relative_to(ROOT)),
        },
    }

    _plot_spectral(live_optics, ref_data)
    _plot_band_errors(optical_rows)
    _plot_pv_curves(thermal)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    _write_summary_md(summary)

    print(f"Wrote {REPORT_DIR / 'summary.json'}")
    print(f"Wrote figures in {FIGURE_DIR}")
    print(f"Mirrored PNG figures to {DOCS_STATIC}")


if __name__ == "__main__":
    main()
