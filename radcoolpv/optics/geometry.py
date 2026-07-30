"""Build the S4 layer stack from the geometry + structure config.

Ports the geometry blocks of ``mainOpticalMatlabS4_v11.m`` (the discretisation
of spheres/semispheres/triangles/cylinders and the flat layer stack). Produces
the declarative ``S4Structure`` that :mod:`radcoolpv.optics.s4_backend` turns
into S4 calls, keeping the geometry math separate from the solver calls.

All lengths are in micrometres. Material names are the *logical* names from the
config (e.g. ``sio2``, ``silicon``, ``vacuum``); :func:`resolve_eps` maps them to
permittivity callables.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from ..config import Config
from ..materials import analytic, registry

LatticeVectors = Tuple[Tuple[float, float], Tuple[float, float]]


@dataclass
class Pattern:
    kind: str                       # 'circle' | 'rectangle'
    material: str                   # logical material name
    center: Tuple[float, float]
    radius: Optional[float] = None             # circle
    halfwidths: Optional[Tuple[float, float]] = None  # rectangle
    angle: float = 0.0              # rectangle, degrees


@dataclass
class S4Layer:
    name: str
    thickness: float
    background: str                 # logical material of the unpatterned region
    patterns: List[Pattern] = field(default_factory=list)


@dataclass
class S4Structure:
    lattice: LatticeVectors
    layers: List[S4Layer]
    silicon_layer: Optional[str]    # layer name used for the Si-absorption probe
    silicon_thickness: float
    bottom_layer: str               # terminal layer name (transmission probe)
    top_layer: str = "layerVacuumTop"


def resolve_eps(cfg: Config) -> Dict[str, Callable]:
    """Map each logical material name to its ``eps(lambda_um)`` callable.

    Single place where a config material name becomes permittivity, so the
    engine and the geometry builder cannot disagree about it.
    """
    funcs: Dict[str, Callable] = {"vacuum": analytic.vacuum}
    for logical, model in cfg.materials.items():
        funcs[logical] = registry.get(model)
    return funcs


def used_materials(structure: S4Structure) -> List[str]:
    """Every logical material appearing anywhere in the structure, sorted."""
    names = {"vacuum"}
    for layer in structure.layers:
        names.add(layer.background)
        for pat in layer.patterns:
            names.add(pat.material)
    return sorted(names)


def _lattice(cfg: Config) -> LatticeVectors:
    lat = cfg.geometry.lattice
    if lat.type == "square":
        return ((lat.x, 0.0), (0.0, lat.x))        # square uses x for both
    if lat.type == "hexagonal":
        return ((lat.x, 0.0), (0.0, lat.y))
    raise ValueError(f"geometry.lattice.type must be square|hexagonal, got {lat.type!r}")


def _corner_center(cfg: Config) -> Tuple[float, float]:
    lat = cfg.geometry.lattice
    return (lat.x / 2.0, lat.y / 2.0)


def _photonic_layers(cfg: Config) -> List[S4Layer]:
    """Build the patterned photonic layers above the flat stack."""
    g = cfg.geometry
    mat = g.photonic_material
    hexa = (g.lattice.type == "hexagonal")
    corner = _corner_center(cfg)
    layers: List[S4Layer] = []

    if g.shape == "flat":
        return layers

    if g.shape == "cylinder":
        r = g.cylinder["radius"]
        h = g.cylinder["height"]
        pats = [Pattern("circle", mat, (0.0, 0.0), radius=r)]
        if hexa:
            pats.append(Pattern("circle", mat, corner, radius=r))
        layers.append(S4Layer("Layer_1", h, "vacuum", pats))
        return layers

    if g.shape in ("sphere", "semisphere"):
        rad = g.sphere["radius"]
        diam = 2.0 * rad
        n = g.discretization_layers
        delta = diam / n
        # Mid-layer y positions and circle radii (MATLAB sphere discretisation).
        ys, xs = [], []
        y_prev = diam - delta * 0.5
        ys.append(y_prev)
        xs.append(math.sqrt(max(rad ** 2 - (y_prev - rad) ** 2, 0.0)))
        for _ in range(1, n):
            y_prev = y_prev - delta
            ys.append(y_prev)
            xs.append(math.sqrt(max(rad ** 2 - (y_prev - rad) ** 2, 0.0)))

        if g.shape == "sphere":
            for i in range(n):
                pats = [Pattern("circle", mat, (0.0, 0.0), radius=xs[i])]
                if hexa:
                    pats.append(Pattern("circle", mat, corner, radius=xs[i]))
                layers.append(S4Layer(f"Layer_{i + 1}", delta, "vacuum", pats))
        else:
            # Semisphere: the dome is the upper half of that sphere, so it must
            # span exactly `rad` for any n. Where the equator falls decides how
            # the middle slab is treated:
            #
            #   n even -> the equator lands on a slab BOUNDARY, so the top n/2
            #             slabs are whole:      (n/2) * delta            = rad
            #   n odd  -> the equator bisects the middle slab, so that one
            #             counts half:  ((n-1)/2 + 1/2) * delta          = rad
            #
            # The MATLAB original wrote this as round(n/2) and only ever claimed
            # to support odd n ("Use odd numbers for semipsheres"). Transcribing
            # that round() was a bug twice over: Python rounds half TO EVEN
            # rather than AWAY FROM ZERO, dropping the equatorial slab for
            # n = 5, 9, 21..., and n = 1 (the default) produced no layers at all.
            n_full = n // 2
            for i in range(n):
                idx = i + 1
                if idx <= n_full:
                    thick = delta
                elif n % 2 == 1 and idx == n_full + 1:
                    thick = delta * 0.5          # slab straddling the equator
                else:
                    break
                pats = [Pattern("circle", mat, (0.0, 0.0), radius=xs[i])]
                if hexa:
                    pats.append(Pattern("circle", mat, corner, radius=xs[i]))
                layers.append(S4Layer(f"Layer_{idx}", thick, "vacuum", pats))
        return layers

    if g.shape == "triangle":
        base = g.triangle["base"]
        height = g.triangle["height"]
        n = g.discretization_layers
        delta = height / n
        y = delta * 0.5
        for i in range(n):
            if i > 0:
                y = y + delta
            x = base * y / (2.0 * height)
            pats = [Pattern("rectangle", mat, (0.0, 0.0), halfwidths=(x, x), angle=0.0)]
            layers.append(S4Layer(f"Layer_{i + 1}", delta, "vacuum", pats))
        return layers

    if g.shape == "grating":
        # 1D lamellar grating: `photonic_material` ridges of period `lattice.x`
        # separated by vacuum grooves, invariant along y. The groove is a single
        # rectangle of the full cell height in y, so the layer is a stripe
        # pattern - S4 solves the true 1D grating (no y structure).
        period = g.lattice.x
        depth = g.grating["depth"]
        duty = g.grating["duty"]                 # fraction of the period that is ridge
        groove_half_x = (1.0 - duty) * period / 2.0
        # Half-height = half the y-period, so the groove spans the whole cell in
        # y and the layer is a true 1D grating.
        groove = Pattern("rectangle", "vacuum", (0.0, 0.0),
                         halfwidths=(groove_half_x, g.lattice.y / 2.0), angle=0.0)
        layers.append(S4Layer("Layer_1", depth, mat, [groove]))
        return layers

    raise ValueError(f"Unsupported geometry.shape: {g.shape!r}")


def build_structure(cfg: Config) -> S4Structure:
    """Assemble the full top-to-bottom S4 layer stack."""
    layers: List[S4Layer] = [S4Layer("layerVacuumTop", 0.0, "vacuum", [])]
    layers.extend(_photonic_layers(cfg))

    silicon_layer = None
    silicon_thickness = 0.0
    bottom_layer = "layerBottom"
    for i, layer in enumerate(cfg.structure):
        if layer.terminal:
            name = "layerBottom"
            bottom_layer = name
        elif layer.material == "silicon":
            name = "layerSilicon"
            silicon_layer = name
            silicon_thickness = layer.thickness
        elif layer.thickness == 0.0:
            continue
        else:
            name = f"layer_{i}_{layer.material}"
        layers.append(S4Layer(name, layer.thickness, layer.material, []))

    return S4Structure(
        lattice=_lattice(cfg), layers=layers,
        silicon_layer=silicon_layer, silicon_thickness=silicon_thickness,
        bottom_layer=bottom_layer,
    )
