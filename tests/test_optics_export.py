"""``run.optics_export`` must produce a file ``run.optics_results`` can read.

The two settings are the write and read halves of the documented "run the optics
once, re-drive the thermal stage from the spectrum" workflow, so they have to
agree on the format. ``optics.csv`` deliberately does not: it is comma-separated
with a text header, which the resume reader rejects. That asymmetry is asserted
here so the export is not quietly replaced by the CSV writer later.
"""

import os

import numpy as np
import pytest

from radcoolpv import config as cm
from radcoolpv import pipeline
from radcoolpv.io import clean_writers
from radcoolpv.optics import directional

CONFIGS = os.path.join(os.path.dirname(__file__), "..", "configs")
ATMOSPHERE = os.path.join(os.path.dirname(__file__), "..", "radcoolpv", "data",
                          "cptrans_nq_100_15.dat")


@pytest.fixture
def optics(tmp_path):
    cfg = cm.load(os.path.join(CONFIGS, "freeform.yaml"))
    cfg.run.results_dir = str(tmp_path)
    return pipeline.run(cfg).optics


def test_export_round_trips_through_the_resume_reader(optics, tmp_path):
    path = str(tmp_path / "spectrum.txt")
    clean_writers.write_optics_export(path, optics)

    resumed = directional.from_reduced_file(path, ATMOSPHERE, "normal")

    assert np.allclose(resumed.lambda_um, optics.lambda_um, rtol=1e-6)
    assert np.allclose(resumed.ref, optics.ref, atol=1e-6)
    assert np.allclose(resumed.emit, optics.emit, atol=1e-6)
    assert np.allclose(resumed.abs_silicon, optics.abs_silicon, atol=1e-6)


def test_export_creates_missing_parent_directories(optics, tmp_path):
    path = str(tmp_path / "nested" / "deeper" / "spectrum.txt")
    clean_writers.write_optics_export(path, optics)
    assert os.path.isfile(path)


def test_optics_csv_is_not_resumable(optics, tmp_path):
    """Why the export exists: the CSV cannot stand in for it."""
    clean_writers.write_optics_csv(str(tmp_path), optics)
    with pytest.raises(ValueError):
        directional.from_reduced_file(
            str(tmp_path / "optics.csv"), ATMOSPHERE, "normal")


def test_pipeline_writes_the_export_when_configured(tmp_path):
    cfg = cm.load(os.path.join(CONFIGS, "freeform.yaml"))
    cfg.run.results_dir = str(tmp_path)
    target = tmp_path / "exported" / "spectrum.txt"
    cfg.run.optics_export = str(target)
    pipeline.run(cfg)
    assert target.is_file()
    assert np.loadtxt(target).shape[1] == 5


def test_export_is_written_even_without_the_results_folder(tmp_path):
    """It is requested by explicit path, so write_outputs must not suppress it."""
    cfg = cm.load(os.path.join(CONFIGS, "freeform.yaml"))
    cfg.run.results_dir = str(tmp_path)
    cfg.run.write_outputs = False
    target = tmp_path / "spectrum.txt"
    cfg.run.optics_export = str(target)
    ctx = pipeline.run(cfg)
    assert target.is_file()
    assert not os.path.exists(os.path.join(ctx.results_dir, "optics.csv"))
