"""Build the S4 layer stack from the geometry + structure config.

Ports the geometry blocks of ``mainOpticalMatlabS4_v11.m`` (the discretisation
of spheres/semispheres/triangles/cylinders and the flat layer stack). Produces a
solver-agnostic description that ``s4_backend`` turns into S4 calls; this keeps
the geometry math testable without S4 installed.

All lengths are in micrometres. Material names are the *logical* names from the
config (e.g. ``sio2``, ``silicon``, ``vacuum``); the backend maps them to eps.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..config import Config

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
    bottom_layer: str               # terminal layer name (transmission probe)
    top_layer: str = "layerVacuumTop"


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
        else:  # semisphere: lower half only (matches the MATLAB writing loop)
            half = round(n / 2)
            for i in range(n):
                idx = i + 1
                if idx < n / 2:
                    thick = delta
                elif idx == half:
                    thick = delta * 0.5
                else:
                    break
                pats = [Pattern("circle", mat, (0.0, 0.0), radius=xs[i])]
                if hexa:
                    pats.append(Pattern("circle", mat, corner, radius=xs[i]))
                layers.append(S4Layer(f"Layer_{idx}", thick, "vacuum", pats))
                if idx == half:
                    break
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

    raise ValueError(f"Unsupported geometry.shape: {g.shape!r}")


def build_structure(cfg: Config) -> S4Structure:
    """Assemble the full top-to-bottom S4 layer stack."""
    layers: List[S4Layer] = [S4Layer("layerVacuumTop", 0.0, "vacuum", [])]
    layers.extend(_photonic_layers(cfg))

    silicon_layer = None
    bottom_layer = "layerBottom"
    for i, layer in enumerate(cfg.structure):
        if layer.terminal:
            name = "layerBottom"
            bottom_layer = name
        elif layer.material == "silicon":
            name = "layerSilicon"
            silicon_layer = name
        else:
            name = f"layer_{i}_{layer.material}"
        layers.append(S4Layer(name, layer.thickness, layer.material, []))

    return S4Structure(
        lattice=_lattice(cfg), layers=layers,
        silicon_layer=silicon_layer, bottom_layer=bottom_layer,
    )
