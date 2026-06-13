"""Tests for the thermal stage: radiative term, Perrakis validation, PV sanity."""

import os

import numpy as np
import pytest

from radcoolpv import config as cm
from radcoolpv.io.results import OpticsResult
from radcoolpv.optics import directional
from radcoolpv.thermal import energy_balance
from radcoolpv.thermal.radiative import rad_power
from radcoolpv.thermal.spectra import load_solar

PKG = os.path.join(os.path.dirname(__file__), "..", "radcoolpv")
PKG_DATA = os.path.join(PKG, "data")
VAL_DATA = os.path.join(PKG, "validation", "data")
QUARTZ = os.path.join(VAL_DATA, "quartzValidations-4-30um")
ATMOS = os.path.join(PKG_DATA, "cptrans_nq_100_15.dat")
PERRAKIS = os.path.join(VAL_DATA, "perrakis-h0.dat")
SOLAR = os.path.join(PKG_DATA, "astmg173.xlsx")


@pytest.mark.parametrize("temp", [250.0, 300.0, 350.0])
def test_radiative_matches_stefan_boltzmann(temp):
    lam = np.linspace(0.3, 300.0, 200000)
    p = np.pi * rad_power(lam, np.ones_like(lam), temp)
    sb = 5.670374419e-8 * temp ** 4
    assert p == pytest.approx(sb, rel=2e-3)


def _quartz_cfg(mode):
    return cm.from_dict({
        "run": {"optics": True, "thermal": True, "plots": False, "mode": mode},
        "simulation": {"wavelength": {"min": 4.0, "max": 30.0, "n": 2000},
                       "angles": "hemispherical"},
        "geometry": {"source": "s4", "shape": "flat", "photonic_material": "sio2"},
        "structure": [{"material": "silicon", "thickness": 250.0},
                      {"material": "substrate", "thickness": 0.0, "terminal": True}],
        "materials": {"sio2": "PalikKitamura_SiO2", "silicon": "SiliconNew",
                      "substrate": "Hagemann_Ag"},
        "thermal": {"ambient_temperature": 300.0, "convection_coefficient": 0.0},
    })


def test_perrakis_fig2_cooling_power():
    raw = directional.from_folder(QUARTZ, 2000)
    grid = np.linspace(4.0, 30.0, 2000)
    optics = directional.reduce(raw, ATMOS, lambda_grid=grid)
    solar = load_solar(SOLAR, grid)
    res = energy_balance.run(_quartz_cfg("test"), optics, solar)

    per = np.loadtxt(PERRAKIS)
    in_range = per[:, 0] <= res.emit_temp[-1]
    mine = np.interp(per[in_range, 0], res.emit_temp, res.cool_power)
    # Reference is digitised from the paper figure; agree to ~10 W/m^2.
    assert np.max(np.abs(mine - per[in_range, 1])) < 10.0


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
        "run": {"optics": True, "thermal": True, "plots": False, "mode": "standard"},
        "simulation": {"wavelength": {"min": 0.3, "max": 30.0, "n": 2000}, "angles": "normal"},
        "geometry": {"source": "s4", "shape": "flat", "photonic_material": "sio2"},
        "structure": [{"material": "silicon", "thickness": 250.0},
                      {"material": "substrate", "thickness": 0.0, "terminal": True}],
        "materials": {"sio2": "PalikKitamura_SiO2", "silicon": "SiliconNew",
                      "substrate": "Hagemann_Ag"},
        "thermal": {"ambient_temperature": 298.0, "convection_coefficient": 12.0,
                    "equilibrium": "auto"},
    })
    res = energy_balance.run(cfg, optics, solar)
    assert res.isc > 0
    assert res.mpp_equil > 0
    assert 0.0 < res.voc_equil <= 0.8
    assert 0.0 < res.ff_equil < 1.0
    assert res.emit_temp[0] <= res.equil_temp <= res.emit_temp[-1]
    assert 0.55 < res.vmpp < 0.75
