"""Validation A.1, step 1: run the live S4 optics and write the spectrum.

Solves ``optics_hemisph_sodalime.yaml`` (TE, normal incidence, hexagonal cell
with a discretised semisphere) and writes the reduced five-column file that
step 2 consumes:

    lambda_um   R   T   emit   abs_si

The intermediate file exists because ``optics.csv`` from a normal CLI run is a
nine-column comma-separated table with a text header, which the resume reader
(``run.optics_results``) does not accept; it reads whitespace-separated five- or
seven-column tables. This mirrors Validation C's build/consume split.

Run from anywhere:

    python "validations/validation A.1/build_optics.py"
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from radcoolpv import config as cm                       # noqa: E402
from radcoolpv.optics import s4_backend                  # noqa: E402
from radcoolpv.optics.averages import band_average       # noqa: E402

CASE = "optics_hemisph_sodalime.yaml"
OUT = os.path.join(HERE, "data", "optics", "hemisph_sodalime_te_normal.txt")
WINDOW = (8.0, 13.0)          # atmospheric window
SOLAR_BAND = (0.3, 1.1)       # silicon absorbing band


def main() -> None:
    cfg = cm.load(os.path.join(HERE, CASE))
    lam = cfg.wavelength_array()

    print(f"Validation A.1 - live S4: {len(lam)} wavelengths, "
          f"{cfg.simulation.polarization} at normal incidence")
    print(f"  cell      : {cfg.geometry.lattice.type} "
          f"x={cfg.geometry.lattice.x} y={cfg.geometry.lattice.y} um")
    print(f"  shape     : {cfg.geometry.shape}, radius "
          f"{cfg.geometry.sphere['radius']} um, "
          f"{cfg.geometry.discretization_layers} slices")

    raw = s4_backend.sweep(cfg, lam)
    # TE only: the TM arrays are None, so take the single requested polarization.
    ref, tran = raw.ref_te[:, 0], raw.tran_te[:, 0]
    emit, abs_si = raw.abs_te[:, 0], raw.abs_si_te[:, 0]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    np.savetxt(OUT, np.column_stack([lam, ref, tran, emit, abs_si]),
               fmt="%.6e",
               header="lambda_um   R           T           emit        abs_si\n"
                      "S4 TE normal-incidence optics; hexagonal semisphere "
                      "smoke test (not a literature validation)")

    energy = np.abs(ref + tran + emit - 1.0).max()
    print(f"\n  written   : {os.path.relpath(OUT, REPO)}")
    print(f"  max |R+T+A-1| = {energy:.2e}   (energy conservation)")
    print(f"  solar-band  absorptance in Si = "
          f"{band_average(lam, abs_si, *SOLAR_BAND):.3f}")
    print(f"  8-13 um window emittance      = "
          f"{band_average(lam, emit, *WINDOW):.3f}")


if __name__ == "__main__":
    main()
