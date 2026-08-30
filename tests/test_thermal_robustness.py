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

import contextlib
import io
import os
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


def test_zero_crossing_rejects_unbracketed_high_root():
    x = np.arange(300.0, 350.0)
    y = -50.0 + 0.5 * (x - 300.0)                  # would cross near 400 K
    with pytest.raises(ValueError, match="no zero crossing"):
        _zero_crossing(x, y)


def test_zero_crossing_rejects_unbracketed_low_root():
    x = np.arange(300.0, 350.0)
    y = np.ones_like(x)                            # already non-negative
    with pytest.raises(ValueError, match="already non-negative"):
        _zero_crossing(x, y)


def _load(name):
    from radcoolpv import config as cm
    return cm.load(os.path.join(os.path.dirname(__file__), "data", name))


def test_explicit_sweep_matching_the_default_changes_nothing():
    """thermal.cooling_temperature drives standard mode, and the default is one.

    lambda_g is a weighted mean over the whole swept array, so the sweep is not
    merely a search window: stating the default explicitly must reproduce it
    exactly, or the coupling has been broken.
    """
    from radcoolpv import config as cm, pipeline
    path = os.path.join(os.path.dirname(__file__), "..", "examples", "freeform_pv.yaml")

    def run(sweep):
        cfg = cm.load(path)
        cfg.run.plots = cfg.run.write_outputs = False
        if sweep is not None:
            cfg.thermal.cooling_temperature = cm.TemperatureSweep(**sweep)
        with contextlib.redirect_stdout(io.StringIO()):
            return pipeline.run(cfg).thermal

    t_amb = 298.0
    default = run(None)
    explicit = run({"min": t_amb, "max": t_amb + 150.0, "n": 151})

    assert explicit.equil_temp == pytest.approx(default.equil_temp, abs=1e-9)
    assert explicit.mpp_amb == pytest.approx(default.mpp_amb, abs=1e-9)
    assert explicit.isc == pytest.approx(default.isc, abs=1e-9)
    assert explicit.beta_p == pytest.approx(default.beta_p, abs=1e-9)


def test_standard_mode_sweep_must_contain_ambient():
    """Otherwise the reported 'ambient' operating point is a silent extrapolation."""
    from radcoolpv import config as cm
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "examples", "freeform_pv.yaml")
    cfg = cm.load(cfg_path)
    cfg.thermal.cooling_temperature = cm.TemperatureSweep(min=400.0, max=500.0, n=51)
    with pytest.raises(cm.ConfigError, match="ambient temperature"):
        cm.validate(cfg)


def test_sub_ambient_equilibrium_resolves():
    """A cooler good enough to go below ambient must not fail to report it."""
    from radcoolpv import pipeline
    cfg = _load("cooling_curve.yaml")
    cfg.thermal.absorbed_solar_power = 10.0     # near-perfect solar rejection
    with contextlib.redirect_stdout(io.StringIO()):
        result = pipeline.run(cfg).thermal
    assert result.equil_temp < cfg.thermal.ambient_temperature


def test_equilibrium_outside_the_sweep_names_the_key_that_fixes_it():
    from radcoolpv import pipeline
    cfg = _load("cooling_curve.yaml")
    cfg.thermal.absorbed_solar_power = 10.0
    cfg.thermal.cooling_temperature.min = 340.0     # equilibrium is below this
    with pytest.raises(ValueError, match="thermal.cooling_temperature"):
        with contextlib.redirect_stdout(io.StringIO()):
            pipeline.run(cfg)


def test_a_diode_solve_that_really_fails_raises(monkeypatch):
    """A wrong current must not reach the results as a warning.

    fsolve reports "not making good progress" both when a solve has stalled and
    when it has converged so exactly there is nothing left to improve. Without
    full_output the two are the same warning, and the stalled one still returns
    its answer. _solve_diode judges by the residual instead.
    """
    with pytest.raises(RuntimeError, match="did not converge"):
        pv._solve_diode(lambda x: np.exp(x) + 1.0, 0.0, scale=300.0)   # no root


def test_a_diode_solve_that_is_merely_exact_is_accepted():
    """The residual is what decides, not how many steps MINPACK took."""
    root = pv._solve_diode(lambda x: x - 2.5, 0.0, scale=300.0)
    assert root == pytest.approx(2.5, abs=1e-12)
