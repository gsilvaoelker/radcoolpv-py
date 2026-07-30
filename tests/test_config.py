import numpy as np
import pytest

from radcoolpv import config as cm


def _base():
    return {
        "run": {"optics": True, "thermal": False, "plots": False},
        "simulation": {
            "wavelength": {"min": 8.0, "max": 13.0, "n": 3},
            "angles": "normal",
        },
        "geometry": {
            "source": "s4", "shape": "flat",
            "photonic_material": "vacuum",
        },
        "structure": [
            {"material": "silicon", "thickness": 10.0},
            {"material": "vacuum", "thickness": 0.0, "terminal": True},
        ],
        "materials": {"silicon": "SiliconNew"},
    }


def test_specific_direction_and_tm_are_yaml_configurable():
    raw = _base()
    raw["simulation"].update({
        "angles": "specific",
        "polar_angle_deg": 37.5,
        "azimuth_angle_deg": 123.0,
        "polarization": "TM",
    })
    cfg = cm.from_dict(raw)
    theta, phi, weight = cfg.direction_arrays()
    assert np.array_equal(theta, [37.5])
    assert np.array_equal(phi, [123.0])
    assert np.array_equal(weight, [1.0])
    assert cfg.simulation.polarization_names() == ["tm"]


def test_hemispherical_quadrature_is_normalized_and_has_azimuths():
    raw = _base()
    raw["simulation"].update({
        "angles": "hemispherical",
        "hemisphere_theta_points": 3,
        "hemisphere_azimuth_points": 4,
    })
    cfg = cm.from_dict(raw)
    theta, phi, weight = cfg.direction_arrays()
    assert len(theta) == 1 + 3 * 4
    assert weight[0] == 0.0
    assert weight.sum() == pytest.approx(1.0)
    assert set(phi[1:]) == {0.0, 90.0, 180.0, 270.0}


@pytest.mark.parametrize("change,match", [
    ({"wavelength": {"min": -1.0, "max": 2.0, "n": 3}}, "0 < min < max"),
    ({"s4_modes": 0}, "s4_modes"),
])
def test_invalid_numerical_inputs_fail_early(change, match):
    raw = _base()
    raw["simulation"].update(change)
    with pytest.raises(cm.ConfigError, match=match):
        cm.from_dict(raw)


def test_exactly_one_last_terminal_layer_is_required():
    raw = _base()
    raw["structure"].insert(
        1, {"material": "vacuum", "thickness": 0.0, "terminal": True})
    with pytest.raises(cm.ConfigError, match="exactly one"):
        cm.from_dict(raw)


def test_one_yaml_can_define_multiple_named_cases(tmp_path):
    path = tmp_path / "cases.yaml"
    path.write_text("""
cases:
  - name: first
    run: {optics: false, thermal: false, mode: spectral_compare}
    comparison:
      spectra: [{label: reference, file: reference.txt}]
  - name: second
    run: {optics: false, thermal: false, mode: spectral_compare}
    comparison:
      spectra: [{label: reference, file: reference.txt}]
""")

    configs = cm.load_cases(str(path))

    assert [cfg.case_name for cfg in configs] == ["first", "second"]
    with pytest.raises(cm.ConfigError, match="2 cases"):
        cm.load(str(path))
