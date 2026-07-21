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
    assert raw.n_theta == 18
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
    # emit_atm is MATLAB's *unweighted* angular integral: it maxes at n_theta*dtheta ~ pi/2.
    assert res.emit_atm.min() >= -1e-9
    assert res.emit_atm.max() <= np.pi / 2 + 1e-6


def test_band_averages_match_matlab_log(reduced):
    _, res = reduced
    avg = averages.optical_band_averages(res.lambda_um, res.ref, res.emit, res.abs_silicon)
    # Compare against the values recorded in the MATLAB simulParam.log.
    assert avg.emit_window1 == pytest.approx(71.6497, abs=5e-3)
    assert avg.emit_window2 == pytest.approx(71.2340, abs=5e-3)


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
