"""Tests for geometry construction, free-form input, and the S4 backend guard."""

import os

import numpy as np
import pytest

from radcoolpv import config as config_module
from radcoolpv.optics import freeform, geometry, s4_backend

PKG_DATA = os.path.join(os.path.dirname(__file__), "..", "radcoolpv", "data")
CONFIGS = os.path.join(os.path.dirname(__file__), "..", "configs")
ATMOS = os.path.join(PKG_DATA, "cptrans_nq_100_15.dat")
FF_FILE = os.path.join(PKG_DATA, "freeform_NIL_1um.txt")


@pytest.fixture
def full_cfg():
    return config_module.load(os.path.join(CONFIGS, "full.yaml"))


def test_cylinder_structure(full_cfg):
    s = geometry.build_structure(full_cfg)
    assert s.lattice == ((20.0, 0.0), (0.0, 20.0))           # square uses x for both
    assert s.layers[0].name == "layerVacuumTop"
    # photonic cylinder layer.
    cyl = s.layers[1]
    assert cyl.name == "Layer_1" and cyl.thickness == 30.0 and cyl.background == "vacuum"
    assert len(cyl.patterns) == 1 and cyl.patterns[0].kind == "circle"
    assert cyl.patterns[0].radius == 5.0 and cyl.patterns[0].material == "sio2"
    # flat stack + terminal.
    assert s.silicon_layer == "layerSilicon"
    assert s.bottom_layer == "layerBottom"
    assert s.layers[-1].name == "layerBottom" and s.layers[-1].background == "substrate"
    # 1 vacuum top + 1 cylinder + 7 structure layers.
    assert len(s.layers) == 1 + 1 + len(full_cfg.structure)


def test_triangle_discretization():
    cfg = config_module.from_dict({
        "run": {"thermal": False},
        "geometry": {"source": "s4", "shape": "triangle",
                     "photonic_material": "sio2",
                     "lattice": {"type": "square", "x": 20.0},
                     "discretization_layers": 4,
                     "triangle": {"base": 12.0, "height": 20.0}},
        "structure": [{"material": "silicon", "thickness": 250.0},
                      {"material": "substrate", "thickness": 0.0, "terminal": True}],
        "materials": {"sio2": "PalikKitamura_SiO2", "silicon": "SiliconNew",
                      "substrate": "Hagemann_Ag"},
    })
    s = geometry.build_structure(cfg)
    tri_layers = [l for l in s.layers if l.name.startswith("Layer_")]
    assert len(tri_layers) == 4
    # Rectangle halfwidths grow from tip to base.
    hw = [l.patterns[0].halfwidths[0] for l in tri_layers]
    assert hw == sorted(hw) and hw[0] > 0


def test_freeform_normal_result():
    res = freeform.load(FF_FILE, n_lambda=500, atmosphere_path=ATMOS)
    assert res.angles == "normal"
    assert res.lambda_um.shape == (500,)
    # tran == 1 - abs - ref by construction.
    assert np.allclose(res.tran, 1.0 - res.emit - res.ref, atol=1e-12)
    assert np.all(np.isfinite(res.abs_silicon))


def test_s4_backend_guard(full_cfg):
    # S4 is not built in this environment; sweep must raise a clear error.
    if s4_backend.is_available():
        pytest.skip("S4 is installed; guard not exercised.")
    with pytest.raises(RuntimeError, match="S4 Python module"):
        s4_backend.sweep(full_cfg, np.linspace(0.3, 30.0, 10),
                         full_cfg.angle_array_deg())


def test_resolve_eps(full_cfg):
    funcs = s4_backend.resolve_eps(full_cfg)
    assert "vacuum" in funcs and "sio2" in funcs and "silicon" in funcs
    assert np.isclose(funcs["vacuum"](1.0), 1.0)
