"""End-to-end pipeline test using the free-form config (no S4 required)."""

import json
import os

import numpy as np
import pytest

from radcoolpv import config as cm
from radcoolpv import pipeline
from radcoolpv.io import clean_writers
from radcoolpv.optics.directional import RawOptics

CONFIGS = os.path.join(os.path.dirname(__file__), "..", "configs")


@pytest.fixture
def freeform_ctx(tmp_path):
    cfg = cm.load(os.path.join(CONFIGS, "freeform.yaml"))
    cfg.run.results_dir = str(tmp_path)
    return pipeline.run(cfg)


def test_pipeline_runs_and_writes_outputs(freeform_ctx):
    ctx = freeform_ctx
    d = ctx.results_dir
    for name in ("optics.csv", "iv.csv", "power.csv", "run.json"):
        assert os.path.isfile(os.path.join(d, name)), f"missing {name}"
    for legacy in ("opticalProps-PVcode.txt", "IV-PVcode.txt",
                   "Power-PVcode.txt", "simulParam.log", "simulParamPV.log"):
        assert not os.path.exists(os.path.join(d, legacy))
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
    assert "thermal_results" in record and "optics" in record
    assert record["resolved_config"]["thermal"]["equilibrium"] == "auto"
    assert record["provenance"]["inputs"]["config"]["sha256"]


def test_directional_csv_preserves_geometry_and_polarization(tmp_path):
    raw = RawOptics(
        theta_deg=np.array([0.0, 35.0]),
        phi_deg=np.array([0.0, 90.0]),
        direction_weight=np.array([0.0, 1.0]),
        lambda_um=np.array([8.0]),
        ref_te=np.array([[0.1, 0.2]]),
        tran_te=np.array([[0.3, 0.4]]),
        abs_te=np.array([[0.6, 0.4]]),
        abs_si_te=np.array([[0.5, 0.3]]),
        mode="hemispherical",
        polarization="TE",
    )

    clean_writers.write_directional_csv(str(tmp_path), raw)

    rows = (tmp_path / "optics_directional.csv").read_text().splitlines()
    assert rows[0].split(",")[:5] == [
        "lambda_um", "polar_angle_deg", "azimuth_angle_deg",
        "polarization", "angular_weight",
    ]
    assert rows[2].split(",")[1:5] == ["35", "90", "TE", "1"]


def test_spectral_compare_mode_writes_overlay(tmp_path):
    np.savetxt(tmp_path / "bare.txt", [[2.5, 0.9], [14.0, 0.9]])
    cfg = cm.from_dict({
        "run": {"optics": False, "thermal": False, "plots": True,
                "mode": "spectral_compare", "results_dir": str(tmp_path / "results")},
        "comparison": {"spectra": [{"label": "Bare", "file": "bare.txt", "color": "#ff7f0e"}]},
    }, base_dir=str(tmp_path))

    ctx = pipeline.run(cfg)

    assert os.path.isfile(os.path.join(ctx.results_dir, "figures", "spectral_comparison.png"))
