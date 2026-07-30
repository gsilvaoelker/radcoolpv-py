"""Validate the S4 RCWA optics backend.

S4 is checked against the analytic transfer-matrix method (`tmm`) for uniform
(flat) stacks - where TMM is exact - across incidence angle and polarisation,
and against energy conservation for patterned stacks.

Tolerances are tight (1e-9) because S4 solves uniform layers exactly: measured
agreement with tmm is ~5e-15. A loose tolerance here would hide real regressions
- it was tightening this bound that exposed the unnormalised-transmission bug
described in `s4_backend._fluxes`.
"""

import numpy as np
import pytest

tmm = pytest.importorskip("tmm")

from radcoolpv import config as config_module
from radcoolpv.materials import registry
from radcoolpv.optics import geometry, s4_backend

pytestmark = pytest.mark.skipif(
    not s4_backend.is_available(), reason="S4 module is not built")

_MATS = {"sio2": "PalikKitamura_SiO2", "silicon": "SiliconNew",
         "substrate": "Hagemann_Ag"}

FLAT_TOL = 1e-9      # S4 is exact for uniform layers
PATTERNED_TOL = 1e-6


def _cfg(photonic="vacuum", shape="flat", cyl=None, grating=None):
    raw = {
        "run": {"optics": True, "thermal": False, "plots": False},
        "simulation": {"wavelength": {"min": 8.0, "max": 10.0, "n": 3},
                       "angles": "normal", "s4_modes": 40},
        "geometry": {"source": "s4", "shape": shape,
                     "photonic_material": photonic,
                     "lattice": {"type": "square", "x": 5.0, "y": 5.0}},
        "structure": [{"material": "sio2", "thickness": 2.0},
                      {"material": "silicon", "thickness": 3.0},
                      {"material": "substrate", "thickness": 0.0, "terminal": True}],
        "materials": _MATS,
        "thermal": {},
    }
    if cyl is not None:
        raw["geometry"]["cylinder"] = cyl
    if grating is not None:
        raw["geometry"]["grating"] = grating
    return config_module.from_dict(raw, base_dir="radcoolpv")


def _tmm_flat(lam_um, theta_deg, pol):
    """R, T, and Si-layer absorptance of vacuum/SiO2(2um)/Si(3um)/Ag via tmm."""
    def nk(model):
        return np.sqrt(registry.get(model)(lam_um))
    n_list = [1.0, nk("PalikKitamura_SiO2"), nk("SiliconNew"), nk("Hagemann_Ag")]
    d_list = [np.inf, 2.0e3, 3.0e3, np.inf]      # nm
    res = tmm.coh_tmm(pol, n_list, d_list, np.deg2rad(theta_deg), lam_um * 1e3)
    a_si = tmm.absorp_in_each_layer(res)[2]      # index 2 == the silicon layer
    return res["R"], res["T"], a_si


LAMBDAS = np.linspace(8.0, 10.0, 3)


def test_flat_normal_matches_tmm():
    raw = s4_backend.sweep(_cfg(), LAMBDAS, np.array([0.0]))
    for i, lam in enumerate(LAMBDAS):
        R, T, a_si = _tmm_flat(lam, 0.0, "s")
        assert raw.ref_te[i, 0] == pytest.approx(R, abs=FLAT_TOL)
        assert raw.tran_te[i, 0] == pytest.approx(T, abs=FLAT_TOL)
        assert raw.abs_te[i, 0] == pytest.approx(1.0 - R - T, abs=FLAT_TOL)
        assert raw.abs_si_te[i, 0] == pytest.approx(a_si, abs=FLAT_TOL)


