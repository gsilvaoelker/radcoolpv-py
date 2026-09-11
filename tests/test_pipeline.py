"""End-to-end pipeline test on a stored spectrum (no S4 required)."""

import json
import os

import numpy as np
import pytest

from radcoolpv import config as cm
from radcoolpv import pipeline
from radcoolpv.io import clean_writers
from radcoolpv.optics.directional import RawOptics

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")


@pytest.fixture
def spectrum_ctx(tmp_path):
    cfg = cm.load(os.path.join(EXAMPLES, "pv_from_spectrum.yaml"))
    return pipeline.run(cfg, results_dir=str(tmp_path))


def test_pipeline_runs_and_writes_outputs(spectrum_ctx):
    d = spectrum_ctx.results_dir
    assert os.path.basename(d).startswith("pv_from_spectrum_")
    for name in ("optics.txt", "iv.csv", "power.csv", "run.json"):
        assert os.path.isfile(os.path.join(d, name)), f"missing {name}"
    figs = os.listdir(os.path.join(d, "figures"))
    assert "iv_curve.png" in figs and "power_curve.png" in figs


def test_pipeline_results_are_physical(spectrum_ctx):
    t = spectrum_ctx.thermal
    assert 100 < t.isc < 600                 # A/m^2, ~ a few tens of mA/cm^2
    assert 0.5 < t.voc_equil < 0.8
    assert 0.7 < t.ff_equil < 0.9
    assert 0.10 < t.efficiency_equil < 0.30
    assert -0.6 < t.beta_p < 0.0             # Si temperature coefficient
    assert spectrum_ctx.config.thermal.ambient_temperature <= t.equil_temp <= t.emit_temp[-1]


def test_run_json_has_scalars(spectrum_ctx):
    with open(os.path.join(spectrum_ctx.results_dir, "run.json")) as fh:
        record = json.load(fh)
    assert "thermal_results" in record and "optics" in record
    assert record["resolved_config"]["cell"]["silicon_thickness"] == 500.0
    assert record["provenance"]["inputs"]["config"]["sha256"]
    assert record["provenance"]["inputs"]["spectrum"]["sha256"]


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
