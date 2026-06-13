"""RCWA optics via the S4 Python bindings.

Replaces the MATLAB-writes-Lua-files-and-shell-calls-S4 dance with direct calls
to the S4 Python module (``import S4``). Builds the structure once, then sweeps
wavelength x angle x polarisation, returning a :class:`RawOptics` identical in
content to the old ``OUTPUTS4-TE.txt`` / ``-TM.txt`` files.

S4 is imported lazily so the rest of the package works without it. The flux
bookkeeping reproduces ``SiO2Spheres-v5.lua`` exactly (including writing the raw
forward transmission flux in the T column).
"""

from __future__ import annotations

from typing import Callable, Dict, List

import numpy as np

from ..config import Config
from ..materials import analytic, registry
from .directional import RawOptics
from .geometry import S4Structure, build_structure


def is_available() -> bool:
    """True if the S4 Python module can be imported."""
    try:
        import S4  # noqa: F401
        return True
    except Exception:
        return False


def resolve_eps(cfg: Config) -> Dict[str, Callable]:
    """Map each logical material name to its ``eps(lambda_um)`` callable."""
    funcs: Dict[str, Callable] = {"vacuum": analytic.vacuum}
    for logical, model in cfg.materials.items():
        funcs[logical] = registry.get(model)
    return funcs


def _used_materials(structure: S4Structure) -> List[str]:
    names = {"vacuum"}
    for layer in structure.layers:
        names.add(layer.background)
        for pat in layer.patterns:
            names.add(pat.material)
    return sorted(names)


def _build_sim(structure: S4Structure, num_basis: int, eps0: Dict[str, complex]):
    import S4

    sim = S4.New(Lattice=structure.lattice, NumBasis=int(num_basis))
    for name in _used_materials(structure):
        sim.SetMaterial(Name=name, Epsilon=complex(eps0[name]))
    for layer in structure.layers:
        sim.AddLayer(Name=layer.name, Thickness=float(layer.thickness),
                     Material=layer.background)
        for pat in layer.patterns:
            if pat.kind == "circle":
                sim.SetRegionCircle(Layer=layer.name, Material=pat.material,
                                    Center=pat.center, Radius=float(pat.radius))
            elif pat.kind == "rectangle":
                sim.SetRegionRectangle(Layer=layer.name, Material=pat.material,
                                       Center=pat.center, Angle=float(pat.angle),
                                       Halfwidths=pat.halfwidths)
            else:
                raise ValueError(f"unknown pattern kind {pat.kind!r}")
    return sim


def sweep(cfg: Config, lambda_grid: np.ndarray, angles_deg: np.ndarray) -> RawOptics:
    """Run the RCWA sweep and return per-(wavelength, angle) raw optics."""
    if not is_available():
        raise RuntimeError(
            "The S4 Python module is not installed. Build it from the Stanford "
            "S4 source with Python support (see README), or use geometry.source: "
            "freeform / a pre-computed optics results folder."
        )

    structure = build_structure(cfg)
    eps_funcs = resolve_eps(cfg)
    mats = _used_materials(structure)

    n_lambda = len(lambda_grid)
    angles = np.asarray(angles_deg, dtype=float)
    n_theta = len(angles)
    normal = (n_theta == 1) and np.isclose(angles[0], 0.0)
    pols = [("te", 1.0, 0.0)] if normal else [("te", 1.0, 0.0), ("tm", 0.0, 1.0)]

    # Pre-evaluate eps for all materials over the grid (vectorised).
    eps_grid = {m: np.asarray(eps_funcs[m](lambda_grid), dtype=complex) for m in mats}
    eps0 = {m: eps_grid[m][0] for m in mats}

    sim = _build_sim(structure, cfg.simulation.rcwa_modes, eps0)

    out = {p[0]: {k: np.zeros((n_lambda, n_theta)) for k in
                  ("ref", "tran", "abs", "abs_si")} for p in pols}

    for it, theta in enumerate(angles):
        for pol_name, s_amp, p_amp in pols:
            sim.SetExcitationPlanewave(IncidenceAngles=(float(theta), 0.0),
                                       sAmplitude=s_amp, pAmplitude=p_amp, Order=0)
            for il in range(n_lambda):
                lam = lambda_grid[il]
                for m in mats:
                    sim.SetMaterial(Name=m, Epsilon=complex(eps_grid[m][il]))
                sim.SetFrequency(1.0 / lam)   # S4 frequency = 1/lambda (lattice in um)

                inc, refl = sim.GetPowerFlux(Layer=structure.top_layer, zOffset=0)
                inc = inc.real if np.iscomplexobj(inc) else inc
                refl = refl.real if np.iscomplexobj(refl) else refl
                t_fwd = sim.GetPowerFlux(Layer=structure.bottom_layer, zOffset=0)[0].real

                R = -refl / inc
                A = 1.0 - R - t_fwd
                if structure.silicon_layer is not None:
                    f_si, b_si = sim.GetPowerFlux(Layer=structure.silicon_layer, zOffset=0)
                    f_b, b_b = sim.GetPowerFlux(Layer=structure.bottom_layer, zOffset=0)
                    a_si = (f_si.real + b_si.real - f_b.real - b_b.real) / inc
                else:
                    a_si = 0.0

                d = out[pol_name]
                d["ref"][il, it] = R
                d["tran"][il, it] = t_fwd
                d["abs"][il, it] = A
                d["abs_si"][il, it] = a_si

    raw = RawOptics(
        theta_deg=angles, lambda_um=np.asarray(lambda_grid, dtype=float),
        ref_te=out["te"]["ref"], tran_te=out["te"]["tran"],
        abs_te=out["te"]["abs"], abs_si_te=out["te"]["abs_si"],
    )
    if not normal:
        raw.ref_tm = out["tm"]["ref"]
        raw.tran_tm = out["tm"]["tran"]
        raw.abs_tm = out["tm"]["abs"]
        raw.abs_si_tm = out["tm"]["abs_si"]
    return raw
