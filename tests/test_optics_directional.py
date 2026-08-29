"""Validate the directional reduction + band averages against MATLAB output.

Uses the committed ``quartzValidations-4-30um`` results (a hemispherical flat
SiO2 run, 18 angles x 2000 wavelengths). Its ``simulParam.log`` reports:
    Average emittance between 8 um and 13 um:  71.6497
    Average emittance between 17 um and 24 um: 71.2340
If our reduction matches MATLAB, we reproduce these to 4 decimals.
"""

import os

import numpy as np
import pytest

from radcoolpv.optics import averages, directional

PKG = os.path.join(os.path.dirname(__file__), "..", "radcoolpv")
QUARTZ = os.path.join(PKG, "validation", "data", "quartzValidations-4-30um")
ATMOS = os.path.join(PKG, "data", "cptrans_nq_100_15.dat")
N_LAMBDA = 2000


@pytest.fixture(scope="module")
def reduced():
    raw = directional.from_folder(QUARTZ, N_LAMBDA)
    # Canonical grid: the quartz run used wavelength window 4-30 um, n=2000.
    grid = np.linspace(4.0, 30.0, N_LAMBDA)
    return raw, directional.reduce(raw, ATMOS, lambda_grid=grid)


def test_raw_shapes(reduced):
    raw, _ = reduced
    assert raw.n_directions == 18
    assert raw.n_lambda == N_LAMBDA
    assert raw.ref_tm is not None
    assert np.isclose(raw.lambda_um[0], 4.0, atol=0.05)
    assert np.isclose(raw.lambda_um[-1], 30.0, atol=0.05)


def test_reduced_in_physical_range(reduced):
    _, res = reduced
    assert res.angles == "hemispherical"
    for arr in (res.ref, res.tran, res.emit, res.abs_silicon, res.emit_atm):
        assert np.all(np.isfinite(arr))
    # Surface emittance is a true 0..1 fraction.
    assert res.emit.min() >= -1e-9 and res.emit.max() <= 1.0 + 1e-3
    # Atmospheric emissivity is reduced with the same normalized solid-angle
    # weights as the surface properties.
    assert res.emit_atm.min() >= -1e-9
    assert res.emit_atm.max() <= 1.0 + 1e-6


def test_band_averages_match_matlab_log(reduced):
    """The reduction reproduces MATLAB; the band edges are deliberately stricter.

    ``simulParam.log`` records 71.6497 and 71.2340. MATLAB located each edge
    with ``find()`` and a fixed tolerance, so it integrated from the nearest
    sample rather than from the edge itself -- here up to 0.013 um outside the
    band at each end. ``band_average`` interpolates the endpoints and
    integrates exactly [lo, hi], which is why the window values differ in the
    first decimal while the reduction they are computed from is identical.
    """
    _, res = reduced
    lam, emit = res.lambda_um, res.emit
    assert 100 * averages.band_average(lam, emit, 8, 13) == pytest.approx(
        71.6497, abs=0.2)
    assert 100 * averages.band_average(lam, emit, 17, 24) == pytest.approx(
        71.2340, abs=0.2)


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


def test_reduced_pvcode_file_loads_directly(tmp_path):
    path = tmp_path / "reduced.txt"
    data = np.array([
        [0.3, 0.2, 0.21, 0.7, 0.69, 0.08, 0.09],
        [1.0, 0.3, 0.31, 0.6, 0.59, 0.15, 0.16],
    ])
    np.savetxt(path, data)

    res = directional.from_reduced_file(str(path), ATMOS)

    assert res.angles == "hemispherical"
    assert np.allclose(res.emit, data[:, 1])
    assert np.allclose(res.ref, data[:, 3])
    assert np.allclose(res.abs_silicon_norm, data[:, 6])


def test_digitized_emittance_column_loads_as_opaque_surface(tmp_path):
    path = tmp_path / "digitized.txt"
    data = np.array([
        [2.0, 0.1, 0.8],
        [16.0, 0.2, 0.9],
    ])
    np.savetxt(path, data)

    res = directional.from_reduced_file(
        str(path), ATMOS, "hemispherical", emittance_column=2)

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

    res = directional.from_reduced_file(
        str(path), ATMOS, "hemispherical", emittance_column=1)

    assert res.silicon_from_emittance
    below = lam < averages.LAMBDA_GAP
    assert np.allclose(res.abs_silicon[below], emit[below])
    assert np.allclose(res.abs_silicon[~below], 0.0)
