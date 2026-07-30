"""Literature validation: Zhao et al., Renewable Energy 191 (2022) - Validation C.

Silica micro-grating photonic cooler. Checks both stages against the paper using
the committed S4 optics spectra under ``validations/validation C/data/optics/``:

  * optics  - the grating raises the atmospheric-window (8-13 um) emissivity of
              the silica cooler from the planar wafer's ~0.77 (with silica's 9 um
              reststrahlen dip) to ~0.93, matching the paper's ~0.9 (Fig. 1c);
  * thermal - the grating-silica cell reaches ~37.8 C above ambient under
              800 W/m2, hc = 6 (paper 37.5 C, Fig. 3).

The bare-cell temperature is deliberately NOT asserted tightly: a 200 um Si slab
emits weakly in the mid-IR, so its temperature is set by the silicon optical
model rather than by the grating - see the README. The grating result is robust
because the silica emissivity dominates.
"""
import os

import numpy as np
import pytest

from radcoolpv import config as cm
from radcoolpv import pipeline
from radcoolpv._compat import trapz

VC = os.path.join(os.path.dirname(__file__), "..", "validations", "validation C")
WINDOW = (8.0, 13.0)
T_AMB = 300.0

pytestmark = pytest.mark.skipif(
    not os.path.isdir(os.path.join(VC, "data", "optics")),
    reason="Validation C optics not built")


def _band_average(path):
    d = np.loadtxt(os.path.join(VC, "data", "optics", path))
    lam, emit = d[:, 0], d[:, 3]
    m = (lam >= WINDOW[0]) & (lam <= WINDOW[1])
    return float(trapz(emit[m], lam[m]) / (WINDOW[1] - WINDOW[0]))


def _equil(yaml_name):
    cfg = cm.load(os.path.join(VC, yaml_name))
    cfg.run.plots = False
    cfg.run.write_outputs = False
    return pipeline.run(cfg).thermal.equil_temp


# --- optics: the grating's emissivity enhancement (Fig. 1c) ----------------

def test_grating_window_emissivity_matches_paper():
    avg = _band_average("cooler_grating.txt")
    assert abs(avg - 0.90) < 0.05, f"grating window emissivity {avg:.3f} vs paper ~0.90"


def test_grating_fills_the_planar_reststrahlen_dip():
    """The paper's core photonic result: the grating fills silica's 9 um dip."""
    planar = _band_average("cooler_planar.txt")
    grating = _band_average("cooler_grating.txt")
    assert planar < 0.80                       # planar wafer carries the dip
    assert grating > planar + 0.10             # grating lifts the window average


def test_planar_silica_has_the_nine_micron_dip():
    d = np.loadtxt(os.path.join(VC, "data", "optics", "cooler_planar.txt"))
    lam, emit = d[:, 0], d[:, 3]
    e9 = emit[np.argmin(np.abs(lam - 9.0))]
    assert e9 < 0.45                           # deep reststrahlen reflection dip


# --- thermal: the grating-silica cell temperature (Fig. 3) -----------------

def test_grating_cell_equilibrium_temperature_matches_paper():
    dt = _equil("cell_grating.yaml") - T_AMB
    assert abs(dt - 37.5) < 3.0, f"grating cell {dt:.1f} C above ambient vs paper 37.5"


def test_grating_cools_relative_to_bare():
    """The grating must substantially cool the cell (paper: tens of degrees)."""
    bare = _equil("cell_bare.yaml")
    grating = _equil("cell_grating.yaml")
    assert bare - grating > 30.0
