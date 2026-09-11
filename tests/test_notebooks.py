"""The notebook is the interface students actually use.

Every YAML it writes is a real case against the current schema, so a schema
change that breaks one must fail here rather than in a classroom. The cases
that need no solver are also run, end to end.
"""

import contextlib
import io
import json
import os

import pytest

from radcoolpv import config as cm
from radcoolpv import pipeline

ROOT = os.path.join(os.path.dirname(__file__), "..")
NOTEBOOK = os.path.join(ROOT, "radcoolpv.ipynb")


def _cells(kind):
    return ["".join(c["source"]) for c in json.load(open(NOTEBOOK))["cells"]
            if c["cell_type"] == kind]


def _written_yaml():
    """Every ``%%writefile <name>.yaml`` cell as {name: body}."""
    out = {}
    for source in _cells("code"):
        head, _, body = source.partition("\n")
        if head.startswith("%%writefile ") and head.endswith(".yaml"):
            out[head.split()[1]] = body
    return out


def test_the_notebook_writes_the_three_cases():
    assert set(_written_yaml()) == {"case_a.yaml", "case_measured.yaml", "case_b.yaml"}


@pytest.mark.parametrize("name", ["case_a.yaml", "case_measured.yaml", "case_b.yaml"])
def test_every_editable_yaml_validates(name, tmp_path):
    target = tmp_path / name
    target.write_text(_written_yaml()[name])
    cfg = cm.load(str(target))
    cfg.base_dir = ROOT          # the notebook runs from the repository root
    if cfg.optics.file is not None:
        assert os.path.isfile(cfg.resolve_data(cfg.optics.file))


@pytest.mark.parametrize("name,temperature", [("case_a.yaml", 327.0),
                                              ("case_measured.yaml", 337.5)])
def test_the_solver_free_cases_run_and_land_on_the_paper(name, temperature, tmp_path):
    target = tmp_path / name
    target.write_text(_written_yaml()[name])
    cfg = cm.load(str(target))
    cfg.base_dir = ROOT
    with contextlib.redirect_stdout(io.StringIO()):
        result = pipeline.run(cfg, results_dir=str(tmp_path), plots=False).thermal
    assert result.equil_temp == pytest.approx(temperature, abs=0.1)


def test_every_case_is_run_through_the_shared_reporter():
    """Three private copies of the reporting code is how they drift apart."""
    runs = [c for c in _cells("code") if "pipeline.run(" in c]
    assert len(runs) == 3
    for cell in runs:
        assert 'report.summary(pipeline.run(config.load("case_' in cell


def test_run_all_never_waits_for_input():
    """Runtime -> Run all has to finish on its own: no file picker, no prompt."""
    for cell in _cells("code"):
        assert "files.upload" not in cell
        assert "input(" not in cell


def test_case_b_is_the_shipped_validation_case_on_a_reduced_grid(tmp_path):
    """Same physics as the shipped case; only the numerical grid is cheaper.

    The notebook says so, and quotes its own reduced-grid numbers rather than
    the converged table, so the grid must be the only thing that differs.
    """
    target = tmp_path / "case_b.yaml"
    target.write_text(_written_yaml()["case_b.yaml"])
    written = cm.load(str(target))
    shipped = {c.case_name: c for c in cm.load_cases(
        os.path.join(ROOT, "validation", "akerboom.yaml"))}["C3_pv_cylinders"]
    for cfg in (written, shipped):
        cfg.optics.wavelength.n = cfg.optics.hemisphere_theta_points = cfg.optics.s4_modes = 0
    assert written.optics == shipped.optics
    assert written.thermal == shipped.thermal
    assert written.cell == shipped.cell


def test_case_a_reads_the_spectrum_case_b_computes(tmp_path):
    target = tmp_path / "case_a.yaml"
    target.write_text(_written_yaml()["case_a.yaml"])
    written = cm.load(str(target))
    assert written.optics.file.endswith("C3_pv_cylinders.txt")
    assert written.optics.column is None