def test_flat_oblique_te_tm_matches_tmm():
    """Guards the transmission normalisation.

    The incident flux through a z-plane carries cos(theta), so a backend that
    forgets to divide T by it passes at normal incidence and fails here - at 60
    degrees by exactly a factor of two.
    """
    raw = s4_backend.sweep(_cfg(), LAMBDAS, np.array([60.0]))   # non-normal -> TE + TM
    for i, lam in enumerate(LAMBDAS):
        Rte, Tte, _ = _tmm_flat(lam, 60.0, "s")
        Rtm, Ttm, _ = _tmm_flat(lam, 60.0, "p")
        assert raw.ref_te[i, 0] == pytest.approx(Rte, abs=FLAT_TOL)
        assert raw.ref_tm[i, 0] == pytest.approx(Rtm, abs=FLAT_TOL)
        assert raw.tran_te[i, 0] == pytest.approx(Tte, abs=FLAT_TOL)
        assert raw.tran_tm[i, 0] == pytest.approx(Ttm, abs=FLAT_TOL)


def test_pattern_path_reduces_to_flat():
    """An all-vacuum cylinder exercises SetRegionCircle but is physically
    transparent, so it must reproduce the flat tmm result."""
    cfg = _cfg(photonic="vacuum", shape="cylinder",
               cyl={"radius": 1.5, "height": 2.0})
    raw = s4_backend.sweep(cfg, LAMBDAS, np.array([0.0]))
    for i, lam in enumerate(LAMBDAS):
        R, T, _ = _tmm_flat(lam, 0.0, "s")
        assert raw.ref_te[i, 0] == pytest.approx(R, abs=FLAT_TOL)
        assert raw.tran_te[i, 0] == pytest.approx(T, abs=FLAT_TOL)


def test_patterned_energy_conservation():
    """A real SiO2 microcylinder array must conserve energy (R + T + A = 1)."""
    cfg = _cfg(photonic="sio2", shape="cylinder",
               cyl={"radius": 1.5, "height": 2.0})
    raw = s4_backend.sweep(cfg, LAMBDAS, np.array([0.0]))
    total = raw.ref_te[:, 0] + raw.tran_te[:, 0] + raw.abs_te[:, 0]
    assert np.allclose(total, 1.0, atol=PATTERNED_TOL)
    for arr in (raw.ref_te, raw.tran_te, raw.abs_te, raw.abs_si_te):
        assert np.all(arr[:, 0] >= -1e-6)
        assert np.all(arr[:, 0] <= 1.0 + 1e-6)


def test_normal_grating_computes_both_polarizations():
    cfg = _cfg(
        photonic="sio2", shape="grating",
        grating={"duty": 0.3, "depth": 2.0})
    raw = s4_backend.sweep(cfg, LAMBDAS, np.array([0.0]))
    assert raw.ref_te is not None
    assert raw.ref_tm is not None
    assert not np.allclose(raw.ref_te, raw.ref_tm, atol=1e-5)


def test_silicon_absorption_uses_its_own_two_interfaces():
    raw_cfg = {
        "run": {"optics": True, "thermal": False, "plots": False},
        "simulation": {
            "wavelength": {"min": 8.0, "max": 10.0, "n": 3},
            "angles": "normal", "polarization": "TE", "s4_modes": 1,
        },
        "geometry": {
            "source": "s4", "shape": "flat",
            "photonic_material": "vacuum",
        },
        "structure": [
            # Deliberately lossless logical silicon followed by lossy PDMS.
            {"material": "silicon", "thickness": 1.0},
            {"material": "pdms", "thickness": 20.0},
            {"material": "substrate", "thickness": 0.0, "terminal": True},
        ],
        "materials": {
            "silicon": "Vacuum",
            "pdms": "GuptaQuerry_PDMS",
            "substrate": "Hagemann_Ag",
        },
    }
    cfg = config_module.from_dict(raw_cfg, base_dir="radcoolpv")
    raw = s4_backend.sweep(cfg, LAMBDAS)
    assert np.max(raw.abs_te) > 0.1
    assert np.max(np.abs(raw.abs_si_te)) < 1e-8


def test_resolve_eps_is_shared():
    """The backend must map material names through the shared geometry helper."""
    assert s4_backend.resolve_eps is geometry.resolve_eps
    funcs = geometry.resolve_eps(_cfg())
    assert set(funcs) >= {"vacuum", "sio2", "silicon", "substrate"}
    assert np.isclose(funcs["vacuum"](1.0), 1.0)


def test_is_available():
    assert s4_backend.is_available() is True
