"""Reporting must never be the thing that refuses to run a valid case.

Two regressions, both found by review rather than by a failing run, and both
sharing a shape: a quantity computed only to be displayed (or not even
displayed) aborted a calculation that was otherwise perfectly well posed.
"""

import io
import contextlib
import json
import os

import pytest

from radcoolpv import config as cm
from radcoolpv import pipeline

CONFIGS = os.path.join(os.path.dirname(__file__), "..", "configs")
VC = os.path.join(os.path.dirname(__file__), "..", "validations", "validation C")


def test_optics_only_stack_without_silicon_can_be_printed():
    """A freestanding cooler has no silicon layer, and that is legal.

    ``Config.thick_si()`` raises when no layer is silicon. The resolved-config
    banner used to call it for every optics run, so this config could be built
    and validated but never executed through the CLI.
    """
    cfg = cm.load(os.path.join(VC, "optics_cooler_planar.yaml"))
    assert not any(l.material == "silicon" for l in cfg.structure)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        pipeline.print_resolved(cfg)
    out = buf.getvalue()
    assert "structure    : 2 layers" in out
    assert "thickSi" not in out          # nothing to report, so nothing claimed


def test_thick_si_still_raises_when_the_thermal_stage_needs_it():
    """The guard above must not weaken the real requirement."""
    cfg = cm.load(os.path.join(VC, "optics_cooler_planar.yaml"))
    with pytest.raises(cm.ConfigError, match="silicon"):
        cfg.thick_si()


def test_voltage_sweep_bracketing_only_the_equilibrium_point_still_runs():
    """Ambient Voc is a diagnostic and must not abort the run.

    Ambient Voc is the largest in the sweep. A range that brackets the
    equilibrium operating point but stops below the ambient one used to raise,
    losing every result for the sake of one diagnostic.
    """
    cfg = cm.load(os.path.join(CONFIGS, "freeform.yaml"))
    cfg.run.plots = False
    cfg.run.write_outputs = False
    with contextlib.redirect_stdout(io.StringIO()):
        full = pipeline.run(cfg).thermal
    assert full.voc_amb > full.voc_equil          # premise of the regression

    cfg2 = cm.load(os.path.join(CONFIGS, "freeform.yaml"))
    cfg2.run.plots = False
    cfg2.run.write_outputs = False
    cfg2.thermal.voltage.max = 0.5 * (full.voc_equil + full.voc_amb)
    with contextlib.redirect_stdout(io.StringIO()):
        narrow = pipeline.run(cfg2).thermal

    assert narrow.equil_temp == pytest.approx(full.equil_temp, abs=0.5)
    # None rather than 0.0: run.json must not present an undetermined Voc as a
    # genuine zero-volt measurement.
    assert narrow.voc_amb is None
    assert narrow.ff_amb is None


def test_run_json_reports_both_ambient_and_equilibrium_operating_points(tmp_path):
    """A reported diagnostic is worth computing; an unreported one is not.

    voc_amb and ff_amb were previously calculated and discarded. They are now in
    the manifest alongside their equilibrium counterparts, so the ambient and
    operating points can be compared without re-running anything.
    """
    cfg = cm.load(os.path.join(CONFIGS, "freeform.yaml"))
    cfg.run.results_dir = str(tmp_path)
    cfg.run.plots = False
    with contextlib.redirect_stdout(io.StringIO()):
        ctx = pipeline.run(cfg)
    block = json.load(open(os.path.join(ctx.results_dir, "run.json")))["thermal_results"]

    for key in ("voc_ambient_V", "voc_equilibrium_V",
                "fill_factor_ambient", "fill_factor_equilibrium"):
        assert key in block, f"run.json is missing {key}"

    # A cell is hotter at equilibrium than at ambient, so it must be the worse
    # operating point on both counts. This also catches the two being swapped.
    assert block["voc_ambient_V"] > block["voc_equilibrium_V"]
    assert block["fill_factor_ambient"] > block["fill_factor_equilibrium"]


def test_undetermined_ambient_voc_is_null_in_run_json(tmp_path):
    cfg = cm.load(os.path.join(CONFIGS, "freeform.yaml"))
    cfg.run.results_dir = str(tmp_path)
    cfg.run.plots = False
    cfg.thermal.voltage.max = 0.74          # brackets equilibrium Voc, not ambient
    with contextlib.redirect_stdout(io.StringIO()):
        ctx = pipeline.run(cfg)
    block = json.load(open(os.path.join(ctx.results_dir, "run.json")))["thermal_results"]
    assert block["voc_ambient_V"] is None
    assert block["fill_factor_ambient"] is None
    assert block["voc_equilibrium_V"] is not None


def test_equilibrium_voc_outside_the_sweep_still_raises():
    """Degrading the diagnostic must not silence the real failure."""
    cfg = cm.load(os.path.join(CONFIGS, "freeform.yaml"))
    cfg.run.plots = False
    cfg.run.write_outputs = False
    cfg.thermal.voltage.max = 0.2                 # below every Voc
    with pytest.raises(ValueError, match="Voc"):
        with contextlib.redirect_stdout(io.StringIO()):
            pipeline.run(cfg)
