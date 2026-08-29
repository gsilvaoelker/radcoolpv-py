"""The one validation: Akerboom et al., ACS Photonics 9 (2022) 3831-3840.

One YAML, three groups. A computes the optics with S4, B runs the thermal model
alone from the digitized measured emittance, and C is the full optical, thermal
and electrical result. Only the B group runs here: A and C need a compiled S4.
"""

import os

import numpy as np
import pytest

from radcoolpv import config, pipeline
from radcoolpv._compat import trapz
from radcoolpv.io.results import OpticsResult
from radcoolpv.thermal import energy_balance
from radcoolpv.thermal.spectra import SolarSpectrum

ROOT = os.path.join(os.path.dirname(__file__), "..", "validation")
YAML = os.path.join(ROOT, "akerboom.yaml")
FIG3A = os.path.join(ROOT, "data", "fig3a_calculated_emittance.txt")
FIG5A = os.path.join(ROOT, "data", "fig5a_measured_emittance.txt")
FIG5B = os.path.join(ROOT, "data", "fig5b_cooling_power.txt")


def _cases():
    return {cfg.case_name: cfg for cfg in config.load_cases(YAML)}


def _zero_crossing(x, y):
    i = np.where(y >= 0.0)[0][0]
    return float(np.interp(0.0, y[i - 1:i + 1], x[i - 1:i + 1]))


def test_one_yaml_defines_all_optical_and_thermal_cases():
    assert set(_cases()) == {
        "A1_optics_bare", "A2_optics_flat_silica", "A3_optics_cylinders",
        "B1_cooling_h6_bare", "B2_cooling_h6_flat_silica",
        "B3_cooling_h6_cylinders",
        "B4_cooling_fitted_bare", "B5_cooling_fitted_flat_silica",
        "B6_cooling_fitted_cylinders",
        "C1_pv_bare", "C2_pv_flat_silica", "C3_pv_cylinders",
    }


def test_yaml_uses_paper_geometry_and_material_models():
    cases = _cases()
    cyl = cases["A3_optics_cylinders"]

    assert cyl.geometry.cylinder == {"radius": 1.75, "height": 2.25}
    assert cyl.geometry.lattice.x == pytest.approx(np.sqrt(3.0) * 6.125)
    assert cyl.geometry.lattice.y == pytest.approx(6.125)
    assert [(layer.material, layer.thickness) for layer in cyl.structure[:-1]] == [
        ("sio2", 500.0),
        ("silicon", 500.0),
        ("gold", 0.08),
    ]
    assert cyl.materials == {
        "sio2": "PalikKitamura_SiO2",
        "silicon": "Akerboom_Si_lossless",
        "gold": "RII_Olmon_2012_ev_Au",
    }


@pytest.mark.parametrize("column,paper_average", [(2, 0.843), (3, 0.977)])
def test_digitized_measured_emittance_preserves_reported_average(
        column, paper_average):
    data = np.loadtxt(FIG5A)
    band = (data[:, 0] >= 7.5) & (data[:, 0] <= 16.0)
    average = trapz(data[band, column], data[band, 0]) / 8.5
    assert average == pytest.approx(paper_average, abs=0.005)


@pytest.mark.parametrize(
    "column,paper_temperature",
    [(1, 360.0), (2, 339.0), (3, 336.0)],
)
def test_digitized_cooling_curves_preserve_reported_zero_crossings(
        column, paper_temperature):
    data = np.loadtxt(FIG5B)
    assert _zero_crossing(data[:, 0], data[:, column]) == pytest.approx(
        paper_temperature, abs=0.6)


@pytest.mark.parametrize(
    "case_name,calculated_temperature",
    [
        ("B1_cooling_h6_bare", 415.4),
        ("B2_cooling_h6_flat_silica", 360.6),
        ("B3_cooling_h6_cylinders", 355.6),
    ],
)
def test_paper_stated_convection_coefficient_exposes_temperature_mismatch(
        case_name, calculated_temperature, tmp_path):
    cfg = _cases()[case_name]
    cfg.run.plots = False
    cfg.run.write_outputs = False
    cfg.run.results_dir = str(tmp_path / case_name)
    result = pipeline.run(cfg).thermal

    assert cfg.thermal.convection_coefficient == pytest.approx(6.0)
    assert result.equil_temp == pytest.approx(calculated_temperature, abs=0.1)


