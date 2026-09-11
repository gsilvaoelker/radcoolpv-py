"""Tests for geometry construction and the S4 backend guard."""

import os

import numpy as np
import pytest

from radcoolpv import config as config_module
from radcoolpv.optics import geometry, s4_backend

CONFIGS = os.path.join(os.path.dirname(__file__), "data")


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
    # flat stack + the semi-infinite substrate.
    assert s.silicon_layer == "layerSilicon"
    assert s.bottom_layer == "layerBottom"
    assert s.layers[-1].name == "layerBottom" and s.layers[-1].background == "substrate"
    assert len(s.layers) == 6


def test_triangle_discretization():
    cfg = config_module.from_dict({"optics": {
        "geometry": {"shape": "triangle", "photonic_material": "sio2",
                     "lattice": {"type": "square", "x": 20.0},
                     "triangle": {"base": 12.0, "height": 20.0, "layers": 4}},
        "structure": [{"material": "silicon", "thickness": 250.0}],
        "substrate": "substrate",
        "materials": {"sio2": "PalikKitamura_SiO2", "silicon": "SiliconNew",
                      "substrate": "Hagemann_Ag"},
    }})
    s = geometry.build_structure(cfg)
    tri_layers = [l for l in s.layers if l.name.startswith("Layer_")]
    assert len(tri_layers) == 4
    # Rectangle halfwidths grow from tip to base.
    hw = [l.patterns[0].halfwidths[0] for l in tri_layers]
    assert hw == sorted(hw) and hw[0] > 0


def test_s4_backend_guard(full_cfg):
    # If S4 is missing, sweep must raise an error naming the build steps.
    if s4_backend.is_available():
        pytest.skip("S4 is installed; guard not exercised.")
    with pytest.raises(RuntimeError, match="S4 Python module is not installed"):
        s4_backend.sweep(full_cfg, np.linspace(0.3, 30.0, 10),
                         full_cfg.direction_arrays()[0])


def test_resolve_eps(full_cfg):
    funcs = s4_backend.resolve_eps(full_cfg)
    assert "vacuum" in funcs and "sio2" in funcs and "silicon" in funcs
    assert np.isclose(funcs["vacuum"](1.0), 1.0)
