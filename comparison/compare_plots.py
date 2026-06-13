"""Build MATLAB vs Python comparison plots for every output of the free-form
energy-balance run. Both used identical settings (manual equilibrium at 319 K,
Vmpp = 0.6586 V), so all curves share the same grids and can be compared
point-by-point.

Outputs (in comparison/plots/):
  optical_properties.png   emittance / reflectance / Si absorptance vs wavelength
  iv_curve.png             current density vs voltage
  power_curve.png          output power vs voltage (equilibrium + ambient)
  energy_balance.png       radiative / atmospheric / convective / cooling / MPP / luminescence vs T
  scalars.png + scalars_comparison.csv   scalar results table (MATLAB, Python, % diff)
"""

import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAT = os.path.join(HERE, "matlab_out")
PY = sorted(glob.glob(os.path.join(HERE, "python_out", "PV-results_*")))[-1]
PLOTS = os.path.join(HERE, "plots")
os.makedirs(PLOTS, exist_ok=True)

MCOL, PCOL = "#1f77b4", "#d62728"   # MATLAB blue, Python red


def load(name):
    return np.loadtxt(os.path.join(MAT, name)), np.loadtxt(os.path.join(PY, name))


def load_scalars(path):
    out = {}
    with open(path) as fh:
        for line in fh:
            k, v = line.split()
            out[k] = float(v)
    return out


def overlay_with_residual(x, m_ys, p_ys, labels, xlabel, ylabel, title, fname,
                          logx=False):
    """Top: MATLAB (solid) vs Python (dashed). Bottom: Python - MATLAB."""
    fig, (ax, axd) = plt.subplots(2, 1, figsize=(8, 6.5), sharex=True,
                                  gridspec_kw={"height_ratios": [3, 1]})
    for my, py, lab in zip(m_ys, p_ys, labels):
        line, = ax.plot(x, my, "-", lw=1.6, label=f"{lab} (MATLAB)")
        ax.plot(x, py, "--", lw=1.4, color=line.get_color(), alpha=0.9,
                label=f"{lab} (Python)")
        axd.plot(x, py - my, lw=1.2, color=line.get_color())
    if logx:
        ax.set_xscale("log"); axd.set_xscale("log")
    ax.set_ylabel(ylabel); ax.set_title(title); ax.legend(frameon=False, fontsize=8, ncol=2)
    axd.axhline(0, color="k", lw=0.6)
    axd.set_xlabel(xlabel); axd.set_ylabel("Python - MATLAB")
    maxabs = max(np.max(np.abs(py - my)) for my, py in zip(m_ys, p_ys))
    axd.text(0.99, 0.05, f"max |diff| = {maxabs:.2e}", transform=axd.transAxes,
             ha="right", va="bottom", fontsize=8)
    fig.tight_layout()
    path = os.path.join(PLOTS, fname)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path, maxabs


def main():
    print(f"MATLAB outputs: {MAT}")
    print(f"Python outputs: {PY}\n")
    summary = []

    # 1) Optical properties: lambda, emit, emitNorm, ref, refNorm, absSi, absSiNorm.
    m, p = load("opticalProps-PVcode.txt")
    lam = m[:, 0]
    _, mx = overlay_with_residual(
        lam, [m[:, 1], m[:, 3], m[:, 5]], [p[:, 1], p[:, 3], p[:, 5]],
        ["Emittance", "Reflectance", "Si absorptance"],
        r"Wavelength ($\mu$m)", "Value", "Optical properties: MATLAB vs Python",
        "optical_properties.png", logx=True)
    summary.append(("optical properties", mx))

    # 2) I-V curve: voltage, current density.
    m, p = load("IV-PVcode.txt")
    _, mx = overlay_with_residual(
        m[:, 0], [m[:, 1]], [p[:, 1]], ["Current density"],
        "Voltage (V)", r"Current density (A/m$^2$)",
        "I-V characteristic: MATLAB vs Python", "iv_curve.png")
    summary.append(("I-V curve", mx))

    # 3) Power curve: voltage, power(equil), power(amb).
    m, p = load("Power-PVcode.txt")
    _, mx = overlay_with_residual(
        m[:, 0], [m[:, 1], m[:, 2]], [p[:, 1], p[:, 2]],
        ["Power (equil. T)", "Power (amb. T)"],
        "Voltage (V)", r"Output power (W/m$^2$)",
        "Output power: MATLAB vs Python", "power_curve.png")
    summary.append(("power curve", mx))

    # 4) Energy-balance terms vs temperature.
    m, p = load("energyBalanceTerms.txt")
    T = m[:, 0]
    labels = [r"$P_{rad}$", r"$P_{atm}$", r"$P_{conv}$", r"$P_{cool}$",
              r"$P_{mpp}$", r"$P_{nonthermal}$"]
    _, mx = overlay_with_residual(
        T, [m[:, i] for i in range(1, 7)], [p[:, i] for i in range(1, 7)], labels,
        "Emitter temperature (K)", r"Power (W/m$^2$)",
        "Energy-balance terms: MATLAB vs Python", "energy_balance.png")
    summary.append(("energy-balance terms", mx))

    # 5) Scalars table.
    ms, ps = load_scalars(os.path.join(MAT, "scalars.txt")), load_scalars(os.path.join(PY, "scalars.txt"))
    keys = list(ms.keys())
    rows, csv_lines = [], ["quantity,matlab,python,abs_diff,pct_diff"]
    for k in keys:
        a, b = ms[k], ps.get(k, float("nan"))
        ad = b - a
        pd = 100.0 * ad / a if a != 0 else float("nan")
        rows.append([k, f"{a:.6g}", f"{b:.6g}", f"{ad:.3g}", f"{pd:.3f}%"])
        csv_lines.append(f"{k},{a:.10g},{b:.10g},{ad:.6g},{pd:.6f}")
    with open(os.path.join(PLOTS, "scalars_comparison.csv"), "w") as fh:
        fh.write("\n".join(csv_lines) + "\n")

    fig, ax = plt.subplots(figsize=(9, 0.5 + 0.4 * len(rows)))
    ax.axis("off")
    tbl = ax.table(cellText=rows,
                   colLabels=["quantity", "MATLAB", "Python", "abs diff", "% diff"],
                   cellLoc="left", loc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(9); tbl.scale(1, 1.3)
    ax.set_title("Scalar results: MATLAB vs Python", pad=12)
    fig.tight_layout()
    fig.savefig(os.path.join(PLOTS, "scalars.png"), dpi=130)
    plt.close(fig)

    print("=== max |Python - MATLAB| per output ===")
    for name, mx in summary:
        print(f"  {name:<24s} {mx:.3e}")
    print("\n=== scalar comparison ===")
    print(f"  {'quantity':<22s} {'MATLAB':>14s} {'Python':>14s} {'% diff':>10s}")
    for r in rows:
        print(f"  {r[0]:<22s} {r[1]:>14s} {r[2]:>14s} {r[4]:>10s}")
    print(f"\nPlots written to: {PLOTS}")


if __name__ == "__main__":
    main()
