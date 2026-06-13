"""End-to-end pipeline test using the free-form config (no S4 required)."""

import json
import os

import pytest

from radcoolpv import config as cm
from radcoolpv import pipeline

CONFIGS = os.path.join(os.path.dirname(__file__), "..", "configs")


@pytest.fixture
def freeform_ctx(tmp_path):
    cfg = cm.load(os.path.join(CONFIGS, "freeform.yaml"))
    cfg.run.results_dir = str(tmp_path)
    return pipeline.run(cfg)


def test_pipeline_runs_and_writes_outputs(freeform_ctx):
    ctx = freeform_ctx
    d = ctx.results_dir
    # legacy + clean files present.
    for name in ("opticalProps-PVcode.txt", "IV-PVcode.txt", "Power-PVcode.txt",
                 "simulParam.log", "simulParamPV.log",
                 "optics.csv", "iv.csv", "power.csv", "run.json"):
        assert os.path.isfile(os.path.join(d, name)), f"missing {name}"
    # figures present.
    figs = os.listdir(os.path.join(d, "figures"))
    assert "iv_curve.png" in figs and "power_curve.png" in figs


def test_pipeline_results_are_physical(freeform_ctx):
    t = freeform_ctx.thermal
    assert 100 < t.isc < 600                 # A/m^2, ~ a few tens of mA/cm^2
    assert 0.5 < t.voc_equil < 0.8
    assert 0.7 < t.ff_equil < 0.9
    assert 0.10 < t.efficiency_equil < 0.30
    assert -0.6 < t.beta_p < 0.0             # Si temperature coefficient
    assert freeform_ctx.config.thermal.ambient_temperature <= t.equil_temp <= t.emit_temp[-1]


def test_run_json_has_scalars(freeform_ctx):
    with open(os.path.join(freeform_ctx.results_dir, "run.json")) as fh:
        record = json.load(fh)
    assert "thermal" in record and "optics" in record
    assert record["thermal"]["equilibrium_mode"] == "auto"
