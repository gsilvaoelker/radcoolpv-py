"""Grid-independence and failure signalling in the thermal/PV layer.

The thermal side previously rested entirely on end-to-end regression: the
existing tests check Stefan-Boltzmann, Perrakis Fig. 2 and a full PV run, all of
which pass while individual quantities are quietly quantised to a sampling grid
or clamped to a sweep endpoint. These tests target that behaviour directly.

Three defects motivated them:

* `open_circuit_voltage` returned the last grid point *before* the crossing, so
  Voc inherited the resolution of `thermal.voltage` and was biased low by up to
  one step. Worse, when the sweep did not bracket Voc it returned `volt[-1]` -
  the MAXIMUM voltage - even when the true Voc lay below the sweep minimum.
* Pmpp and Vmpp came from `max()`/`argmax()` over the same grid.
* `_zero_crossing` clamped to a sweep endpoint and returned it as though it were
  a real equilibrium.
"""

import warnings

import numpy as np
import pytest

from radcoolpv.thermal import pv
from radcoolpv.thermal.energy_balance import _zero_crossing

VOLT = np.linspace(0.1, 0.8, 100)      # the default sweep; step = 7.07 mV
STEP = VOLT[1] - VOLT[0]


# --- sub-grid peak refinement ---------------------------------------------

@pytest.mark.parametrize("peak", [0.3011, 0.4523, 0.6237, 0.7104])
def test_refine_peak_recovers_an_exact_parabola(peak):
    y = -(VOLT - peak) ** 2 + 5.0
    x_ref, y_ref = pv.refine_peak(VOLT, y)
    assert x_ref == pytest.approx(peak, abs=1e-9)
    assert y_ref == pytest.approx(5.0, abs=1e-9)


@pytest.mark.parametrize("peak", [0.3011, 0.6237])
def test_refine_peak_beats_the_raw_argmax(peak):
    y = -(VOLT - peak) ** 2 + 5.0
    raw = abs(VOLT[np.argmax(y)] - peak)
    ref = abs(pv.refine_peak(VOLT, y)[0] - peak)
    assert ref < raw / 100.0


def test_refine_peak_is_grid_independent():
    """The whole point: the answer must not depend on how finely we sample."""
    peak = 0.5137
    xs = [np.linspace(0.1, 0.8, n) for n in (40, 100, 400)]
    got = [pv.refine_peak(x, -(x - peak) ** 2 + 5.0)[0] for x in xs]
    assert got == pytest.approx([peak] * 3, abs=1e-9)


def test_refine_peak_falls_back_on_a_boundary_maximum():
    y = np.linspace(0.0, 1.0, len(VOLT))          # maximum at the last sample
    x_ref, y_ref = pv.refine_peak(VOLT, y)
    assert x_ref == pytest.approx(VOLT[-1])
    assert y_ref == pytest.approx(y[-1])


def test_refine_peak_falls_back_on_a_flat_top():
    y = np.zeros_like(VOLT)
    assert pv.refine_peak(VOLT, y)[1] == pytest.approx(0.0)


# --- open-circuit voltage --------------------------------------------------

@pytest.mark.parametrize("true_voc", [0.2534, 0.5011, 0.7234])
def test_open_circuit_voltage_interpolates_the_crossing(true_voc):
    # -J positive below Voc, negative above; smooth through the crossing.
    minus_j = 1.0 - np.exp((VOLT - true_voc) * 40.0)
    got = pv.open_circuit_voltage(-minus_j, VOLT)
    assert got == pytest.approx(true_voc, abs=0.2 * STEP)


def test_open_circuit_voltage_is_grid_independent():
    true_voc = 0.6413
    got = []
    for n in (40, 100, 400):
        v = np.linspace(0.1, 0.8, n)
        got.append(pv.open_circuit_voltage(-(1.0 - np.exp((v - true_voc) * 40.0)), v))
    assert got == pytest.approx([true_voc] * 3, abs=1e-3)


def test_open_circuit_voltage_raises_when_voc_is_above_the_sweep():
    minus_j = np.ones_like(VOLT)                  # never crosses
    with pytest.raises(ValueError, match="above the sweep"):
        pv.open_circuit_voltage(-minus_j, VOLT)


def test_open_circuit_voltage_raises_when_voc_is_below_the_sweep():
    """Used to return volt[-1] - the maximum - for a cell already past Voc."""
    minus_j = -np.ones_like(VOLT)                 # already negative at volt[0]
    with pytest.raises(ValueError, match="below the sweep"):
        pv.open_circuit_voltage(-minus_j, VOLT)


# --- equilibrium temperature ----------------------------------------------

def test_zero_crossing_interpolates():
    x = np.arange(300.0, 350.0)
    y = x - 322.4                                  # crosses at 322.4
    with warnings.catch_warnings():
        warnings.simplefilter("error")             # must NOT warn here
        xc, _ = _zero_crossing(x, y)
    assert xc == pytest.approx(322.4)


def test_zero_crossing_warns_when_it_clamps_high():
    x = np.arange(300.0, 350.0)
    y = -50.0 + 0.5 * (x - 300.0)                  # would cross near 400 K
    with pytest.warns(RuntimeWarning, match="no zero crossing"):
        xc, _ = _zero_crossing(x, y)
    assert xc == pytest.approx(x[-1])


def test_zero_crossing_warns_when_it_clamps_low():
    x = np.arange(300.0, 350.0)
    y = np.ones_like(x)                            # already non-negative
    with pytest.warns(RuntimeWarning, match="already non-negative"):
        xc, _ = _zero_crossing(x, y)
    assert xc == pytest.approx(x[0])
