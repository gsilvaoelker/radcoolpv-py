"""Geometric correctness of the photonic-structure discretisation.

`sphere` and `semisphere` previously had no coverage at all - no test, no
config - and every validation config runs `optics: false`, so nothing in the
suite had ever executed this code. Three defects were living there, all in the
semisphere branch:

1. `round(n / 2)` transcribed MATLAB's `round` literally, but MATLAB rounds half
   AWAY FROM ZERO and Python rounds half TO EVEN, so the equatorial slab was
   dropped for odd n with n//2 even (n = 5, 9, 21, ...).
2. Even n halved the middle slab even though the equator falls on a slab
   BOUNDARY there, leaving every even count `radius / n` short.
3. n = 1 - the default - produced no patterned layers at all, so the photonic
   structure silently vanished and a flat stack was reported as a hemisphere.

The dome now spans exactly `radius` for every n, even or odd.

These tests assert the *shape*, not just that the code runs: total stack height,
slab thicknesses, peak radius, and the radius profile. They need no optics
engine, so they run everywhere regardless of whether S4 is built.
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
             "triangle": "triangle", "cylinder": "cylinder",
             "grating": "grating"}.get(shape)
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

@pytest.mark.parametrize("n", list(range(1, 25)) + [31, 32, 64])
def test_semisphere_spans_exactly_its_radius(n):
    """The dome must span exactly `radius`, for EVERY layer count.

    Regression test for two defects. The old `round(n / 2)` dropped the
    equatorial slab at n = 5, 9, 21... (Python rounds half to even, MATLAB
    rounds half away from zero), and every even n was `radius / n` short
    because the middle slab was halved when the equator actually falls on a
    slab boundary. n = 1, the default, produced no layers at all.
    """
    s = _structure("semisphere", n, radius=RADIUS)
    assert _height(s) == pytest.approx(RADIUS, rel=1e-12), (
        f"n={n}: dome is {RADIUS - _height(s):.4f} um short")


@pytest.mark.parametrize("n", [1, 2, 3, 4, 9, 10])
def test_semisphere_is_never_empty(n):
    """`discretization_layers` defaults to 1, which used to yield NO patterned
    layers at all - the photonic structure vanished and a bare flat stack was
    reported as a hemisphere."""
    s = _structure("semisphere", n, radius=RADIUS)
    assert len(_photonic(s)) >= 1


@pytest.mark.parametrize("n", [3, 4, 9, 10, 21])
def test_semisphere_widens_downward_towards_the_equator(n):
    s = _structure("semisphere", n, radius=RADIUS)
    radii = [L.patterns[0].radius for L in _photonic(s)]
    assert all(b >= a for a, b in zip(radii, radii[1:]))   # monotonic
    assert max(radii) <= RADIUS + 1e-12
    if n % 2 == 1:
        # The middle slab is centred on the equator, so its radius is exactly r.
        assert radii[-1] == pytest.approx(RADIUS, rel=1e-9)
    else:
        # Whole slabs only: the lowest sits delta/2 above the equator, so its
        # mid-slab radius is below r but approaches it as n grows.
        assert radii[-1] < RADIUS
        assert radii[-1] > RADIUS * (1.0 - 2.0 / n)


@pytest.mark.parametrize("shape", ["sphere", "semisphere", "triangle"])
def test_discretised_shapes_reject_nonsensical_layer_counts(shape):
    kw = {"radius": RADIUS} if shape != "triangle" else {"base": 8.0, "height": 6.0}
    with pytest.raises(ConfigError, match="discretization_layers"):
        _structure(shape, 0, **kw)


@pytest.mark.parametrize("n", [2, 4, 8, 16])
def test_semisphere_even_counts_use_whole_slabs(n):
    """With the equator on a slab boundary there is no half slab to take."""
    s = _structure("semisphere", n, radius=RADIUS)
    thick = [L.thickness for L in _photonic(s)]
    assert len(thick) == n // 2
    assert all(t == pytest.approx(2 * RADIUS / n) for t in thick)


@pytest.mark.parametrize("n", [3, 5, 9, 21])
def test_semisphere_odd_counts_halve_the_equatorial_slab(n):
    s = _structure("semisphere", n, radius=RADIUS)
    thick = [L.thickness for L in _photonic(s)]
    delta = 2 * RADIUS / n
    assert len(thick) == n // 2 + 1
    assert all(t == pytest.approx(delta) for t in thick[:-1])
    assert thick[-1] == pytest.approx(delta / 2)


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


# --- grating (1-D lamellar) -----------------------------------------------

def test_grating_is_one_stripe_layer_of_its_depth():
    s = _structure("grating", duty=0.2, depth=10.0)
    pl = _photonic(s)
    assert len(pl) == 1
    assert _height(s) == pytest.approx(10.0)
    layer = pl[0]
    assert layer.background == "sio2"          # ridge is the photonic material
    assert len(layer.patterns) == 1
    groove = layer.patterns[0]
    assert groove.kind == "rectangle"
    assert groove.material == "vacuum"         # groove is empty


@pytest.mark.parametrize("duty,ridge_w", [(0.2, 4.0), (0.5, 10.0), (0.8, 16.0)])
def test_grating_duty_sets_the_ridge_width(duty, ridge_w):
    """duty is the ridge (photonic-material) fraction of the period; for the
    LATTICE period 20 um that gives ridge width duty*20."""
    s = _structure("grating", duty=duty, depth=5.0)
    groove = _photonic(s)[0].patterns[0]
    groove_w = 2 * groove.halfwidths[0]
    assert LATTICE - groove_w == pytest.approx(ridge_w)     # ridge = period - groove
    assert groove.halfwidths[1] == pytest.approx(LATTICE / 2)  # spans full cell in y


@pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.5])
def test_grating_rejects_out_of_range_duty(bad):
    with pytest.raises(ConfigError, match="duty"):
        _structure("grating", duty=bad, depth=5.0)


def test_grating_rejects_nonpositive_depth():
    with pytest.raises(ConfigError, match="depth"):
        _structure("grating", duty=0.2, depth=0.0)


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


@pytest.mark.parametrize("n", [8, 9])
def test_sphere_and_semisphere_agree_on_the_upper_half(n):
    """A semisphere must reuse the sphere's own slab radii, not a second
    derivation that could drift from it."""
    sph = [L.patterns[0].radius for L in _photonic(_structure("sphere", n, radius=RADIUS))]
    dome = [L.patterns[0].radius for L in _photonic(_structure("semisphere", n, radius=RADIUS))]
    assert dome == pytest.approx(sph[:len(dome)])
