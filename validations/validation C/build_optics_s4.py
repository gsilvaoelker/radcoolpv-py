"""Generate Validation C optical spectra with the S4 RCWA engine.

Validation C reproduces the main results of

  B. Zhao, K. Lu, M. Hu, J. Liu, L. Wu, C. Xu, Q. Xuan, G. Pei,
  "Radiative cooling of solar cells with micro-grating photonic cooler,"
  Renewable Energy 191 (2022) 662-668.

The paper's photonic cooler is a 1-D silica micro-grating etched into a 500 um
fused-silica wafer sitting on the cell:

    period p = 7 um, silica ridge width w = 1.4 um (duty r = w/p = 0.2),
    etch depth d = 10 um.

The grating breaks the flat-interface reflection at silica's 9 um reststrahlen
band - where bulk silica has near-metallic negative permittivity and therefore a
deep emissivity dip - acting as an effective-medium antireflection layer for
thermal emission. This raises the atmospheric-window (8-13 um) emissivity from
the planar wafer's ~0.78 (with the 9 um dip) to ~0.9 (paper Fig. 1c, 2d).

The grating is a genuine RCWA computation via radcoolpv's new `grating` shape;
it is well converged (emissivity flat to <0.003 over 10-120 Fourier modes,
because a 1-D grating only needs modes along the grating vector).

Two spectrum families are written as radcoolpv 5-column reduced files
(``lambda_um  R  T  emit  abs_si``):

* Cooler alone (Fig. 1c): freestanding planar and grating silica, emissivity
  1 - R - T. These validate the optics.
* Cell stacks (Fig. 3 thermal model): the paper's 200 um silicon slab, bare and
  with the grating-silica cooler on top, over the full 0.3-30 um band. The solar
  band carries the S4 solar absorptivity; the IR carries the emissivity. These
  feed the cooling_curve energy balance.

Back mirror: the cell stacks use a silver back contact (Hagemann_Ag), the only
metal in the bundled material set.
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
from radcoolpv._compat import trapz                       # noqa: E402
from radcoolpv.optics import s4_backend                   # noqa: E402

OUT_DIR = os.path.join(HERE, "data", "optics")

# Grating vector along x; y-period is arbitrary for a 1-D grating.
PERIOD = 7.0
DUTY = 0.2                 # silica ridge fraction -> ridge width 1.4 um = paper's w
DEPTH = 10.0
SILICA_UM = 500.0          # wafer thickness (paper)
SI_UM = 200.0              # cell thickness used in the paper's Fig. 3 model
GRATING_MODES = 20         # converged for this 1-D grating (see module docstring)
WINDOW = (8.0, 13.0)       # atmospheric window
SOLAR_ALPHA = 0.95         # paper's cell solar absorptivity, 0.3-1.1 um (Fig. 2d)
BANDGAP_UM = 1.1           # Si band edge; solar absorptivity imposed below this

# Full output grid: fine in the solar band and the IR reststrahlen features.
LAM = np.concatenate([np.linspace(0.3, 2.0, 340)[:-1], np.linspace(2.0, 30.0, 560)])

_MATS = {"sio2": "PalikKitamura_SiO2", "silicon": "SiliconNew",
         "substrate": "Hagemann_Ag", "vacuum": "Vacuum"}


def _cfg(shape, structure, modes, grating=None):
    geom = {"source": "s4", "shape": shape, "photonic_material": "sio2",
            "lattice": {"type": "square", "x": PERIOD, "y": PERIOD}}
    if grating:
        geom["grating"] = grating
    return cm.from_dict({
        "run": {"optics": True, "thermal": False, "plots": False},
        "simulation": {"wavelength": {"min": 0.3, "max": 30.0, "n": len(LAM)},
                       "angles": "normal", "rcwa_modes": modes},
        "geometry": geom, "structure": structure, "materials": _MATS,
        "thermal": {},
    }, base_dir="radcoolpv")


def _emissivity(shape, structure, modes, grating=None, impose_solar=False):
    """Normal-incidence emissivity = 1 - R - T on LAM via a live S4 sweep.

    For the cell stacks (``impose_solar``) the solar band is fixed to the paper's
    cell absorptivity (~0.95, Fig. 2d). A bare 200 um Si slab without the cell's
    antireflection and texturing absorbs only ~0.5 of AM1.5, which would understate
    the absorbed solar and the cell temperature; imposing the paper's value
    isolates the grating's mid-IR emissivity effect - the paper's actual result -
    from that unrelated front-surface artefact. The cooler-alone spectra
    (Fig. 1c) are left untouched, since there the optics *are* the result.
    """
    cfg = _cfg(shape, structure, modes, grating)
    raw = s4_backend.sweep(cfg, LAM, np.array([0.0]))
    emit = 1.0 - raw.ref_te[:, 0] - raw.tran_te[:, 0]
    if impose_solar:
        emit[LAM <= BANDGAP_UM] = SOLAR_ALPHA
    return emit


def _band_average(emit):
    m = (LAM >= WINDOW[0]) & (LAM <= WINDOW[1])
    return float(trapz(emit[m], LAM[m]) / (WINDOW[1] - WINDOW[0]))


def _write(name, emit):
    ref = 1.0 - emit                      # opaque/absorbing stack: report T = 0
    np.savetxt(os.path.join(OUT_DIR, name),
               np.column_stack([LAM, ref, np.zeros_like(emit), emit, emit]),
               fmt="%.6e",
               header="lambda_um   R           T           emit        abs_si\n"
                      "S4 RCWA emissivity, Zhao et al. Renewable Energy 191 (2022)")
    return _band_average(emit)


# Structures --------------------------------------------------------------- #

def _cooler_alone(grating):
    """Freestanding silica cooler (vacuum substrate): Fig. 1c."""
    if grating:
        return [{"material": "sio2", "thickness": SILICA_UM - DEPTH},
                {"material": "vacuum", "thickness": 0.0, "terminal": True}]
    return [{"material": "sio2", "thickness": SILICA_UM},
            {"material": "vacuum", "thickness": 0.0, "terminal": True}]


def _cell_stack(with_cooler):
    """Paper's Fig. 3 model: 200 um Si on Ag, optionally with the grating cooler."""
    stack = [{"material": "silicon", "thickness": SI_UM},
             {"material": "substrate", "thickness": 0.0, "terminal": True}]
    if with_cooler:
        stack.insert(0, {"material": "sio2", "thickness": SILICA_UM - DEPTH})
    return stack


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    grating = {"duty": DUTY, "depth": DEPTH}
    print("Building Validation C optics with S4...")

    print("\n Cooler alone (Fig. 1c) - freestanding silica emissivity:")
    for shape, g, fname, lbl in (
            ("flat", None, "cooler_planar.txt", "planar silica"),
            ("grating", grating, "cooler_grating.txt", "grating silica")):
        avg = _write(fname, _emissivity(shape, _cooler_alone(g), GRATING_MODES, g))
        print(f"   {lbl:16s} window avg 8-13um = {avg * 100:5.1f} %", flush=True)

    print("\n Cell stacks (Fig. 3) - 200um Si, solar band fixed to the paper's "
          "alpha~0.95:")
    for shape, g, fname, lbl in (
            ("flat", None, "cell_bare.txt", "bare 200um Si"),
            ("grating", grating, "cell_grating.txt", "Si + grating silica")):
        avg = _write(fname, _emissivity(shape, _cell_stack(g is not None),
                                        GRATING_MODES, g, impose_solar=True))
        print(f"   {lbl:20s} window avg 8-13um = {avg * 100:5.1f} %", flush=True)


if __name__ == "__main__":
    main()
