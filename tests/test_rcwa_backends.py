"""Validate the RCWA optics backends.

Every engine is checked against the analytic transfer-matrix method (`tmm`) for
uniform (flat) stacks - where TMM is exact - across incidence angle and
polarisation, and against energy conservation for patterned stacks. The tests
are parameterised over the backend, so an engine cannot be swapped in without
satisfying the same physics the previous one did.

The tolerance is per-backend: S4 solves uniform layers exactly (agreement is at
machine precision), whereas grcwa rasterises every patterned layer onto an
Nx x Ny grid and is correspondingly looser.
"""

import numpy as np
import pytest

tmm = pytest.importorskip("tmm")

from radcoolpv import config as config_module
from radcoolpv.materials import registry
from radcoolpv.optics import geometry

_MATS = {"sio2": "PalikKitamura_SiO2", "silicon": "SiliconNew",
         "substrate": "Hagemann_Ag"}

# (module name, config source name, flat-stack tolerance, patterned tolerance)
_BACKENDS = [
    ("s4_backend", "s4", 1e-9, 1e-6),
    ("grcwa_backend", "grcwa", 3e-3, 1e-4),
]


@pytest.fixture(params=_BACKENDS, ids=[b[1] for b in _BACKENDS])
def backend(request):
    """Yield an importable backend, skipping engines that are not built."""
    import importlib

    mod_name, source, flat_tol, patt_tol = request.param
    mod = importlib.import_module(f"radcoolpv.optics.{mod_name}")
    if not mod.is_available():
        pytest.skip(f"{source} engine is not installed")
    return mod, source, flat_tol, patt_tol


def _cfg(source, photonic="vacuum", shape="flat", cyl=None):
    raw = {
        "run": {"optics": True, "thermal": False, "plots": False},
        "simulation": {"wavelength": {"min": 8.0, "max": 10.0, "n": 3},
                       "angles": "normal", "rcwa_modes": 40,
                       "grid_nx": 64, "grid_ny": 64},
        "geometry": {"source": source, "shape": shape,
                     "photonic_material": photonic,
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


def test_flat_normal_matches_tmm(backend):
    mod, source, tol, _ = backend
    raw = mod.sweep(_cfg(source), LAMBDAS, np.array([0.0]))
    for i, lam in enumerate(LAMBDAS):
        R, T, a_si = _tmm_flat(lam, 0.0, "s")
        assert raw.ref_te[i, 0] == pytest.approx(R, abs=tol)
        assert raw.tran_te[i, 0] == pytest.approx(T, abs=tol)
        assert raw.abs_te[i, 0] == pytest.approx(1.0 - R - T, abs=tol)
        assert raw.abs_si_te[i, 0] == pytest.approx(a_si, abs=tol)


def test_flat_oblique_te_tm_matches_tmm(backend):
    mod, source, tol, _ = backend
    raw = mod.sweep(_cfg(source), LAMBDAS, np.array([60.0]))   # non-normal -> TE + TM
    for i, lam in enumerate(LAMBDAS):
        Rte, Tte, _ = _tmm_flat(lam, 60.0, "s")
        Rtm, Ttm, _ = _tmm_flat(lam, 60.0, "p")
        assert raw.ref_te[i, 0] == pytest.approx(Rte, abs=tol)
        assert raw.ref_tm[i, 0] == pytest.approx(Rtm, abs=tol)
        assert raw.tran_te[i, 0] == pytest.approx(Tte, abs=tol)
        assert raw.tran_tm[i, 0] == pytest.approx(Ttm, abs=tol)


def test_pattern_path_reduces_to_flat(backend):
    """An all-vacuum cylinder layer exercises the patterning code path but is
    physically transparent, so it must reproduce the flat tmm result."""
    mod, source, tol, _ = backend
    cfg = _cfg(source, photonic="vacuum", shape="cylinder",
               cyl={"radius": 1.5, "height": 2.0})
    raw = mod.sweep(cfg, LAMBDAS, np.array([0.0]))
    for i, lam in enumerate(LAMBDAS):
        R, T, _ = _tmm_flat(lam, 0.0, "s")
        assert raw.ref_te[i, 0] == pytest.approx(R, abs=tol)
        assert raw.tran_te[i, 0] == pytest.approx(T, abs=tol)


def test_patterned_energy_conservation(backend):
    """A real SiO2 microcylinder array must conserve energy (R + T + A = 1)."""
    mod, source, _, tol = backend
    cfg = _cfg(source, photonic="sio2", shape="cylinder",
               cyl={"radius": 1.5, "height": 2.0})
    raw = mod.sweep(cfg, LAMBDAS, np.array([0.0]))
    total = raw.ref_te[:, 0] + raw.tran_te[:, 0] + raw.abs_te[:, 0]
    assert np.allclose(total, 1.0, atol=tol)
    for arr in (raw.ref_te, raw.tran_te, raw.abs_te, raw.abs_si_te):
        assert np.all(arr[:, 0] >= -1e-6)
        assert np.all(arr[:, 0] <= 1.0 + 1e-6)


def test_resolve_eps_is_shared(backend):
    """Both backends must map config material names through the same helper."""
    mod, source, _, _ = backend
    assert mod.resolve_eps is geometry.resolve_eps
    funcs = geometry.resolve_eps(_cfg(source))
    assert set(funcs) >= {"vacuum", "sio2", "silicon", "substrate"}
    assert np.iscomplexobj(np.asarray(funcs["sio2"](LAMBDAS)))


def test_backends_agree_on_patterned_structure():
    """S4 (analytic circle) and grcwa (rasterised grid) must agree on the same
    patterned structure. This is the only direct cross-engine check: it is what
    licenses trusting S4 results where no analytic reference exists.

    The residual is dominated by grcwa's staircase discretisation of the circle,
    so the tolerance is looser than either engine's own flat-stack accuracy.
    """
    from radcoolpv.optics import grcwa_backend, s4_backend

    if not (s4_backend.is_available() and grcwa_backend.is_available()):
        pytest.skip("cross-engine check needs both S4 and grcwa built")

    cyl = {"radius": 1.5, "height": 2.0}
    kw = dict(photonic="sio2", shape="cylinder", cyl=cyl)
    a = s4_backend.sweep(_cfg("s4", **kw), LAMBDAS, np.array([0.0]))
    b = grcwa_backend.sweep(_cfg("grcwa", **kw), LAMBDAS, np.array([0.0]))

    assert np.allclose(a.ref_te, b.ref_te, atol=2e-3)
    assert np.allclose(a.tran_te, b.tran_te, atol=2e-3)
    assert np.allclose(a.abs_si_te, b.abs_si_te, atol=2e-3)
