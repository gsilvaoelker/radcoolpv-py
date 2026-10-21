"""The browser simulator (webapp/app.py) is radcoolpv, not a re-implementation.

Its "Enfriador radiativo" scenario with the C3 spectrum must land on the pinned
Akerboom C3 result, and a literature cooler that is just the base spectrum must
reproduce the base scenario.
"""

import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "webapp"))
import app  # noqa: E402

app.DATA = os.path.join(ROOT, "validation", "data")
INPUTS = dict(t_amb_c=26.85, n_cells=60, side_mm=156.75, h=6.0, h_foam=15.0,
              cooler="C3", csv="", tau_solar=1.0)


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


def test_literature_cooler_equal_to_base_changes_nothing():
    base = app._load()["base"]
    csv = "\n".join(f"{x},{e}" for x, e in zip(base.lambda_um, base.emit))
    out = app.simulate(dict(INPUTS, g=1000.0, cooler="custom", csv=csv))
    assert out["rows"][2]["t_cell"] == pytest.approx(out["rows"][0]["t_cell"], abs=1e-6)
    assert out["stc"]["Enfriador radiativo"]["pmp"] == pytest.approx(out["stc"]["Base"]["pmp"])
