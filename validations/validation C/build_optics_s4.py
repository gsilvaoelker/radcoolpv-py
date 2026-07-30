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

The grating is a genuine S4 computation via radcoolpv's `grating` shape. Both
normal-incidence polarizations are computed; the 20--80-mode window average
varies by less than 0.001.

Four YAML cases generate two spectrum families written as 5-column reduced files
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

WINDOW = (8.0, 13.0)       # atmospheric window
SOLAR_ALPHA = 0.95         # paper's cell solar absorptivity, 0.3-1.1 um (Fig. 2d)
BANDGAP_UM = 1.1           # Si band edge; solar absorptivity imposed below this

# Full output grid: fine in the solar band and the IR reststrahlen features.
LAM = np.concatenate([np.linspace(0.3, 2.0, 340)[:-1], np.linspace(2.0, 30.0, 560)])

def _optics(yaml_name, impose_solar=False):
    """Return normal, unpolarized R/T/A/A_Si from one YAML S4 case.

    For the cell stacks (``impose_solar``) the solar band is fixed to the paper's
    cell absorptivity (~0.95, Fig. 2d). A bare 200 um Si slab without the cell's
    antireflection and texturing absorbs only ~0.5 of AM1.5, which would understate
    the absorbed solar and the cell temperature; imposing the paper's value
    isolates the grating's mid-IR emissivity effect - the paper's actual result -
    from that unrelated front-surface artefact. The cooler-alone spectra
    (Fig. 1c) are left untouched, since there the optics *are* the result.
    """
    cfg = cm.load(os.path.join(HERE, yaml_name))
    raw = s4_backend.sweep(cfg, LAM)
    ref = 0.5 * (raw.ref_te[:, 0] + raw.ref_tm[:, 0])
    tran = 0.5 * (raw.tran_te[:, 0] + raw.tran_tm[:, 0])
    emit = 0.5 * (raw.abs_te[:, 0] + raw.abs_tm[:, 0])
    abs_si = 0.5 * (raw.abs_si_te[:, 0] + raw.abs_si_tm[:, 0])
    if impose_solar:
        solar = LAM <= BANDGAP_UM
        ref[solar] = 1.0 - SOLAR_ALPHA
        tran[solar] = 0.0
        emit[solar] = SOLAR_ALPHA
        abs_si[solar] = SOLAR_ALPHA
    return ref, tran, emit, abs_si


def _band_average(emit):
    m = (LAM >= WINDOW[0]) & (LAM <= WINDOW[1])
    return float(trapz(emit[m], LAM[m]) / (WINDOW[1] - WINDOW[0]))


def _write(name, spectra):
    ref, tran, emit, abs_si = spectra
    np.savetxt(os.path.join(OUT_DIR, name),
               np.column_stack([LAM, ref, tran, emit, abs_si]),
               fmt="%.6e",
               header="lambda_um   R           T           emit        abs_si\n"
                      "S4 normal-incidence unpolarized optics; Zhao et al. 2022")
    return _band_average(emit)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Building Validation C optics with S4...")

    print("\n Cooler alone (Fig. 1c) - freestanding silica emissivity:")
    for yaml_name, fname, lbl in (
            ("optics_cooler_planar.yaml", "cooler_planar.txt", "planar silica"),
            ("optics_cooler_grating.yaml", "cooler_grating.txt", "grating silica")):
        avg = _write(fname, _optics(yaml_name))
        print(f"   {lbl:16s} window avg 8-13um = {avg * 100:5.1f} %", flush=True)

    print("\n Cell stacks (Fig. 3) - 200um Si, solar band fixed to the paper's "
          "alpha~0.95:")
    for yaml_name, fname, lbl in (
            ("optics_cell_bare.yaml", "cell_bare.txt", "bare 200um Si"),
            ("optics_cell_grating.yaml", "cell_grating.txt", "Si + grating silica")):
        avg = _write(fname, _optics(yaml_name, impose_solar=True))
        print(f"   {lbl:20s} window avg 8-13um = {avg * 100:5.1f} %", flush=True)


if __name__ == "__main__":
    main()
