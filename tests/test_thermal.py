"""Tests for the thermal stage: radiative term, PV sanity, cooling curve."""

import os

import numpy as np
import pytest

from radcoolpv import config as cm
from radcoolpv._compat import trapz
from radcoolpv.io.results import OpticsResult
from radcoolpv.thermal import energy_balance
from radcoolpv.thermal.radiative import rad_power
from radcoolpv.thermal.spectra import load_solar

PKG_DATA = os.path.join(os.path.dirname(__file__), "..", "radcoolpv", "data")
ATMOS = os.path.join(PKG_DATA, "cptrans_nq_100_15.dat")
SOLAR = os.path.join(PKG_DATA, "astmg173.xlsx")

_STACK = {
    "wavelength": {"min": 0.3, "max": 30.0, "n": 2000}, "angles": "hemispherical",
    "structure": [{"material": "silicon", "thickness": 250.0}],
    "substrate": "substrate",
    "materials": {"silicon": "SiliconNew", "substrate": "Hagemann_Ag"},
}


@pytest.mark.parametrize("temp", [250.0, 300.0, 350.0])
def test_radiative_matches_stefan_boltzmann(temp):
    lam = np.linspace(0.3, 300.0, 200000)
    p = np.pi * rad_power(lam, np.ones_like(lam), temp)
    sb = 5.670374419e-8 * temp ** 4
    assert p == pytest.approx(sb, rel=2e-3)


def _synthetic_optics(grid, atmosphere_path):
    """A simple absorber: Si absorbs in the visible, modest broadband emittance."""
    abs_si = np.where(grid < 1.1, 0.9, 0.0)
    emit = np.full_like(grid, 0.5)
    ref = 1.0 - emit
    from radcoolpv.thermal.spectra import load_atmosphere
    atm = load_atmosphere(atmosphere_path, grid)
    emit_atm = 1.0 - atm
    return OpticsResult(
        lambda_um=grid, ref=ref, tran=np.zeros_like(grid), emit=emit,
        abs_silicon=abs_si, emit_atm=emit_atm, emitt_spec_times_emit_atm=emit_atm * emit,
        angles="normal",
    )


def test_pv_path_is_sane_and_fixed_point_converges():
    grid = np.linspace(0.3, 30.0, 2000)
    optics = _synthetic_optics(grid, ATMOS)
    solar = load_solar(SOLAR, grid)
    cfg = cm.from_dict({
        "optics": _STACK,
        "thermal": {"ambient_temperature": 298.0, "convection_coefficient": 12.0},
        "cell": {},
    })
    res = energy_balance.run(cfg, optics, solar)
    assert res.isc > 0
    assert res.mpp_equil > 0
    assert 0.0 < res.voc_equil <= 0.8
    assert 0.0 < res.ff_equil < 1.0
    assert res.emit_temp[0] <= res.equil_temp <= res.emit_temp[-1]
    assert 0.55 < res.vmpp < 0.75
    assert res.rad_power_equil == pytest.approx(
        np.interp(res.equil_temp, res.emit_temp, res.rad_power))
    assert np.allclose(
        res.power_equil,
        [np.interp(res.equil_temp, res.emit_temp, row) for row in res.iv.cell_power],
    )


def test_without_a_cell_the_configured_temperature_sweep_drives_the_curve():
    grid = np.linspace(0.3, 30.0, 2000)
    optics = _synthetic_optics(grid, ATMOS)
    solar = load_solar(SOLAR, grid)
    cfg = cm.from_dict({
        "optics": _STACK,
        "thermal": {"ambient_temperature": 298.0, "convection_coefficient": 9.0,
                    "reference_temperature": 350.0,
                    "temperatures": {"min": 310.0, "max": 360.0, "n": 101}},
    })

    res = energy_balance.run(cfg, optics, solar)

    assert res.iv is None
    assert res.emit_temp[0] == pytest.approx(310.0)
    assert res.emit_temp[-1] == pytest.approx(360.0)
    assert len(res.cool_power) == 101
    assert res.temperature_reduction == pytest.approx(350.0 - res.equil_temp)
    assert res.solar_power == pytest.approx(
        trapz(optics.emit * solar.irradiance_per_um, grid))


def test_absorbed_solar_power_replaces_the_am15_integral():
    grid = np.linspace(2.0, 16.0, 281)
    optics = _synthetic_optics(grid, ATMOS)
    solar = load_solar(SOLAR, grid)
    cfg = cm.from_dict({
        "optics": {"file": "unused.txt", "column": 1},
        "thermal": {
            "ambient_temperature": 300.0,
            "convection_coefficient": 12.0,
            "absorbed_solar_power": 808.0,
            "temperatures": {"min": 260.0, "max": 380.0, "n": 121},
        },
    })

    res = energy_balance.run(cfg, optics, solar)

    assert res.solar_power == pytest.approx(808.0)
