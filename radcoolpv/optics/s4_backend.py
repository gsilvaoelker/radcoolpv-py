"""RCWA optics via the Stanford S4 Python bindings.

Calls the S4 Python module (``import S4``) directly, replacing the original
MATLAB-writes-Lua-files-and-shell-calls-S4 dance. The structure is built once
and only ``SetMaterial`` / ``SetFrequency`` are re-issued per wavelength.

Patterns are **analytic** (``SetRegionCircle`` / ``SetRegionRectangle``) rather
than rasterised onto a grid, so curved shapes carry no staircase approximation,
and uniform layers are solved exactly (agreement with analytic TMM is ~5e-15).

S4 is imported lazily so the rest of the package works without it.
"""

from __future__ import annotations

from typing import Dict

import numpy as np

from ..config import Config
from . import directional
from .directional import RawOptics
from .geometry import S4Structure, build_structure, resolve_eps, used_materials

_INSTALL_HINT = (
    "The S4 Python module is not installed. S4 has no PyPI package and must be "
    "built from source:\n"
    "    brew install fftw suite-sparse openblas lapack boost\n"
    "    git clone https://github.com/phoebe-p/S4 && cd S4\n"
    "    make -f Makefile.m1 S4_pyext      # Apple silicon; else: make S4_pyext\n"
    "Alternatively use geometry.source: freeform, or resume from a pre-computed "
    "optics results folder."
)


# S4 is a C++ extension compiled against the numpy 1.x ABI, so an interpreter
# carrying numpy >= 2 raises on import even though the .so is present and fine.
# Reporting that as "not installed" sends you off to rebuild a working build.
_ABI_HINT = (
    "S4 is installed at {path}, but this interpreter cannot load it:\n"
    "    {exc}\n"
    "S4 was compiled against the numpy 1.x ABI and this interpreter has numpy "
    "{numpy}. The build is fine; the interpreter is wrong.\n"
    "Pin this environment with:  pip install 'numpy<2'\n"
    "or run from one that already is, naming the interpreter outright rather "
    "than relying on a python3 alias to follow the activated environment."
)


def _import_failure():
    """None if ``import S4`` succeeds, else a message naming the actual cause."""
    try:
        import S4  # noqa: F401
        return None
    except ImportError as exc:
        if "numpy" not in str(exc).lower():
            return _INSTALL_HINT
        spec = None
        try:
            import importlib.util
            spec = importlib.util.find_spec("S4")
        except Exception:
            pass
        return _ABI_HINT.format(
            path=(spec.origin if spec is not None else "an unknown location"),
            exc=exc, numpy=np.__version__)
    except Exception as exc:
        return f"S4 is present but failed to import: {type(exc).__name__}: {exc}"


def is_available() -> bool:
    """True if the S4 Python module can be imported.

    A pure predicate: callers use it to skip, never to diagnose. ``sweep``
    reports *why* the import failed via :func:`_import_failure`.
    """
    return _import_failure() is None


def _build_sim(structure: S4Structure, num_basis: int, eps0: Dict[str, complex]):
    """Construct the S4 simulation once, with placeholder (first-wavelength) eps."""
    import S4

    sim = S4.New(Lattice=structure.lattice, NumBasis=int(num_basis))
    for name in used_materials(structure):
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


