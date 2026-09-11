"""Every run writes ``optics.txt``, and ``optics.file`` reads it back exactly.

That is the whole "run the optics once, re-drive the thermal stage from the
spectrum" workflow, so the writer and the reader have to agree on the format.
"""

import os

import numpy as np
import pytest

from radcoolpv import config as cm
from radcoolpv import pipeline
from radcoolpv.optics import directional

EXAMPLES = os.path.join(os.path.dirname(__file__), "..", "examples")
ATMOSPHERE = os.path.join(os.path.dirname(__file__), "..", "radcoolpv", "data",
                          "cptrans_nq_100_15.dat")


@pytest.fixture
def ctx(tmp_path):
    cfg = cm.load(os.path.join(EXAMPLES, "pv_from_spectrum.yaml"))
    return pipeline.run(cfg, results_dir=str(tmp_path), plots=False)


def test_optics_txt_round_trips_through_the_reader(ctx):
    optics = ctx.optics
    resumed = directional.from_file(
        os.path.join(ctx.results_dir, "optics.txt"), ATMOSPHERE)

    assert np.allclose(resumed.lambda_um, optics.lambda_um, rtol=1e-6)
    assert np.allclose(resumed.ref, optics.ref, atol=1e-6)
    assert np.allclose(resumed.emit, optics.emit, atol=1e-6)
    assert np.allclose(resumed.abs_silicon, optics.abs_silicon, atol=1e-6)
    # The sixth column is the whole point: without it the atmospheric term is
    # rebuilt at the zenith and the resumed balance is not the one exported.
    assert np.allclose(resumed.emitt_spec_times_emit_atm,
                       optics.emitt_spec_times_emit_atm, atol=1e-6)


def test_a_run_resumed_from_its_own_optics_txt_reproduces_itself(ctx, tmp_path):
    cfg = cm.from_dict({
        "optics": {"file": os.path.join(ctx.results_dir, "optics.txt")},
        "thermal": {"ambient_temperature": 300.0, "convection_coefficient": 6.0},
        "cell": {"silicon_thickness": 500.0},
    })
    again = pipeline.run(cfg, results_dir=str(tmp_path), plots=False).thermal
    assert again.equil_temp == pytest.approx(ctx.thermal.equil_temp, abs=1e-3)
    assert again.efficiency_equil == pytest.approx(ctx.thermal.efficiency_equil, abs=1e-5)


def test_any_other_table_needs_the_column_named(tmp_path):
    path = tmp_path / "five.txt"
    np.savetxt(path, np.ones((3, 5)))
    with pytest.raises(ValueError, match="optics.column"):
        directional.from_file(str(path), ATMOSPHERE)
