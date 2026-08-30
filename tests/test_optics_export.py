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

CONFIGS = os.path.join(os.path.dirname(__file__), "data")
EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")
ATMOSPHERE = os.path.join(os.path.dirname(__file__), "..", "radcoolpv", "data",
                          "cptrans_nq_100_15.dat")


@pytest.fixture
def optics(tmp_path):
    cfg = cm.load(os.path.join(EXAMPLES, "freeform_pv.yaml"))
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
    # The sixth column is the whole point: without it the atmospheric term is
    # rebuilt at the zenith and the resumed balance is not the one exported.
    assert np.allclose(resumed.emitt_spec_times_emit_atm,
                       optics.emitt_spec_times_emit_atm, atol=1e-6)


def test_five_column_files_still_load(optics, tmp_path):
    """Older exports and hand-written HEMSIPH tables must keep working."""
    path = tmp_path / "legacy.txt"
    np.savetxt(path, np.column_stack([optics.lambda_um, optics.ref, optics.tran,
                                      optics.emit, optics.abs_silicon]))

    resumed = directional.from_reduced_file(str(path), ATMOSPHERE, "normal")

    assert np.allclose(resumed.emit, optics.emit, atol=1e-6)
    # No exported product, so the atmospheric term falls back to the zenith
    # approximation rather than silently claiming the angular one.
    assert np.allclose(resumed.emitt_spec_times_emit_atm,
                       resumed.emit_atm * resumed.emit)


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
    cfg = cm.load(os.path.join(EXAMPLES, "freeform_pv.yaml"))
    cfg.run.results_dir = str(tmp_path)
    target = tmp_path / "exported" / "spectrum.txt"
    cfg.run.optics_export = str(target)
    pipeline.run(cfg)
    assert target.is_file()
    assert np.loadtxt(target).shape[1] == 6


def test_export_is_written_even_without_the_results_folder(tmp_path):
    """It is requested by explicit path, so write_outputs must not suppress it."""
    cfg = cm.load(os.path.join(EXAMPLES, "freeform_pv.yaml"))
    cfg.run.results_dir = str(tmp_path)
    cfg.run.write_outputs = False
    target = tmp_path / "spectrum.txt"
    cfg.run.optics_export = str(target)
    ctx = pipeline.run(cfg)
    assert target.is_file()
    assert not os.path.exists(os.path.join(ctx.results_dir, "optics.csv"))


def test_a_resumed_run_does_not_re_export_over_its_own_source(tmp_path):
    """Reading a spectrum and writing it back is never what was wanted.

    The validation cases set optics_export so the case that produces a
    committed spectrum names it. A resumed run of the same case still carries
    that key, and without this guard it overwrites the file it just read --
    with whatever grid the resumed run happened to use.
    """
    cfg = cm.load(os.path.join(EXAMPLES, "freeform_pv.yaml"))
    cfg.run.results_dir = str(tmp_path)
    cfg.run.plots = cfg.run.write_outputs = False
    source = tmp_path / "spectrum.txt"
    cfg.run.optics_export = str(source)
    pipeline.run(cfg)
    original = source.read_bytes()

    resumed = cm.load(os.path.join(EXAMPLES, "freeform_pv.yaml"))
    resumed.run.results_dir = str(tmp_path)
    resumed.run.plots = resumed.run.write_outputs = False
    resumed.run.optics = False
    resumed.run.optics_results = str(source)
    resumed.run.optics_export = str(source)          # still set, as in the YAML
    resumed.simulation.wavelength.n = 50             # a different grid
    pipeline.run(resumed)

    assert source.read_bytes() == original, "the resumed run overwrote its source"
