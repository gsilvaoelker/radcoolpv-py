"""Validate the pure-Python grcwa optics backend.

The RCWA engine is checked against the analytic transfer-matrix method (`tmm`)
for uniform (flat) stacks - where TMM is exact - across incidence angle and
polarisation, and against energy conservation for patterned stacks. A trivial
(all-vacuum) grid layer is used to prove the patterned/FFT code path reduces to
the correct uniform limit.
"""

import numpy as np
import pytest

grcwa = pytest.importorskip("grcwa")
tmm = pytest.importorskip("tmm")

from radcoolpv import config as config_module
from radcoolpv.materials import registry
from radcoolpv.optics import grcwa_backend as gb

_MATS = {"sio2": "PalikKitamura_SiO2", "silicon": "SiliconNew",
         "substrate": "Hagemann_Ag"}


def _flat_cfg(photonic="vacuum", shape="flat", cyl=None):
    raw = {
        "run": {"optics": True, "thermal": False, "plots": False},
        "simulation": {"wavelength": {"min": 8.0, "max": 10.0, "n": 3},
                       "angles": "normal", "rcwa_modes": 40,
                       "grid_nx": 64, "grid_ny": 64},
        "geometry": {"source": "grcwa", "shape": shape, "photonic_material": photonic,
                     "lattice": {"type": "square", "x": 5.0, "y": 5.0}},
        "structure": [{"material": "sio2", "thickness": 2.0},
                      {"material": "silicon", "thickness": 3.0},
                      {"material": "substrate", "thickness": 0.0, "terminal": True}],
        "materials": _MATS,
        "thermal": {},
    }
    if cyl is not None:
        raw["geometry"]["cylinder"] = cyl
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
    cfg = _flat_cfg()
    raw = gb.sweep(cfg, LAMBDAS, np.array([0.0]))
    for i, lam in enumerate(LAMBDAS):
        R, T, a_si = _tmm_flat(lam, 0.0, "s")
        assert raw.ref_te[i, 0] == pytest.approx(R, abs=3e-3)
        assert raw.tran_te[i, 0] == pytest.approx(T, abs=3e-3)
        assert raw.abs_te[i, 0] == pytest.approx(1.0 - R - T, abs=3e-3)
        assert raw.abs_si_te[i, 0] == pytest.approx(a_si, abs=3e-3)


def test_flat_oblique_te_tm_matches_tmm():
    cfg = _flat_cfg()
    raw = gb.sweep(cfg, LAMBDAS, np.array([60.0]))   # non-normal -> TE + TM
    for i, lam in enumerate(LAMBDAS):
        Rte, Tte, _ = _tmm_flat(lam, 60.0, "s")
        Rtm, Ttm, _ = _tmm_flat(lam, 60.0, "p")
        assert raw.ref_te[i, 0] == pytest.approx(Rte, abs=3e-3)
        assert raw.ref_tm[i, 0] == pytest.approx(Rtm, abs=3e-3)
        assert raw.tran_te[i, 0] == pytest.approx(Tte, abs=3e-3)
        assert raw.tran_tm[i, 0] == pytest.approx(Ttm, abs=3e-3)


def test_grid_path_reduces_to_flat():
    """An all-vacuum cylinder layer exercises Add_LayerGrid/GridLayer_geteps but
    is physically transparent, so it must reproduce the flat tmm result."""
    cfg = _flat_cfg(photonic="vacuum", shape="cylinder",
                    cyl={"radius": 1.5, "height": 2.0})
    raw = gb.sweep(cfg, LAMBDAS, np.array([0.0]))
    for i, lam in enumerate(LAMBDAS):
        R, T, _ = _tmm_flat(lam, 0.0, "s")
        assert raw.ref_te[i, 0] == pytest.approx(R, abs=3e-3)
        assert raw.tran_te[i, 0] == pytest.approx(T, abs=3e-3)


def test_patterned_energy_conservation():
    """A real SiO2 microcylinder array must conserve energy (R + T + A = 1)."""
    cfg = _flat_cfg(photonic="sio2", shape="cylinder",
                    cyl={"radius": 1.5, "height": 2.0})
    raw = gb.sweep(cfg, LAMBDAS, np.array([0.0]))
    total = raw.ref_te[:, 0] + raw.tran_te[:, 0] + raw.abs_te[:, 0]
    assert np.allclose(total, 1.0, atol=1e-4)
    for arr in (raw.ref_te, raw.tran_te, raw.abs_te, raw.abs_si_te):
        assert np.all(arr[:, 0] >= -1e-6)
        assert np.all(arr[:, 0] <= 1.0 + 1e-6)


def test_is_available():
    assert gb.is_available() is True
