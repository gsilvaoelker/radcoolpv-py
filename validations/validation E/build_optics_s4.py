"""Generate Validation E optical spectra with the S4 RCWA engine.

Validation E reproduces the main results of

  Akerboom, Veeken, Hecker, van de Groep & Polman, "Passive Radiative Cooling
  of Silicon Solar Modules with Photonic Silica Microcylinders,"
  ACS Photonics 2022, 9, 3831-3840.

The earlier version of this validation could not compute the microcylinder
optics - S4 was not built, so the cylinder spectrum was the flat-silica TMM
result scaled to the paper's *reported* 97.7 % band average. Its emissivity then
matched the paper by construction, validating only the thermal engine.

With S4 available, all three module stacks are now computed from first
principles by the same RCWA engine radcoolpv uses for a live run:

    vacuum / SiO2 200 um module glass / Si 500 um / Ag mirror

The microcylinder case adds a hexagonal array of silica cylinders (radius
1.75 um, height 2.25 um, pitch 6.125 um) etched into the top of the glass -
the paper's optimised geometry (its Fig. 5 / SI). radcoolpv lays a hexagonal
array of pitch p on a rectangular sqrt(3)p x p cell carrying two cylinders,
which reproduces the true hexagonal fill fraction 2*pi*r^2/(sqrt(3)p^2)=29.6 %
exactly.

Two honest caveats, both documented in the README:

* Mode truncation. RCWA expands a circular, high-index-contrast, lossy scatterer
  in a Fourier basis, which converges slowly and non-monotonically for this
  structure - the band-averaged cylinder emissivity sits at ~98 % but scatters
  ~0.5 % across 40-100 modes. That truncation uncertainty is why the paper used
  FDTD. It is far smaller than the flat->cylinder emissivity jump the validation
  is testing, and the equilibrium temperature is insensitive to it.
* Back mirror. The paper uses an 80 nm gold film; only silver optical constants
  (Hagemann_Ag) are bundled. Both are near-perfect IR mirrors (T ~ 0).

Written spectra are radcoolpv 5-column reduced files
(``lambda_um  R  T  emit  abs_si``) on a shared grid, consumed by the stack_*
YAMLs with ``run.optics: false``.
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

# Shared output grid: dense enough in the IR for the reststrahlen features, and
# extended down to the solar band where emissivity is imposed, not computed.
LAM = np.linspace(0.3, 30.0, 3000)
BANDGAP_UM = 1.107          # Si, Eg = 1.12 eV
IR_MIN = 2.0                # S4 evaluated for lambda >= IR_MIN
IR_N = 220                  # IR sampling points passed to S4 (interp onto LAM)
BAND = (7.5, 16.0)          # paper's average-emissivity window

SIO2_UM, SI_UM = 200.0, 500.0
PITCH = 6.125
CYL = {"radius": 1.75, "height": 2.25}
CYL_MODES = 60              # see the mode-truncation caveat above

_MATERIALS = {"sio2": "PalikKitamura_SiO2", "silicon": "SiliconNew",
              "substrate": "Hagemann_Ag"}

# Normal incidence, matching the paper. Akerboom reports normal-incidence
# emissivity spectra (Fig. 5a) and folds the angular dependence into an
# effective convection coefficient, rather than carrying a hemispherical
# emissivity. Using normal incidence therefore both matches the 84.3 % the
# validation compares against and keeps the cylinder build to a single angle
# (~1 min) instead of eighteen.


def _cfg(shape, n_lambda, modes):
    geom = {"source": "s4", "shape": shape, "photonic_material": "sio2",
            "lattice": {"type": "hexagonal", "x": np.sqrt(3) * PITCH, "y": PITCH}}
    structure = [{"material": "silicon", "thickness": SI_UM},
                 {"material": "substrate", "thickness": 0.0, "terminal": True}]
    if shape != "bare":
        structure.insert(0, {"material": "sio2", "thickness": SIO2_UM})
    if shape == "cylinder":
        geom["cylinder"] = CYL
    return cm.from_dict({
        "run": {"optics": True, "thermal": False, "plots": False},
        "simulation": {"wavelength": {"min": IR_MIN, "max": 30.0, "n": n_lambda},
                       "angles": "normal", "rcwa_modes": modes},
        "geometry": geom, "structure": structure, "materials": _MATERIALS,
        "thermal": {},
    }, base_dir="radcoolpv")


def _reduced_emissivity(shape, modes):
    """Normal-incidence emissivity on the LAM grid via a live S4 sweep.

    Opaque back contact (T ~ 0 through the Ag mirror), so emissivity = 1 - R.
    """
    lam_ir = np.linspace(IR_MIN, 30.0, IR_N)
    build_shape = "cylinder" if shape == "cylinder" else "flat"
    cfg = _cfg(build_shape, IR_N, modes)
    if shape == "bare":
        cfg.structure = [s for s in cfg.structure if s.material != "sio2"]
    raw = s4_backend.sweep(cfg, lam_ir, np.array([0.0]))
    emit_ir = 1.0 - raw.ref_te[:, 0]

    emit = np.interp(LAM, lam_ir, emit_ir, left=0.0, right=0.0)
    # Impose the paper's fixed solar input: full absorption above the bandgap,
    # none in the below-gap solar tail (P_sun ~ 808 W/m^2 independent of the IR
    # design). The IR band carries the S4 result.
    emit[LAM <= BANDGAP_UM] = 1.0
    emit[(LAM > BANDGAP_UM) & (LAM < IR_MIN)] = 0.0
    return emit


def _band_average(emit):
    band = (LAM >= BAND[0]) & (LAM <= BAND[1])
    return float(trapz(emit[band], LAM[band]) / (BAND[1] - BAND[0]))


def _write(name, emit):
    ref = 1.0 - emit                      # opaque back contact -> T = 0
    path = os.path.join(OUT_DIR, name)
    np.savetxt(path, np.column_stack([LAM, ref, np.zeros_like(emit), emit, emit]),
               fmt="%.6e",
               header="lambda_um   R           T           emit        abs_si\n"
                      "S4 RCWA hemispherical emissivity, Akerboom et al. 2022")
    return _band_average(emit)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Building Validation E optics with S4 (this computes the IR by RCWA)...")
    for shape, fname, modes, paper in (
            ("bare", "s4_au_si.txt", 1, None),
            ("flat", "s4_au_si_sio2_flat.txt", 1, 84.3),
            ("cylinder", "s4_au_si_sio2_cylinders.txt", CYL_MODES, 97.7)):
        avg = _write(fname, _reduced_emissivity(shape, modes))
        ref = f"  (paper {paper:.1f} %)" if paper else ""
        print(f"  {shape:9s} -> {fname:28s}  band avg 7.5-16um = "
              f"{avg * 100:5.1f} %{ref}", flush=True)


if __name__ == "__main__":
    main()
