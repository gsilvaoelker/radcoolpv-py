"""Validate radcoolpv's live S4 optics against the published spectrum of:

  Silva-Oelker & Jaramillo-Fernandez, "Numerical study of sodalime and PDMS
  hemisphere photonic structures for radiative cooling of silicon solar
  cells," Opt. Express 30(18), 32965 (2022), Fig. 3(c) blue.

WHAT THIS CHECKS
    That a live S4 run of the paper's own PDMS geometry reproduces the paper's
    own optical spectrum. Unlike Validation A -- which reads that spectrum from
    disk and only exercises the thermal/PV stages -- this case computes the
    spectrum from the YAML geometry and compares it against the published one.
    It is therefore the direct test of the optical backend.

WHY THIS ROW AND NOT SODA-LIME
    The paper states the PDMS periodic cell explicitly ("both in a periodic
    cell of (17.3, 10) um"), so nothing about the geometry is guessed. The
    soda-lime pitch is not stated anywhere in the paper, so a live comparison
    of that row would confound code error with an assumed parameter. See
    "validation A.1", which is a smoke test for exactly that reason.

WHAT THIS DOES NOT CHECK
    The comparison is at normal incidence, against the published spectrum's
    normal-incidence columns. It says nothing about the hemispherical average
    that the thermal model consumes, and therefore nothing about Table 1's
    temperatures or PV numbers. The hemispherical recipe is in the README; it
    costs roughly 194 S4 solves per wavelength instead of one.

    The paper states neither its Fourier-mode count nor its dome
    discretisation, so those are not reproduced -- they are established here by
    the convergence table in the README.

This script always exits 0. It reports differences; it does not pass or fail.
"""

from __future__ import annotations

import argparse
import io
import contextlib
import os
import time

import numpy as np

from radcoolpv import config as config_module
from radcoolpv import pipeline
from radcoolpv.optics.averages import band_average

BASE = os.path.dirname(os.path.abspath(__file__))
YAML = os.path.join(BASE, "optics_pdms_hemisph.yaml")

#: Published spectrum for the same structure, bundled with Validation A.
#: Seven-column PVcode form: lambda, emit, emitNorm, ref, refNorm, absSi, absSiNorm.
REFERENCE = os.path.join(
    BASE, os.pardir, "validation A", "data", "Fig. 3C blue",
    "opticalProps-PVcode.txt")

#: Normal-incidence column indices in that file.
COL_EMIT_NORM, COL_REF_NORM, COL_ABSSI_NORM = 2, 4, 6

#: (label, lo_um, hi_um, computed attribute, reference column)
BANDS = [
    ("Emittance 8-13 um (atm. window)", 8.0, 13.0, "emit", COL_EMIT_NORM),
    ("Emittance 17-24 um", 17.0, 24.0, "emit", COL_EMIT_NORM),
    ("Emittance 4-30 um (broadband)", 4.0, 30.0, "emit", COL_EMIT_NORM),
    ("Si absorptance 0.3-1.12 um", 0.3, 1.12, "abs_silicon", COL_ABSSI_NORM),
    ("Reflectance 0.3-1.12 um", 0.3, 1.12, "ref", COL_REF_NORM),
    ("Reflectance 1.12-4 um (sub-gap)", 1.12, 4.0, "ref", COL_REF_NORM),
]


def run_optics(modes: int = None, layers: int = None):
    """Run the live S4 optical stage, returning the OpticsResult."""
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
                    help="override simulation.s4_modes (default: the YAML value)")
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
        print(f"{label:<34}{np.sqrt(np.mean(d ** 2)):>11.4f}{np.abs(d).max():>11.4f}")

    closure = np.abs(optics.ref + optics.tran + optics.emit - 1.0).max()
    print(f"\nEnergy closure, max |R+T+A-1| = {closure:.2e}")
    print("\nDifferences are reported, not asserted.")
    print("The three emittance rows are converged in s4_modes; trust those.")
    print("The solar-band rows are NOT, and cannot cheaply be: at 0.3 um the "
          "10 um pitch is over\nthirty wavelengths wide, and silicon "
          "absorptance moves non-monotonically across\nmodes 30/45/60. Treat "
          "their differences as numerical scatter, not physics. Pointwise\n"
          "solar scatter is further inflated by interference fringes in the "
          "250 um silicon,\nwhich shift with the wavelength grid. See the "
          "convergence table in validations/README.md.")


if __name__ == "__main__":
    main()
