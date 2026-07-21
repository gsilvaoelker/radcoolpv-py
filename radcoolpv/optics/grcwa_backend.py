"""RCWA optics via the pure-Python `grcwa` package.

Replaces the C++ Stanford-S4 backend so the whole optics stage is pure Python.
The public contract is identical to the old ``s4_backend``: ``sweep`` builds the
structure from :func:`geometry.build_structure`, sweeps wavelength x angle x
polarisation, and returns a :class:`~radcoolpv.optics.directional.RawOptics`
with the same fields, so ``directional.reduce`` and everything downstream are
unchanged.

grcwa (Jin, Williamson & Fan) is pure Python (numpy + autograd). Two mappings
differ from S4 and are handled here:

* Patterned layers are **rasterised** to an ``Nx x Ny`` permittivity grid
  (grcwa has no analytic circle/rectangle primitives); resolution is
  ``simulation.grid_nx/ny``. ``simulation.rcwa_modes`` is used as grcwa's
  Fourier truncation ``nG``.
* Per-layer silicon absorptance is obtained from the net z-Poynting-flux
  difference across the silicon layer (the exact analogue of the S4
  ``GetPowerFlux`` bookkeeping), consistent with grcwa's own ``RT_Solve``
  normalisation.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

import numpy as np

from ..config import Config
from ..materials import analytic, registry
from .directional import RawOptics
from .geometry import S4Structure, build_structure


def is_available() -> bool:
    """True if the grcwa module can be imported."""
    try:
        import grcwa  # noqa: F401
        return True
    except Exception:
        return False


def resolve_eps(cfg: Config) -> Dict[str, Callable]:
    """Map each logical material name to its ``eps(lambda_um)`` callable."""
    funcs: Dict[str, Callable] = {"vacuum": analytic.vacuum}
    for logical, model in cfg.materials.items():
        funcs[logical] = registry.get(model)
    return funcs


def _pattern_masks(structure: S4Structure, nx: int, ny: int):
    """Precompute per-patterned-layer boolean masks (wavelength-independent).

    Returns a dict ``{layer_index: [(mask, material), ...]}`` on an ``nx x ny``
    cell-centred grid. Masks use the minimum-image (periodic) distance so a
    circle centred on a cell corner correctly wraps to all four corners.
    """
    (l1x, _l1y), (_l2x, l2y) = structure.lattice
    lx, ly = float(l1x), float(l2y)          # radcoolpv lattices are axis-aligned
    fx = (np.arange(nx) + 0.5) / nx
    fy = (np.arange(ny) + 0.5) / ny
    xg, yg = np.meshgrid(fx * lx, fy * ly, indexing="ij")

    masks: Dict[int, List[Tuple[np.ndarray, str]]] = {}
    for i, layer in enumerate(structure.layers):
        if not layer.patterns:
            continue
        entries: List[Tuple[np.ndarray, str]] = []
        for pat in layer.patterns:
            cx, cy = pat.center
            dx = np.mod(xg - cx + lx / 2.0, lx) - lx / 2.0
            dy = np.mod(yg - cy + ly / 2.0, ly) - ly / 2.0
            if pat.kind == "circle":
                m = dx ** 2 + dy ** 2 < float(pat.radius) ** 2
            elif pat.kind == "rectangle":
                hx, hy = pat.halfwidths
                m = (np.abs(dx) < float(hx)) & (np.abs(dy) < float(hy))
            else:
                raise ValueError(f"unknown pattern kind {pat.kind!r}")
            entries.append((m, pat.material))
        masks[i] = entries
    return masks


def sweep(cfg: Config, lambda_grid: np.ndarray, angles_deg: np.ndarray) -> RawOptics:
    """Run the grcwa RCWA sweep and return per-(wavelength, angle) raw optics."""
    if not is_available():
        raise RuntimeError(
            "The grcwa module is not installed. Install it with `pip install "
            "grcwa` (pure Python), or use geometry.source: freeform / a "
            "pre-computed optics results folder."
        )
    import grcwa
    from grcwa.rcwa import GetZPoyntingFlux

    structure = build_structure(cfg)
    eps_funcs = resolve_eps(cfg)
    (l1x, l1y), (l2x, l2y) = structure.lattice
    L1, L2 = [float(l1x), float(l1y)], [float(l2x), float(l2y)]
    nG = int(cfg.simulation.rcwa_modes)
    nx, ny = int(cfg.simulation.grid_nx), int(cfg.simulation.grid_ny)

    masks = _pattern_masks(structure, nx, ny)
    grid_indices = [i for i, ly in enumerate(structure.layers) if ly.patterns]
    si_idx = None
    if structure.silicon_layer is not None:
        si_idx = next(i for i, ly in enumerate(structure.layers)
                      if ly.name == structure.silicon_layer)

    angles = np.asarray(angles_deg, dtype=float)
    n_theta, n_lambda = len(angles), len(lambda_grid)
    normal = (n_theta == 1) and np.isclose(angles[0], 0.0)
    # (name, s_amp, p_amp): TE = s-polarised, TM = p-polarised.
    pols = [("te", 1.0, 0.0)] if normal else [("te", 1.0, 0.0), ("tm", 0.0, 1.0)]

    out = {p[0]: {k: np.zeros((n_lambda, n_theta)) for k in
                  ("ref", "tran", "abs", "abs_si")} for p in pols}

    for it, theta_deg in enumerate(angles):
        theta = np.deg2rad(theta_deg)
        for pol_name, s_amp, p_amp in pols:
            for il, lam in enumerate(lambda_grid):
                obj = grcwa.obj(nG, L1, L2, 1.0 / lam, theta, 0.0, verbose=0)
                for i, layer in enumerate(structure.layers):
                    if i in masks:
                        obj.Add_LayerGrid(layer.thickness, nx, ny)
                    else:
                        obj.Add_LayerUniform(
                            layer.thickness, complex(eps_funcs[layer.background](lam)))
                obj.Init_Setup()
                obj.MakeExcitationPlanewave(p_amp, 0.0, s_amp, 0.0, order=0)
                if grid_indices:
                    ep_all = []
                    for i in grid_indices:
                        layer = structure.layers[i]
                        epg = np.full((nx, ny), complex(eps_funcs[layer.background](lam)),
                                      dtype=complex)
                        for mask, mat in masks[i]:
                            epg[mask] = complex(eps_funcs[mat](lam))
                        ep_all.append(epg.flatten())
                    obj.GridLayer_geteps(np.concatenate(ep_all))

                R, T = obj.RT_Solve(normalize=1)
                R, T = float(np.real(R)), float(np.real(T))
                A = 1.0 - R - T

                a_si = 0.0
                if si_idx is not None:
                    a_si = _layer_absorption(obj, GetZPoyntingFlux, si_idx)
                    a_si = float(np.clip(a_si, 0.0, max(A, 0.0)))

                d = out[pol_name]
                d["ref"][il, it] = R
                d["tran"][il, it] = T
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


def _layer_absorption(obj, get_flux, layer_idx: int) -> float:
    """Absorptance within one layer = net z-Poynting flux in at its top minus
    out at its bottom, normalised like ``RT_Solve`` (net_top - net_bottom).
    """
    thickness = obj.thickness_list[layer_idx]
    kp, phi, q = obj.kp_list[layer_idx], obj.phi_list[layer_idx], obj.q_list[layer_idx]
    a_top, b_top = obj.GetAmplitudes(layer_idx, 0.0)
    f0, b0 = get_flux(a_top, b_top, obj.omega, kp, phi, q)
    a_bot, b_bot = obj.GetAmplitudes(layer_idx, thickness)
    f1, b1 = get_flux(a_bot, b_bot, obj.omega, kp, phi, q)
    return float(np.real(((f0 + b0) - (f1 + b1)) * obj.normalization))
