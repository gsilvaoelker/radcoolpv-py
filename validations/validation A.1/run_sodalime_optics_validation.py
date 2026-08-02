"""Validate live S4 optics against the published soda-lime spectrum.

Reference:
  Silva-Oelker & Jaramillo-Fernandez, "Numerical study of sodalime and PDMS
  hemisphere photonic structures for radiative cooling of silicon solar
  cells," Opt. Express 30(18), 32965 (2022), Fig. 3(b) blue.

This compares normal-incidence, unpolarized live S4 output against the
normal-incidence columns in the bundled seven-column PVcode spectrum. Thermal
and PV comparison against Table 1 is handled by ``pv_hemisph_sodalime.yaml``.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import time

import numpy as np

from radcoolpv import config as config_module
from radcoolpv import pipeline
from radcoolpv.optics.averages import band_average

BASE = os.path.dirname(os.path.abspath(__file__))
YAML = os.path.join(BASE, "optics_hemisph_sodalime.yaml")

# Published Fig. 3(b) blue spectrum. Seven-column PVcode form:
# lambda, emit, emitNorm, ref, refNorm, absSi, absSiNorm.
REFERENCE = os.path.join(
    BASE, os.pardir, "validation A", "data", "Fig. 3B blue",
    "opticalProps-PVcode.txt")

COL_EMIT_NORM, COL_REF_NORM, COL_ABSSI_NORM = 2, 4, 6

BANDS = [
    ("Emittance 8-13 um (atm. window)", 8.0, 13.0, "emit", COL_EMIT_NORM),
    ("Emittance 17-24 um", 17.0, 24.0, "emit", COL_EMIT_NORM),
    ("Emittance 4-30 um (broadband)", 4.0, 30.0, "emit", COL_EMIT_NORM),
    ("Si absorptance 0.3-1.12 um", 0.3, 1.12, "abs_silicon", COL_ABSSI_NORM),
    ("Reflectance 0.3-1.12 um", 0.3, 1.12, "ref", COL_REF_NORM),
    ("Reflectance 1.12-4 um (sub-gap)", 1.12, 4.0, "ref", COL_REF_NORM),
]


def run_optics(modes: int = None, layers: int = None):
    cfg = config_module.load(YAML)
    if modes is not None:
        cfg.simulation.s4_modes = modes
    if layers is not None:
        cfg.geometry.discretization_layers = layers
    t0 = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        ctx = pipeline.run(cfg)
    return ctx.optics, cfg.simulation.s4_modes, cfg.geometry.discretization_layers, time.time() - t0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--modes", type=int, default=None,
                    help="override simulation.s4_modes")
    ap.add_argument("--layers", type=int, default=None,
                    help="override geometry.discretization_layers")
    args = ap.parse_args()

    if not os.path.isfile(REFERENCE):
        raise SystemExit(f"reference spectrum not found: {REFERENCE}")

    optics, modes, layers, elapsed = run_optics(args.modes, args.layers)
    ref = np.loadtxt(REFERENCE)
    lam = optics.lambda_um

    print(f"Live S4, normal incidence, unpolarized: s4_modes={modes}, "
          f"discretization_layers={layers}, {len(lam)} wavelengths, {elapsed:.0f} s")
    print(f"Reference: {os.path.relpath(REFERENCE, BASE)} "
          f"(normal-incidence columns)\n")

    print(f"{'Band average':<34}{'Published':>11}{'Computed':>11}"
          f"{'Diff':>10}{'Rel.err %':>11}")
    print("-" * 77)
    for label, lo, hi, attr, col in BANDS:
        computed = band_average(lam, getattr(optics, attr), lo, hi)
        published = band_average(lam, np.interp(lam, ref[:, 0], ref[:, col]), lo, hi)
        rel = (computed - published) / published * 100.0 if published else float("nan")
        print(f"{label:<34}{published:>11.4f}{computed:>11.4f}"
              f"{computed - published:>+10.4f}{rel:>+11.2f}")

    print(f"\n{'Pointwise emittance difference':<34}{'RMS':>11}{'Max':>11}")
    print("-" * 56)
    for label, lo, hi in [("4-30 um (thermal)", 4.0, 30.0),
                          ("0.3-1.12 um (solar)", 0.3, 1.12)]:
        m = (lam >= lo) & (lam <= hi)
        d = optics.emit[m] - np.interp(lam, ref[:, 0], ref[:, COL_EMIT_NORM])[m]
        print(f"{label:<34}{np.sqrt(np.mean(d * d)):>11.4f}"
              f"{np.max(np.abs(d)):>11.4f}")


if __name__ == "__main__":
    main()
