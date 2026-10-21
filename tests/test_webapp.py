"""The browser simulator (webapp/app.py) is radcoolpv, not a re-implementation.

Its "Enfriador radiativo" scenario with the C3 spectrum must land on the pinned
Akerboom C3 result. A literature coating sits on the base module in a single
pass: a clear one changes nothing, and its solar-band T and emit act as they
physically should.
"""

import os
import sys

import numpy as np
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "webapp"))
import app  # noqa: E402

app.DATA = os.path.join(ROOT, "validation", "data")
INPUTS = dict(t_amb_c=26.85, n_cells=60, side_mm=156.75, h=6.0, h_foam=15.0,
              cooler="C3", csv="")


def test_c3_scenario_reproduces_the_pinned_case():
    # Integrate the sun to the unscaled AM1.5G, as the pinned run does.
    out = app.simulate(dict(INPUTS, g=app._load()["sun"].total_am15))
    base, foam, cooler, both = out["rows"]
    assert cooler["t_cell"] + 273.15 == pytest.approx(327.9, abs=0.1)
    assert cooler["eta"] == pytest.approx(17.60, abs=0.01)
    assert base["t_cell"] > cooler["t_cell"] > both["t_cell"]
    assert base["t_cell"] > foam["t_cell"] > both["t_cell"]
    stc = out["stc"]["Base"]
    assert stc["voc_mv"] < 0.0 < stc["isc_ma"]


def _coating(t, e):
    """Simulate under a coating given as T and emit on the base grid."""
    lam = app._load()["base"].lambda_um
    csv = "\n".join(f"{x},{a},{b}" for x, a, b in zip(lam, t(lam), e(lam)))
    out = app.simulate(dict(INPUTS, g=1000.0, cooler="custom", csv=csv))
    return out["rows"], out["stc"]["Base"], out["stc"]["Enfriador radiativo"]


def test_clear_coating_changes_nothing():
    rows, stc_base, stc_coat = _coating(np.ones_like, np.zeros_like)
    assert rows[2]["t_cell"] == pytest.approx(rows[0]["t_cell"], abs=1e-6)
    assert stc_coat["pmp"] == pytest.approx(stc_base["pmp"])


def test_solar_band_reflection_and_absorption():
    subgap = lambda lam: (lam > 1.2) & (lam < 4.0)
    # A sub-gap mirror removes heat without touching the photocurrent ...
    rows, stc_base, stc_coat = _coating(lambda lam: np.where(subgap(lam), 0.0, 1.0), np.zeros_like)
    assert rows[2]["t_cell"] < rows[0]["t_cell"]
    assert stc_coat["isc"] == pytest.approx(stc_base["isc"])
    # ... while parasitic solar absorption heats the module and costs current.
    rows, stc_base, stc_coat = _coating(lambda lam: np.where(lam < 4.0, 0.9, 1.0),
                                        lambda lam: np.where(lam < 4.0, 0.1, 0.0))
    assert rows[2]["t_cell"] > rows[0]["t_cell"]
    assert stc_coat["isc"] == pytest.approx(0.9 * stc_base["isc"])


def test_coating_file_must_have_three_columns_and_cover_the_window():
    base = app._load()["base"]
    with pytest.raises(ValueError):
        app.literature_cooler(base, "0.3,0.5\n20,0.9")
    with pytest.raises(ValueError):
        app.literature_cooler(base, "0.3,0.9,0.05\n10,0.0,0.9")
