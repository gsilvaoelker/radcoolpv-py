"""Parity against the original MATLAB + Lua/S4 toolchain, on a PATTERNED structure.

This is the check nothing else in the suite makes. Validations A and B both
resume from precomputed spectra (`run.optics: false`), and the archived
`comparison/` folder ran both sides free-form - so none of them ever exercised
an optics engine. `test_optics_directional` validates `directional.reduce` by
*reading* MATLAB files, not by running a solver.

The reference in `validation/data/matlab_patterned_ref/` was produced by running
`READS4-*.lua` + `SiO2Spheres-v5.lua` - exactly as MATLAB last wrote them -
through the standalone S4 Lua binary (S4 v1.1.1). The MATLAB tree itself is not
part of this repository, so this committed extract is what keeps the comparison
reproducible.

Case: square 20 x 20 um cell, nModes = 10, theta = 85 deg,
      vacuum / [30 um vacuum + SiO2 circle r = 5 um] / SiO2 100 um /
      Si3N4 0.075 um / Si 250 um / Ag substrate.

Two conventions matter when reading the reference:

* Its T column is **raw flux**, not normalised by the incident flux, because the
  Lua writes `transmission_flux` rather than `transmission_flux_vacuum` (see
  `s4_backend._fluxes`). At 85 degrees that is a factor of ~11.
* Agreement is asserted only over 8-30 um. Below ~8 um the SiO2 is transparent
  and a 10-mode patterned RCWA is far from converged, so the two runs differ by
  up to 0.23 in R there - that is undersampling, not an engine disagreement.
  The 8-30 um window is what the thermal stage integrates over anyway.

The tolerance reflects MATLAB's own numerical floor, not ours: it passes epsilon
to S4 through READS4-PROPS.lua at ~6 significant figures. On the flat quartz
validation that floor is mean 9.0e-4 against analytic TMM, while this package's
S4 backend matches TMM to 5.8e-15.
"""

import os

import numpy as np
import pytest

from radcoolpv import config as config_module
from radcoolpv.optics import s4_backend

pytestmark = pytest.mark.skipif(
    not s4_backend.is_available(), reason="S4 module is not built")

REF_DIR = os.path.join(os.path.dirname(__file__), "..", "radcoolpv",
                       "validation", "data", "matlab_patterned_ref")

BAND = (8.0, 30.0)
MEAN_TOL = 2.0e-3      # MATLAB's epsilon-rounding floor is ~9e-4
MAX_TOL = 1.0e-2


def _cfg(n_lambda):
    return config_module.from_dict({
        "run": {"optics": True, "thermal": False, "plots": False},
        "simulation": {"wavelength": {"min": BAND[0], "max": BAND[1], "n": n_lambda},
                       "angles": "hemispherical", "rcwa_modes": 10},
        "geometry": {"source": "s4", "shape": "cylinder",
                     "photonic_material": "sio2",
                     "lattice": {"type": "square", "x": 20.0, "y": 20.0},
                     "cylinder": {"radius": 5.0, "height": 30.0}},
        "structure": [{"material": "sio2", "thickness": 100.0},
                      {"material": "si3n4", "thickness": 0.075},
                      {"material": "silicon", "thickness": 250.0},
                      {"material": "substrate", "thickness": 0.0, "terminal": True}],
        "materials": {"sio2": "PalikKitamura_SiO2", "si3n4": "DrudeSi3N4",
                      "silicon": "SiliconNew", "substrate": "Hagemann_Ag"},
        "thermal": {},
    }, base_dir="radcoolpv")


@pytest.fixture(scope="module")
def parity():
    te = np.loadtxt(os.path.join(REF_DIR, "OUTPUTS4-TE.txt"))
    tm = np.loadtxt(os.path.join(REF_DIR, "OUTPUTS4-TM.txt"))
    theta = te[0, 0]
    lam = te[:, 1]
    raw = s4_backend.sweep(_cfg(len(lam)), lam, np.array([theta]))
    return te, tm, raw, np.cos(np.deg2rad(theta))


@pytest.mark.parametrize("pol", ["te", "tm"])
def test_reflectance_matches_matlab(parity, pol):
    te, tm, raw, _ = parity
    ref = (te if pol == "te" else tm)[:, 2]
    got = getattr(raw, f"ref_{pol}")[:, 0]
    d = np.abs(got - ref)
    assert d.mean() < MEAN_TOL, f"{pol} mean |dR| = {d.mean():.3e}"
    assert d.max() < MAX_TOL, f"{pol} max |dR| = {d.max():.3e}"


@pytest.mark.parametrize("pol", ["te", "tm"])
def test_transmission_matches_matlab_raw_flux_convention(parity, pol):
    """The reference T column is raw flux; ours is normalised by incident flux."""
    te, tm, raw, cos_t = parity
    ref = (te if pol == "te" else tm)[:, 3]
    got = getattr(raw, f"tran_{pol}")[:, 0]
    assert np.abs(got * cos_t - ref).max() < MEAN_TOL


@pytest.mark.parametrize("pol", ["te", "tm"])
def test_silicon_absorptance_matches_matlab(parity, pol):
    te, tm, raw, _ = parity
    ref = (te if pol == "te" else tm)[:, 5]
    got = getattr(raw, f"abs_si_{pol}")[:, 0]
    assert np.abs(got - ref).max() < MEAN_TOL


def test_reference_covers_the_thermal_window(parity):
    """Guard the fixture itself: the extract must span 8-30 um."""
    te, _, _, _ = parity
    lam = te[:, 1]
    assert lam.min() >= BAND[0] and lam.max() <= BAND[1]
    assert lam.max() - lam.min() > 20.0
    assert len(lam) > 100
