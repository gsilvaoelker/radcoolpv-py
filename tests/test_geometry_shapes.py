"""Geometric correctness of the photonic-structure discretisation.

`sphere` and `semisphere` previously had no coverage at all - no test, no
config - and every validation config runs `optics: false`, so nothing in the
suite had ever executed this code. A real bug lived there: `round(n / 2)` was a
literal transcription of MATLAB's `round`, but MATLAB rounds half AWAY FROM
ZERO while Python rounds half TO EVEN, so the equatorial slab was dropped
whenever n was odd with n//2 even (n = 5, 9, 21, ...) and the dome came out one
slab short.

These tests assert the *shape*, not just that the code runs: total stack height,
peak radius, and the radius profile. They need no optics engine.
"""

import math

import numpy as np
import pytest

from radcoolpv import config as config_module
from radcoolpv.config import ConfigError
from radcoolpv.optics import geometry

RADIUS = 5.0
LATTICE = 20.0


def _structure(shape, n_layers=3, **shape_kw):
    block = {"sphere": "sphere", "semisphere": "sphere",
             "triangle": "triangle", "cylinder": "cylinder"}.get(shape)
    geom = {"source": "s4", "shape": shape, "photonic_material": "sio2",
            "lattice": {"type": "square", "x": LATTICE, "y": LATTICE},
            "discretization_layers": n_layers}
    if block:
        geom[block] = shape_kw
    cfg = config_module.from_dict({
        "run": {"optics": True, "thermal": False, "plots": False},
        "simulation": {"wavelength": {"min": 8.0, "max": 10.0, "n": 3},
                       "angles": "normal", "rcwa_modes": 10},
        "geometry": geom,
        "structure": [{"material": "silicon", "thickness": 250.0},
                      {"material": "substrate", "thickness": 0.0, "terminal": True}],
        "materials": {"sio2": "PalikKitamura_SiO2", "silicon": "SiliconNew",
                      "substrate": "Hagemann_Ag"},
        "thermal": {},
    }, base_dir="radcoolpv")
    return geometry.build_structure(cfg)


def _photonic(structure):
    return [L for L in structure.layers if L.patterns]


def _height(structure):
    return sum(L.thickness for L in _photonic(structure))


def _max_radius(structure):
    return max(p.radius for L in _photonic(structure) for p in L.patterns)


# --- sphere ---------------------------------------------------------------

@pytest.mark.parametrize("n", [2, 5, 8, 9, 32])
def test_sphere_spans_its_diameter(n):
    s = _structure("sphere", n, radius=RADIUS)
    assert len(_photonic(s)) == n
    assert _height(s) == pytest.approx(2 * RADIUS, rel=1e-12)


@pytest.mark.parametrize("n", [8, 9, 32])
def test_sphere_radius_profile_is_symmetric_and_bounded(n):
    s = _structure("sphere", n, radius=RADIUS)
    radii = [L.patterns[0].radius for L in _photonic(s)]
    assert max(radii) <= RADIUS + 1e-12
    assert radii == pytest.approx(radii[::-1])          # symmetric about equator
    assert radii[0] < radii[n // 2]                     # widest in the middle


# --- semisphere -----------------------------------------------------------

@pytest.mark.parametrize("n", [1, 3, 5, 7, 9, 11, 21, 31])
def test_semisphere_spans_exactly_its_radius(n):
    """The regression test for the round()-semantics bug.

    Fails at n = 5, 9, 21 with the old `round(n / 2)`: the dome came out
    `radius / n` short because Python dropped the equatorial slab.
    """
    s = _structure("semisphere", n, radius=RADIUS)
    assert _height(s) == pytest.approx(RADIUS, rel=1e-12), (
        f"n={n}: dome is {RADIUS - _height(s):.4f} um short")


@pytest.mark.parametrize("n", [1, 3, 9])
def test_semisphere_is_never_empty(n):
    """`discretization_layers` defaults to 1, which used to yield NO patterned
    layers at all - the photonic structure vanished and a bare flat stack was
    reported as a hemisphere."""
    s = _structure("semisphere", n, radius=RADIUS)
    assert len(_photonic(s)) >= 1


@pytest.mark.parametrize("n", [3, 9, 21])
def test_semisphere_widens_downward_towards_the_equator(n):
    s = _structure("semisphere", n, radius=RADIUS)
    radii = [L.patterns[0].radius for L in _photonic(s)]
    assert all(b >= a for a, b in zip(radii, radii[1:]))   # monotonic
    assert max(radii) <= RADIUS + 1e-12
    assert radii[-1] == pytest.approx(RADIUS, rel=0.05)    # reaches the equator


@pytest.mark.parametrize("n", [2, 4, 8])
def test_semisphere_rejects_even_layer_counts(n):
    with pytest.raises(ConfigError, match="must be ODD"):
        _structure("semisphere", n, radius=RADIUS)


# --- other shapes ---------------------------------------------------------

@pytest.mark.parametrize("n", [1, 4, 9])
def test_triangle_spans_its_height(n):
    s = _structure("triangle", n, base=8.0, height=6.0)
    assert _height(s) == pytest.approx(6.0, rel=1e-12)
    hw = [p.halfwidths for L in _photonic(s) for p in L.patterns]
    assert all(a == pytest.approx(b) for a, b in hw)       # square cross-section
    assert max(max(h) for h in hw) <= 8.0 / 2 + 1e-12


def test_cylinder_is_one_layer_of_its_height():
    s = _structure("cylinder", 5, radius=2.0, height=3.0)
    assert len(_photonic(s)) == 1
    assert _height(s) == pytest.approx(3.0)
    assert _max_radius(s) == pytest.approx(2.0)


def test_flat_has_no_photonic_layers():
    assert _photonic(_structure("flat")) == []


def test_hexagonal_lattice_adds_the_corner_copy():
    """A hexagonal cell carries a second circle at the cell corner."""
    sq = _structure("cylinder", 1, radius=2.0, height=3.0)
    assert len(_photonic(sq)[0].patterns) == 1
    cfg = config_module.from_dict({
        "run": {"optics": True, "thermal": False, "plots": False},
        "simulation": {"wavelength": {"min": 8.0, "max": 10.0, "n": 3},
                       "angles": "normal", "rcwa_modes": 10},
        "geometry": {"source": "s4", "shape": "cylinder",
                     "photonic_material": "sio2",
                     "lattice": {"type": "hexagonal", "x": LATTICE, "y": 10.0},
                     "cylinder": {"radius": 2.0, "height": 3.0}},
        "structure": [{"material": "silicon", "thickness": 250.0},
                      {"material": "substrate", "thickness": 0.0, "terminal": True}],
        "materials": {"sio2": "PalikKitamura_SiO2", "silicon": "SiliconNew",
                      "substrate": "Hagemann_Ag"},
        "thermal": {},
    }, base_dir="radcoolpv")
    hexa = _photonic(geometry.build_structure(cfg))[0]
    assert len(hexa.patterns) == 2
    assert hexa.patterns[1].center == (LATTICE / 2, 10.0 / 2)


def test_sphere_and_semisphere_agree_on_the_upper_half():
    """A semisphere must reuse the sphere's own slab radii, not a second
    derivation that could drift from it."""
    n = 9
    sph = [L.patterns[0].radius for L in _photonic(_structure("sphere", n, radius=RADIUS))]
    dome = [L.patterns[0].radius for L in _photonic(_structure("semisphere", n, radius=RADIUS))]
    assert dome == pytest.approx(sph[:len(dome)])