def _fluxes(sim, structure: S4Structure):
    """R, T, A and silicon absorptance at the current (lambda, angle).

    Every flux is normalised by the incident flux.

    This is a deliberate, documented **divergence from the MATLAB reference**.
    ``SiO2Spheres-v5.lua`` normalises R and the per-layer absorptances but not T::

        reflection_flux_vacuum   = (-1) * reflection_flux_vacuum / incidence_flux
        transmission_flux        = S:GetPoyntingFlux('layerBottom', 0.0)
        transmission_flux_vacuum = transmission_flux / incidence_flux   -- never used
        absorption_flux          = 1 - reflection_flux_vacuum - transmission_flux

    so the Lua mixes a normalised R with a raw T, both in the T column it writes
    and in ``A = 1 - R - T``. Incident flux through a z-plane carries cos(theta),
    making the raw column correct only at normal incidence and low by cos(theta)
    elsewhere - a factor of ~11 at the 85 degree end of a hemispherical sweep.

    The practical impact on the published results is negligible because those
    stacks are opaque: in the committed ``OUTPUTS4`` reference the T column peaks
    at 5.4e-3 and averages 2.6e-5, bounding the error in A by |T|(1 - cos theta).
    Normalising here is therefore strictly more correct and numerically
    indistinguishable for opaque structures, but it does matter for any
    transmissive stack, which is why the engine does it properly.
    """
    inc, refl = sim.GetPowerFlux(Layer=structure.top_layer, zOffset=0)
    inc, refl = np.real(inc), np.real(refl)
    t_fwd = np.real(sim.GetPowerFlux(Layer=structure.bottom_layer, zOffset=0)[0]) / inc

    R = -refl / inc
    A = 1.0 - R - t_fwd

    a_si = 0.0
    if structure.silicon_layer is not None:
        # Absorptance inside Si is the net flux difference between its own two
        # interfaces. Using terminal-layer flux would incorrectly attribute any
        # downstream absorbing layer to silicon.
        f_si, b_si = sim.GetPowerFlux(Layer=structure.silicon_layer, zOffset=0)
        f_b, b_b = sim.GetPowerFlux(
            Layer=structure.silicon_layer,
            zOffset=structure.silicon_thickness)
        a_si = (np.real(f_si) + np.real(b_si) - np.real(f_b) - np.real(b_b)) / inc

    return R, t_fwd, A, a_si


def sweep(cfg: Config, lambda_grid: np.ndarray,
          angles_deg: np.ndarray = None) -> RawOptics:
    """Run S4 and return per-(wavelength, direction) raw optics.

    ``angles_deg`` is retained only for compact solver-level tests and MATLAB
    parity. Production runs obtain polar angle, azimuth, and weights from YAML.
    """
    failure = _import_failure()
    if failure is not None:
        raise RuntimeError(failure)

    structure = build_structure(cfg)
    eps_funcs = resolve_eps(cfg)
    mats = used_materials(structure)

    if angles_deg is None:
        theta, phi, weights = cfg.direction_arrays()
        mode = cfg.simulation.angles
    else:
        theta = np.asarray(angles_deg, dtype=float)
        phi = np.zeros_like(theta)
        weights = np.ones_like(theta)
        mode = ("normal" if len(theta) == 1 and np.isclose(theta[0], 0.0)
                else "specific")
    pols = directional.polarisations(
        cfg.simulation.polarization_names())
    n_lambda, n_direction = len(lambda_grid), len(theta)
    out = directional.new_accumulator(pols, n_lambda, n_direction)

    # Pre-evaluate eps for every material over the whole grid (vectorised), then
    # build the simulation once using the first wavelength's values.
    eps_grid = {m: np.asarray(eps_funcs[m](lambda_grid), dtype=complex) for m in mats}
    sim = _build_sim(structure, cfg.simulation.s4_modes,
                     {m: eps_grid[m][0] for m in mats})

    for it, (polar, azimuth) in enumerate(zip(theta, phi)):
        for pol_name, s_amp, p_amp in pols:
            sim.SetExcitationPlanewave(
                                       IncidenceAngles=(float(polar), float(azimuth)),
                                       sAmplitude=s_amp, pAmplitude=p_amp, Order=0)
            for il, lam in enumerate(lambda_grid):
                for m in mats:
                    sim.SetMaterial(Name=m, Epsilon=complex(eps_grid[m][il]))
                sim.SetFrequency(1.0 / lam)   # S4 frequency = 1/lambda (lattice in um)

                R, t_fwd, A, a_si = _fluxes(sim, structure)
                d = out[pol_name]
                d["ref"][il, it] = R
                d["tran"][il, it] = t_fwd
                d["abs"][il, it] = A
                d["abs_si"][il, it] = a_si

    return directional.pack_raw(
        out, theta, phi, weights, lambda_grid, mode,
        cfg.simulation.polarization)