def test_paper_zero_emitter_exposes_convection_inconsistency():
    cfg = _cases()["B1_cooling_h6_bare"]
    grid = cfg.wavelength_array()
    zeros = np.zeros_like(grid)
    optics = OpticsResult(
        lambda_um=grid,
        ref=np.ones_like(grid),
        tran=zeros,
        emit=zeros,
        abs_silicon=zeros,
        emit_atm=zeros,
        emitt_spec_times_emit_atm=zeros,
        angles="hemispherical",
    )
    solar = SolarSpectrum(
        lambda_um=grid,
        irradiance_per_um=zeros,
        photon_flux=zeros,
        total_am15=0.0,
        raw_lambda_um=grid,
        raw_irradiance_per_um=zeros,
    )

    result = energy_balance.run(cfg, optics, solar)

    assert result.equil_temp == pytest.approx(300.0 + 808.0 / 6.0)
    assert result.equil_temp != pytest.approx(366.5, abs=0.1)


@pytest.mark.parametrize(
    "case_name,paper_temperature,column",
    [
        ("B4_cooling_fitted_bare", 360.0, 1),
        ("B5_cooling_fitted_flat_silica", 339.0, 2),
        ("B6_cooling_fitted_cylinders", 336.0, 3),
    ],
)
def test_inferred_convection_coefficient_reproduces_figure_5b(
        case_name, paper_temperature, column, tmp_path):
    cfg = _cases()[case_name]
    cfg.run.plots = False
    cfg.run.write_outputs = False
    cfg.run.results_dir = str(tmp_path / case_name)
    result = pipeline.run(cfg).thermal

    reference = np.loadtxt(FIG5B)
    paper_power = np.interp(
        result.emit_temp, reference[:, 0], reference[:, column])
    rmse = np.sqrt(np.mean((result.cool_power - paper_power) ** 2))

    assert cfg.thermal.convection_coefficient == pytest.approx(12.54)
    assert result.equil_temp == pytest.approx(paper_temperature, abs=1.6)
    assert rmse < 50.0


def test_digitized_calculated_emittance_is_complete():
    data = np.loadtxt(FIG3A)
    assert data.shape == (281, 4)
    assert data[0, 0] == pytest.approx(2.0)
    assert data[-1, 0] == pytest.approx(16.0)
    assert np.all((data[:, 1:] >= 0.0) & (data[:, 1:] <= 1.0))


def test_pv_group_uses_lossy_silicon():
    """Group C cannot inherit the paper's lossless silicon.

    ``Akerboom_Si_lossless`` is the paper's own cooling-band assumption, k = 0
    at every wavelength. That is right for groups A and B and fatal for C: with
    no absorption in the silicon, Jsc integrates to zero and the cell reports a
    few millivolts instead of an operating point. The two groups therefore have
    to disagree about the silicon table, which is easy to lose in a refactor.
    """
    cases = _cases()
    for name in ("C1_pv_bare", "C2_pv_flat_silica", "C3_pv_cylinders"):
        assert cases[name].materials["silicon"] == "Palik_Si"
    for name in ("A1_optics_bare", "A2_optics_flat_silica", "A3_optics_cylinders"):
        assert cases[name].materials["silicon"] == "Akerboom_Si_lossless"


def test_pv_group_wavelength_range_stays_inside_the_gold_table():
    """RII_Olmon_2012_ev_Au is tabulated to 24.93 um and refuses to extrapolate."""
    from radcoolpv.materials import registry
    for name in ("C1_pv_bare", "C2_pv_flat_silica", "C3_pv_cylinders"):
        grid = _cases()[name].wavelength_array()
        for model in ("RII_Olmon_2012_ev_Au", "Palik_Si", "PalikKitamura_SiO2"):
            registry.get(model)(grid)   # raises if the range is out of bounds
