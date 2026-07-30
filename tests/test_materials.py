"""Tests for the material registry, tabulated loader, and analytic models."""

import os

import numpy as np
import pytest

from radcoolpv.materials import registry, tabulated

USED_MODELS = [
    "PalikKitamura_SiO2", "SiliconNew", "Rubin_SodaLime",
    "GuptaQuerry_PDMS", "Hagemann_Ag", "Jaramillo_NILresist", "DrudeSi3N4",
]

DATA_DIR = os.path.join(os.path.dirname(registry.__file__), "data")


def test_all_used_models_resolve():
    avail = registry.available()
    for name in USED_MODELS:
        assert name in avail, f"{name} not registered"
        assert callable(registry.get(name))


def test_unknown_model_raises():
    with pytest.raises(KeyError):
        registry.get("DefinitelyNotAModel")


@pytest.mark.parametrize("name", [m for m in USED_MODELS if m != "DrudeSi3N4"])
def test_tabulated_covers_simulation_range_without_nan(name):
    csv = os.path.join(DATA_DIR, f"{name}.csv")
    lam_t, _, _ = tabulated.load_table(csv)
    lam = np.linspace(lam_t[0], lam_t[-1], 500)
    eps = registry.get(name)(lam)
    assert eps.shape == lam.shape
    assert np.all(np.isfinite(eps)), f"{name} produced non-finite eps in its table"


def test_tabulated_rejects_out_of_range_wavelengths():
    with pytest.raises(ValueError, match="outside tabulated range"):
        registry.get("Jaramillo_NILresist")(30.0)


def test_tabulated_matches_nk_formula_at_node_and_midpoint():
    # Use the SiO2 table; check eps == (n + i k)^2 at a node and a midpoint.
    csv = os.path.join(DATA_DIR, "PalikKitamura_SiO2.csv")
    lam_t, n_t, k_t = tabulated.load_table(csv)
    eps = tabulated.make_tabulated(csv)

    # Exact node.
    i = 50
    expected_node = (n_t[i] + 1j * k_t[i]) ** 2
    assert np.isclose(eps(lam_t[i]), expected_node, rtol=1e-12)

    # Midpoint between two nodes -> linear interpolation of n and k.
    lam_mid = 0.5 * (lam_t[i] + lam_t[i + 1])
    n_mid = 0.5 * (n_t[i] + n_t[i + 1])
    k_mid = 0.5 * (k_t[i] + k_t[i + 1])
    assert np.isclose(eps(lam_mid), (n_mid + 1j * k_mid) ** 2, rtol=1e-9)


def test_silicon_known_first_node():
    # SiliconNew first row: 0.28  2.919769  5.28592321
    eps = registry.get("SiliconNew")(0.28)
    assert np.isclose(eps, (2.919769 + 5.28592321j) ** 2, rtol=1e-9)


def test_refractiveindex_info_olmon_ev_gold():
    eps = registry.get("RII_Olmon_2012_ev_Au")(0.3)
    assert np.isclose(eps, (1.596 + 1.888j) ** 2, rtol=1e-12)
    with pytest.raises(ValueError, match="outside tabulated range"):
        registry.get("RII_Olmon_2012_ev_Au")(25.0)


def test_akerboom_silicon_uses_inherited_index_without_ir_loss():
    eps = registry.get("Akerboom_Si_lossless")(
        np.array([2.0, 8.0, 16.0]))
    assert np.all(np.isreal(eps))
    assert np.sqrt(eps) == pytest.approx(
        [3.449085553844084, 3.4221846985472157, 3.41981831086898])


def test_drude_si3n4_is_lossy_in_ir():
    lam = np.array([8.0, 10.0, 13.0])  # atmospheric window
    eps = registry.get("DrudeSi3N4")(lam)
    assert np.all(np.isfinite(eps))
    assert np.all(eps.imag > 0), "Si3N4 should be lossy (Im eps > 0) in the IR"
