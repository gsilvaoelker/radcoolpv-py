"""Validation E - Akerboom et al., ACS Photonics 2022, 9, 3831-3840.

Passive radiative cooling of silicon solar modules with silica microcylinders.

This validation exercises BOTH stages of radcoolpv against one paper:

  * Optics  - the S4 RCWA engine computes the normal-incidence band-averaged
              emissivity (7.5-16 um) of the flat and microcylinder module
              glass, compared to the paper's 84.3 % and 97.7 % (Fig. 5a).
  * Thermal - the cooling_curve energy balance solves the equilibrium
              temperature of the idealized bounds (Fig. 2d) and of the three
              real stacks (Fig. 5b), compared to the paper's reported values.

Unlike the earlier archived version, the microcylinder optics are now genuinely
computed by RCWA rather than fitted to the paper's reported emissivity. See the
README for the two documented caveats (RCWA mode-truncation on the circular
Mie resonator, and Ag vs the paper's Au back mirror).

Run from this directory (with the package installed, e.g. ../../install.sh):

    python run_validation.py            # rebuild S4 optics, then validate
    python run_validation.py --no-build # reuse data/optics/s4_*.txt
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from radcoolpv import config as cm            # noqa: E402
from radcoolpv import pipeline                # noqa: E402
from radcoolpv._compat import trapz           # noqa: E402

BAND = (7.5, 16.0)

# (yaml, label, paper T_eq [K]) - idealized emissivity, Fig. 2d
BOUNDS = [
    ("bounds_zero.yaml", "zero IR emissivity (upper bound)", 366.5),
    ("bounds_window.yaml", "8-14 um window only", 341.5),
    ("bounds_ideal.yaml", "ideal 3-30 um absorber (min)", 330.5),
]

# (yaml, label, paper T_eq [K], paper band-avg emissivity [%] or None) - Fig. 5b
STACKS = [
    ("stack_bare.yaml", "Au-Si (bare reference)", 360.0, None),
    ("stack_flat.yaml", "Au-Si-SiO2 (flat glass)", 339.0, 84.3),
    ("stack_cylinders.yaml", "Au-Si-SiO2-cylinders", 336.0, 97.7),
]


def _band_average(lam, emit):
    m = (lam >= BAND[0]) & (lam <= BAND[1])
    return float(trapz(emit[m], lam[m]) / (BAND[1] - BAND[0]))


def _run(yaml_name):
    cfg = cm.load(os.path.join(HERE, yaml_name))
    cfg.run.plots = False
    return pipeline.run(cfg)


def main():
    if "--no-build" not in sys.argv:
        import build_optics_s4
        build_optics_s4.main()
        print()

    print("=" * 72)
    print("Validation E - Akerboom et al., ACS Photonics 2022 (silica microcylinders)")
    print("=" * 72)

    print("\nA. Theoretical bounds (Fig. 2d) - idealized emissivity [thermal engine]")
    print(f"   {'case':<34}{'paper':>8}{'calc':>9}{'err K':>8}")
    print("   " + "-" * 57)
    for yaml_name, label, paper_t in BOUNDS:
        t = _run(yaml_name).thermal.equil_temp
        print(f"   {label:<34}{paper_t:>8.1f}{t:>9.1f}{t - paper_t:>8.1f}")

    print("\nB. Real module stacks (Fig. 5) - S4 optics + cooling-curve thermal")
    print(f"   {'stack':<26}{'emis% paper/calc':>20}{'T_eq K paper/calc/err':>24}")
    print("   " + "-" * 69)
    for yaml_name, label, paper_t, paper_e in STACKS:
        ctx = _run(yaml_name)
        t = ctx.thermal.equil_temp
        avg = _band_average(ctx.optics.lambda_um, ctx.optics.emit) * 100.0
        e = f"{paper_e:>6.1f} /{avg:>6.1f}" if paper_e else f"{'--':>6} /{avg:>6.1f}"
        print(f"   {label:<26}{e:>20}{paper_t:>10.0f} /{t:>6.1f} /{t - paper_t:>5.1f}")

    print("\nSee README.md for the two documented caveats (RCWA mode truncation on "
          "the\nMie-resonant cylinders; Ag vs the paper's Au back mirror).")


if __name__ == "__main__":
    main()
