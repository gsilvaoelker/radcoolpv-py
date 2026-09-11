"""Band averages on arbitrary grids, and the file reader."""

import os

import numpy as np
import pytest

from radcoolpv.optics import averages, directional

ATMOS = os.path.join(os.path.dirname(__file__), "..", "radcoolpv", "data",
                     "cptrans_nq_100_15.dat")


def test_band_average_integrates_the_exact_band_on_any_grid():
    """The value must not depend on whether a sample lands on an edge."""
    ramp = lambda x: 2.0 + 0.5 * x
    for n in (37, 100, 281, 1000):
        lam = np.linspace(2.0, 16.0, n)
        # Mean of a linear ramp over [8, 13] is its value at the midpoint.
        assert averages.band_average(lam, ramp(lam), 8.0, 13.0) == pytest.approx(
            ramp(10.5), rel=1e-12)


def test_band_outside_the_grid_is_reported_as_missing_not_as_zero():
    lam = np.linspace(2.0, 16.0, 281)
    assert averages.band_average(lam, np.ones_like(lam), 17.0, 24.0) is None


def test_digitized_emittance_column_loads_as_opaque_surface(tmp_path):
    path = tmp_path / "digitized.txt"
    data = np.array([
        [2.0, 0.1, 0.8],
        [16.0, 0.2, 0.9],
    ])
    np.savetxt(path, data)

    res = directional.from_file(str(path), ATMOS, column=2)

    assert np.allclose(res.emit, data[:, 2])
    assert np.allclose(res.ref, 1.0 - data[:, 2])
    assert np.allclose(res.tran, 0.0)
    assert np.allclose(res.abs_silicon, 0.0)


def test_supplied_emittance_becomes_silicon_absorptance_below_the_gap(tmp_path):
    """A single emittance column has to carry the PV stage on its own.

    Above the gap essentially everything absorbed is absorbed in the silicon,
    below it nothing is. Without this the resumed spectrum reports A_Si = 0
    everywhere, Jsc integrates to zero, and the PV result collapses silently.
    """
    path = tmp_path / "digitized.txt"
    lam = np.array([0.4, 0.9, 1.5, 8.0])
    emit = np.array([0.90, 0.85, 0.20, 0.95])
    np.savetxt(path, np.column_stack([lam, emit]))

    res = directional.from_file(str(path), ATMOS, column=1)

    assert res.silicon_from_emittance
    below = lam < averages.LAMBDA_GAP
    assert np.allclose(res.abs_silicon[below], emit[below])
    assert np.allclose(res.abs_silicon[~below], 0.0)
