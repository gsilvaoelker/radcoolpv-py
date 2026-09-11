"""The three-block schema: what is present is computed, and errors name the key."""

import numpy as np
import pytest

from radcoolpv import config as cm


def _s4():
    return {
        "wavelength": {"min": 8.0, "max": 13.0, "n": 3},
        "angles": "normal",
        "structure": [{"material": "silicon", "thickness": 10.0}],
        "materials": {"silicon": "SiliconNew"},
    }


def test_blocks_switch_on_by_presence():
    cfg = cm.from_dict({"optics": _s4()})
    assert cfg.thermal is None and cfg.cell is None
    cfg = cm.from_dict({"optics": {"file": "x.txt", "column": 1},
                        "thermal": {}, "cell": {"silicon_thickness": 500}})
    assert cfg.thermal.ambient_temperature == 298.0
    assert cfg.cell.silicon_thickness == 500


def test_optics_is_a_file_or_a_structure_never_both_or_neither():
    with pytest.raises(cm.ConfigError, match="exactly one"):
        cm.from_dict({"optics": {}})
    with pytest.raises(cm.ConfigError, match="exactly one"):
        cm.from_dict({"optics": dict(_s4(), file="x.txt")})


def test_a_file_spectrum_with_a_cell_needs_the_silicon_thickness():
    with pytest.raises(cm.ConfigError, match="silicon_thickness"):
        cm.from_dict({"optics": {"file": "x.txt", "column": 1},
                      "thermal": {}, "cell": {}})


def test_a_structure_with_a_cell_reads_the_silicon_layer():
    cfg = cm.from_dict({"optics": dict(_s4(), angles="hemispherical"),
                        "thermal": {}, "cell": {}})
    assert cfg.silicon_thickness() == 10.0
    with pytest.raises(cm.ConfigError, match="do not set it as well"):
        cm.from_dict({"optics": dict(_s4(), angles="hemispherical"),
                      "thermal": {}, "cell": {"silicon_thickness": 5.0}})


def test_cell_needs_thermal():
    with pytest.raises(cm.ConfigError, match="cell needs thermal"):
        cm.from_dict({"optics": {"file": "x.txt", "column": 1},
                      "cell": {"silicon_thickness": 500}})


def test_thermal_from_a_live_structure_needs_hemispherical_optics():
    with pytest.raises(cm.ConfigError, match="hemispherical"):
        cm.from_dict({"optics": _s4(), "thermal": {}})


def test_a_typo_names_the_block_and_the_valid_keys():
    with pytest.raises(cm.ConfigError, match="thermal.*convection_coefficient"):
        cm.from_dict({"optics": {"file": "x.txt", "column": 1},
                      "thermal": {"convection_coeficient": 5}})
    with pytest.raises(cm.ConfigError, match="unknown top-level keys"):
        cm.from_dict({"optics": {"file": "x.txt", "column": 1}, "run": {}})


def test_tm_polarization_and_normal_incidence_are_yaml_configurable():
    cfg = cm.from_dict({"optics": dict(_s4(), polarization="TM")})
    theta, phi, weight = cfg.direction_arrays()
    assert np.array_equal(theta, [0.0]) and np.array_equal(weight, [1.0])
    assert cfg.optics.polarization_names() == ["tm"]


def test_hemispherical_quadrature_is_normalized_and_has_azimuths():
    cfg = cm.from_dict({"optics": dict(
        _s4(), angles="hemispherical",
        hemisphere_theta_points=3, hemisphere_azimuth_points=4)})
    theta, phi, weight = cfg.direction_arrays()
    assert len(theta) == 1 + 3 * 4
    assert weight[0] == 0.0
    assert weight.sum() == pytest.approx(1.0)
    assert set(phi[1:]) == {0.0, 90.0, 180.0, 270.0}


@pytest.mark.parametrize("change,match", [
    ({"wavelength": {"min": -1.0, "max": 2.0, "n": 3}}, "0 < min < max"),
    ({"s4_modes": 0}, "s4_modes"),
    ({"structure": [{"material": "silicon", "thickness": 0.0}]}, "thicknesses must be > 0"),
    ({"materials": {}}, "not declared"),
])
def test_invalid_structure_inputs_fail_early(change, match):
    with pytest.raises(cm.ConfigError, match=match):
        cm.from_dict({"optics": dict(_s4(), **change)})


def test_the_temperature_sweep_must_contain_ambient_when_a_cell_is_solved():
    raw = {"optics": {"file": "x.txt", "column": 1},
           "thermal": {"ambient_temperature": 300.0,
                       "temperatures": {"min": 400.0, "max": 500.0, "n": 51}}}
    cm.from_dict(raw)                                   # a cooling curve may sweep anywhere
    raw["cell"] = {"silicon_thickness": 500}
    with pytest.raises(cm.ConfigError, match="ambient temperature"):
        cm.from_dict(raw)


def test_one_yaml_can_define_multiple_named_cases(tmp_path):
    path = tmp_path / "cases.yaml"
    path.write_text("""
cases:
  - name: first
    optics: {file: reference.txt, column: 1}
  - name: second
    optics: {file: reference.txt, column: 2}
""")
    configs = cm.load_cases(str(path))
    assert [cfg.case_name for cfg in configs] == ["first", "second"]
    with pytest.raises(cm.ConfigError, match="2 cases"):
        cm.load(str(path))


def test_a_single_case_is_named_after_its_file(tmp_path):
    path = tmp_path / "my_module.yaml"
    path.write_text("optics: {file: reference.txt, column: 1}\n")
    assert cm.load(str(path)).case_name == "my_module"
