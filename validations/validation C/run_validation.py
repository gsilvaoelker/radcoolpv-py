"""Validation C - Zhao et al., Renewable Energy 191 (2022) 662-668.

Radiative cooling of solar cells with a silica micro-grating photonic cooler.

Exercises BOTH radcoolpv stages against the paper:

  * Optics  - the S4 RCWA engine (via the `grating` shape) computes the
              atmospheric-window (8-13 um) emissivity of the planar and grating
              silica cooler. The grating fills silica's 9 um reststrahlen dip,
              raising the window emissivity to ~0.9 (paper Fig. 1c / 2d).
  * Thermal - the cooling_curve energy balance gives the equilibrium
              temperature of the paper's 200 um Si cell, bare and with the
              grating cooler, under 800 W/m2 and hc = 6 W/m2K (paper Fig. 3).

Run from this directory (package installed, e.g. ../../install.sh):

    python run_validation.py            # rebuild S4 optics, then validate
    python run_validation.py --no-build # reuse data/optics/*.txt
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from radcoolpv import config as cm                   # noqa: E402
from radcoolpv import pipeline                       # noqa: E402
from radcoolpv.optics.averages import band_average   # noqa: E402

from build_optics_s4 import WINDOW                   # noqa: E402

T_AMB = 300.0


def _window_emissivity(path):
    d = np.loadtxt(os.path.join(HERE, "data", "optics", path))
    return band_average(d[:, 0], d[:, 3], *WINDOW)


def _equil(yaml_name):
    cfg = cm.load(os.path.join(HERE, yaml_name))
    cfg.run.plots = False
    return pipeline.run(cfg).thermal.equil_temp


def main():
    if "--no-build" not in sys.argv:
        import build_optics_s4
        build_optics_s4.main()
        print()

    print("=" * 66)
    print("Validation C - Zhao et al., Renewable Energy 191 (2022)")
    print("Silica micro-grating photonic cooler for solar cells")
    print("=" * 66)

    print("\nA. Cooler optics (Fig. 1c) - S4 window-averaged emissivity 8-13 um")
    print(f"   {'cooler':<18}{'paper':>8}{'S4':>8}")
    print("   " + "-" * 34)
    for path, label, paper in (("cooler_planar.txt", "planar silica", None),
                               ("cooler_grating.txt", "grating silica", 0.90)):
        avg = _window_emissivity(path)
        p = f"{paper * 100:>7.0f}%" if paper else f"{'(dip)':>8}"
        print(f"   {label:<18}{p}{avg * 100:>7.0f}%")

    print("\nB. Cell temperature (Fig. 3) - cooling_curve, 800 W/m2, hc=6, Ta=300K")
    print(f"   {'cell':<22}{'paper dT':>10}{'calc dT':>10}")
    print("   " + "-" * 42)
    for yaml_name, label, paper_dt in (("cell_bare.yaml", "bare 200um Si", 77.5),
                                       ("cell_grating.yaml", "+ grating cooler", 37.5)):
        dt = _equil(yaml_name) - T_AMB
        print(f"   {label:<22}{paper_dt:>9.1f}C{dt:>9.1f}C")

    print("\nSee ../README.md: the grating temperature agrees within 1 K only under")
    print("the prescribed-solar and angle-independent-optics approximations.")


if __name__ == "__main__":
    main()
