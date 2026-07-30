"""Load and validate the YAML configuration.

A single YAML file drives the whole run. It is parsed into typed dataclasses
with defaults, light validation, and a few derived helpers (wavelength grid,
angle list, silicon thickness). The ``simulation`` section is shared by both
stages so the optics and thermal calculations can never drift apart.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import yaml


class ConfigError(ValueError):
    """Raised when the YAML config is missing or inconsistent."""


class _LinspaceSweep:
    """Mixin for the ``min``/``max``/``n`` sweep sections.

    Declares no fields, so subclasses stay plain dataclasses and remain free to
    choose their own defaults (or require explicit values).
    """

    def array(self) -> np.ndarray:
        return np.linspace(self.min, self.max, self.n)


# --------------------------------------------------------------------------- #
# Dataclasses (mirror the YAML structure).
# --------------------------------------------------------------------------- #

@dataclass
class RunConfig:
    optics: bool = True
    thermal: bool = True
    plots: bool = True
    mode: str = "standard"  # standard | test | cooling_curve | spectral_compare
    results_dir: str = "results"
    write_outputs: bool = True
    optics_results: Optional[str] = None  # resume a prior optics run
    optics_results_angles: str = "hemispherical"
    optics_results_emittance_column: Optional[int] = None


@dataclass
class Wavelength(_LinspaceSweep):
    min: float = 0.3
    max: float = 30.0
    n: int = 2000


@dataclass
class SimulationConfig:
    wavelength: Wavelength = field(default_factory=Wavelength)
    angles: str = "hemispherical"     # normal | specific | hemispherical
    polar_angle_deg: float = 0.0
    azimuth_angle_deg: float = 0.0
    polarization: str = "unpolarized"  # TE | TM | unpolarized
    hemisphere_theta_points: int = 8
    hemisphere_azimuth_points: int = 12
    s4_modes: int = 10              # S4 Fourier truncation (NumBasis)

    def directions(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return polar angles, azimuths, and normalized angular weights.

        A hemispherical run uses Gauss-Legendre nodes in
        ``u = sin(theta)^2`` and a uniform periodic azimuth rule. The first
        direction is an explicit zero-weight normal-incidence probe used by the
        PV luminescence model.
        """
        if self.angles == "normal":
            return (np.array([0.0]), np.array([self.azimuth_angle_deg]),
                    np.array([1.0]))
        if self.angles == "specific":
            return (np.array([self.polar_angle_deg]),
                    np.array([self.azimuth_angle_deg]), np.array([1.0]))
        if self.angles == "hemispherical":
            nodes, weights = np.polynomial.legendre.leggauss(
                self.hemisphere_theta_points)
            u = 0.5 * (nodes + 1.0)
            u_weights = 0.5 * weights
            theta = np.rad2deg(np.arcsin(np.sqrt(u)))
            phi = np.arange(self.hemisphere_azimuth_points, dtype=float)
            phi *= 360.0 / self.hemisphere_azimuth_points
            theta_grid, phi_grid = np.meshgrid(theta, phi, indexing="ij")
            angular_weights = np.repeat(
                u_weights / self.hemisphere_azimuth_points,
                self.hemisphere_azimuth_points)
            return (
                np.concatenate(([0.0], theta_grid.ravel())),
                np.concatenate(([0.0], phi_grid.ravel())),
                np.concatenate(([0.0], angular_weights)),
            )
        raise ConfigError(
            "simulation.angles must be normal|specific|hemispherical, "
            f"got {self.angles!r}")

    def angle_array_deg(self) -> np.ndarray:
        return self.directions()[0]

    def polarization_names(self) -> List[str]:
        value = self.polarization.lower()
        if value == "te":
            return ["te"]
        if value == "tm":
            return ["tm"]
        if value == "unpolarized":
            return ["te", "tm"]
        raise ConfigError(
            "simulation.polarization must be TE|TM|unpolarized, "
            f"got {self.polarization!r}")


@dataclass
class Lattice:
    type: str = "square"              # square | hexagonal
    x: float = 20.0
    y: float = 20.0


@dataclass
class GeometryConfig:
    source: str = "s4"               # s4 | freeform
    shape: str = "flat"              # flat | sphere | semisphere | triangle | cylinder | grating
    photonic_material: str = "sio2"
    lattice: Lattice = field(default_factory=Lattice)
    discretization_layers: int = 1
    sphere: Dict[str, float] = field(default_factory=dict)
    triangle: Dict[str, float] = field(default_factory=dict)
    cylinder: Dict[str, float] = field(default_factory=dict)
    grating: Dict[str, float] = field(default_factory=dict)  # {duty, depth}; period = lattice.x
    freeform: Dict[str, str] = field(default_factory=dict)


@dataclass
class Layer:
    material: str
    thickness: float
    terminal: bool = False


@dataclass
class BandGap:
    eg0: float = 1.166
    alpha: float = 4.73e-4
    beta: float = 636.0


@dataclass
class PVConfig:
    series_resistance: float = 0.00011
    shunt_resistance: float = 0.1
    bandgap: BandGap = field(default_factory=BandGap)
    iqe_file: str = "data/siliconIQE.txt"


@dataclass
class VoltageSweep(_LinspaceSweep):
    min: float = 0.1
    max: float = 0.8
    n: int = 100


@dataclass
class TemperatureSweep(_LinspaceSweep):
    min: float
    max: float
    n: int


@dataclass
class ThermalConfig:
    ambient_temperature: float = 298.0
    convection_coefficient: float = 12.0  # total effective h for the chosen area
    voltage: VoltageSweep = field(default_factory=VoltageSweep)
    equilibrium: str = "auto"        # auto | manual
    cooling_temperature: Optional[TemperatureSweep] = None
    solar_irradiance: Optional[float] = None  # W/m2; cooling_curve-only normalization
    absorbed_solar_power: Optional[float] = None  # W/m2; direct paper/model input
    reference_curve_file: Optional[str] = None
    reference_curve_column: int = 1
    reference_temperature: Optional[float] = None
    emit_temp: float = 319.0         # used only if manual
    vmpp: float = 0.6586             # used only if manual
    pv: PVConfig = field(default_factory=PVConfig)


@dataclass
class DataConfig:
    solar_spectrum: str = "data/astmg173.xlsx"
    atmosphere: str = "data/cptrans_nq_100_15.dat"


@dataclass
class ComparisonConfig:
    spectra: List[Dict[str, str]] = field(default_factory=list)
    xlim: List[float] = field(default_factory=lambda: [2.5, 14.0])
    ylim: List[float] = field(default_factory=lambda: [0.0, 1.0])
    xlabel: str = r"Wavelength, $\lambda$ ($\mu$m)"
    ylabel: str = "Emissivity"
    title: str = "Mid- and LWIR emissivity"
    output_file: str = "spectral_comparison.png"


@dataclass
class Config:
    run: RunConfig = field(default_factory=RunConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    geometry: GeometryConfig = field(default_factory=GeometryConfig)
    structure: List[Layer] = field(default_factory=list)
    materials: Dict[str, str] = field(default_factory=dict)
    thermal: ThermalConfig = field(default_factory=ThermalConfig)
    data: DataConfig = field(default_factory=DataConfig)
    comparison: ComparisonConfig = field(default_factory=ComparisonConfig)
    case_name: Optional[str] = None
    base_dir: str = "."              # directory the config was loaded from
    config_path: Optional[str] = None

    # ----- derived helpers ------------------------------------------------- #
    def wavelength_array(self) -> np.ndarray:
        return self.simulation.wavelength.array()

    def angle_array_deg(self) -> np.ndarray:
        return self.simulation.angle_array_deg()

    def direction_arrays(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.simulation.directions()

    def thick_si(self) -> float:
        """Silicon thickness taken from the structure (single source of truth)."""
        for layer in self.structure:
            if layer.material == "silicon":
                return layer.thickness
        raise ConfigError(
            "No layer with material 'silicon' in `structure`; thermal stage needs it for thickSi."
        )

    def resolve(self, path: Optional[str]) -> Optional[str]:
        """Resolve a path from the config relative to the config's directory."""
        if path is None:
            return None
        if os.path.isabs(path):
            return path
        return os.path.normpath(os.path.join(self.base_dir, path))

    def resolve_data(self, path: Optional[str]) -> Optional[str]:
        """Resolve an input data file.

        Tries, in order: an existing absolute path, a path relative to the
        config's directory, then a file of the same basename bundled in the
        package's ``data/`` folder. This lets configs reference bundled defaults
        (solar spectrum, atmosphere, IQE) by name while still allowing custom
        user-provided files.
        """
        if path is None:
            return None
        if os.path.isabs(path) and os.path.exists(path):
            return path
        cand = os.path.normpath(os.path.join(self.base_dir, path))
        if os.path.exists(cand):
            return cand
        # Fall back to data bundled inside the package (by basename). Works for
        # both files (data/) and resume folders (validation/data/).
        here = os.path.dirname(__file__)
        base = os.path.basename(path)
        for sub in ("data", os.path.join("validation", "data")):
            bundled = os.path.join(here, sub, base)
            if os.path.exists(bundled):
                return bundled
        return cand   # let the caller raise a clear "not found" error


# --------------------------------------------------------------------------- #
# Parsing.
# --------------------------------------------------------------------------- #

def _section(raw: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = raw.get(key) or {}
    if not isinstance(value, dict):
        raise ConfigError(f"`{key}` section must be a mapping, got {type(value).__name__}")
    return value


def from_dict(raw: Dict[str, Any], base_dir: str = ".") -> Config:
    """Build a :class:`Config` from a parsed YAML mapping, applying defaults."""
    raw = raw or {}

    run = RunConfig(**_section(raw, "run"))

    sim_raw = dict(_section(raw, "simulation"))
    if "wavelength" in sim_raw:
        sim_raw["wavelength"] = Wavelength(**sim_raw["wavelength"])
    simulation = SimulationConfig(**sim_raw)

    geom_raw = dict(_section(raw, "geometry"))
    if "lattice" in geom_raw:
        geom_raw["lattice"] = Lattice(**geom_raw["lattice"])
    geometry = GeometryConfig(**geom_raw)

    structure = [
        Layer(material=l["material"], thickness=float(l["thickness"]),
              terminal=bool(l.get("terminal", False)))
        for l in (raw.get("structure") or [])
    ]

    materials = dict(raw.get("materials") or {})

    th_raw = dict(_section(raw, "thermal"))
    if "voltage" in th_raw:
        th_raw["voltage"] = VoltageSweep(**th_raw["voltage"])
    if "cooling_temperature" in th_raw:
        th_raw["cooling_temperature"] = TemperatureSweep(**th_raw["cooling_temperature"])
    if "pv" in th_raw:
        pv_raw = dict(th_raw["pv"])
        if "bandgap" in pv_raw:
            pv_raw["bandgap"] = BandGap(**pv_raw["bandgap"])
        th_raw["pv"] = PVConfig(**pv_raw)
    thermal = ThermalConfig(**th_raw)

    data = DataConfig(**_section(raw, "data"))
    comparison = ComparisonConfig(**_section(raw, "comparison"))

    cfg = Config(
        run=run, simulation=simulation, geometry=geometry, structure=structure,
        materials=materials, thermal=thermal, data=data,
        comparison=comparison,
        base_dir=base_dir,
    )
    validate(cfg)
    return cfg


def load_cases(path: str) -> List[Config]:
    """Load one config or a list of named configs from one YAML file."""
    if not os.path.isfile(path):
        raise ConfigError(f"Config file not found: {path}")
    with open(path, "r") as fh:
        raw = yaml.safe_load(fh)
    absolute = os.path.abspath(path)
    raw = raw or {}
    cases = raw.get("cases")
    if cases is None:
        cases = [raw]
    elif not isinstance(cases, list) or not cases:
        raise ConfigError("`cases` must be a non-empty list.")

    configs = []
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise ConfigError(f"cases[{index - 1}] must be a mapping.")
        cfg = from_dict(case, base_dir=os.path.dirname(absolute))
        cfg.case_name = case.get("name") or f"case_{index}"
        cfg.config_path = absolute
        configs.append(cfg)
    return configs


def load(path: str) -> Config:
    """Load a YAML file containing exactly one simulation config."""
    configs = load_cases(path)
    if len(configs) != 1:
        raise ConfigError(
            f"Config contains {len(configs)} cases; use load_cases().")
    return configs[0]


# --------------------------------------------------------------------------- #
# Validation (light, fail fast with clear messages).
# --------------------------------------------------------------------------- #

_SHAPES = {"flat", "sphere", "semisphere", "triangle", "cylinder", "grating"}
_SOURCES = {"s4", "freeform"}


def validate(cfg: Config) -> None:
    if cfg.run.mode not in {"standard", "test", "cooling_curve", "spectral_compare"}:
        raise ConfigError(
            f"run.mode must be standard|test|cooling_curve|spectral_compare, got {cfg.run.mode!r}"
        )
    if not (cfg.run.optics or cfg.run.thermal or cfg.run.mode == "spectral_compare"):
        raise ConfigError("Nothing to do: run.optics and run.thermal are both false.")

    if cfg.run.mode == "spectral_compare":
        if cfg.run.optics or cfg.run.thermal:
            raise ConfigError("spectral_compare mode requires run.optics and run.thermal to be false.")
        if not cfg.comparison.spectra:
            raise ConfigError("spectral_compare mode requires comparison.spectra.")
        for series in cfg.comparison.spectra:
            if "label" not in series or "file" not in series:
                raise ConfigError("Each comparison.spectra item requires label and file.")
        if len(cfg.comparison.xlim) != 2 or len(cfg.comparison.ylim) != 2:
            raise ConfigError("comparison.xlim and comparison.ylim must each contain two values.")

    # Cross-check: thermal without optics must resume a prior optics run.
    if cfg.run.thermal and not cfg.run.optics and not cfg.run.optics_results:
        raise ConfigError(
            "run.thermal is true but run.optics is false: set run.optics_results "
            "to a previous optics results folder."
        )
    if cfg.run.optics_results_angles not in {"normal", "hemispherical"}:
        raise ConfigError(
            "run.optics_results_angles must be normal|hemispherical.")
    column = cfg.run.optics_results_emittance_column
    if column is not None and column < 1:
        raise ConfigError(
            "run.optics_results_emittance_column must be >= 1 because "
            "column 0 is wavelength.")

    wave = cfg.simulation.wavelength
    if wave.n < 2:
        raise ConfigError("simulation.wavelength.n must be >= 2.")
    if wave.min <= 0.0 or wave.max <= wave.min:
        raise ConfigError(
            "simulation.wavelength requires 0 < min < max.")
    if cfg.simulation.s4_modes < 1:
        raise ConfigError("simulation.s4_modes must be >= 1.")
    if not 0.0 <= cfg.simulation.azimuth_angle_deg < 360.0:
        raise ConfigError(
            "simulation.azimuth_angle_deg must be in [0, 360).")
    if cfg.simulation.angles == "specific":
        if not 0.0 <= cfg.simulation.polar_angle_deg < 90.0:
            raise ConfigError(
                "simulation.polar_angle_deg must be in [0, 90) for a "
                "specific direction.")
    if cfg.simulation.hemisphere_theta_points < 1:
        raise ConfigError("simulation.hemisphere_theta_points must be >= 1.")
    if cfg.simulation.hemisphere_azimuth_points < 1:
        raise ConfigError("simulation.hemisphere_azimuth_points must be >= 1.")
    cfg.simulation.directions()
    cfg.simulation.polarization_names()

    if cfg.run.optics and cfg.geometry.source not in _SOURCES:
        raise ConfigError(
            f"geometry.source must be one of {sorted(_SOURCES)}, "
            f"got {cfg.geometry.source!r}")

    if cfg.run.optics and cfg.geometry.source == "s4":
        if cfg.run.thermal and cfg.simulation.angles != "hemispherical":
            raise ConfigError(
                "Live S4 thermal runs require simulation.angles: "
                "hemispherical. Directional spectra are insufficient for the "
                "radiative energy balance.")
        if cfg.geometry.shape not in _SHAPES:
            raise ConfigError(f"geometry.shape must be one of {sorted(_SHAPES)}, got {cfg.geometry.shape!r}")
        _require_shape_params(cfg.geometry)
        if not cfg.structure:
            raise ConfigError("`structure` must list at least the terminal layer when running S4 optics.")
        if sum(l.terminal for l in cfg.structure) != 1:
            raise ConfigError("`structure` must mark exactly one layer as terminal: true (the substrate).")
        if not cfg.structure[-1].terminal:
            raise ConfigError("The terminal layer must be last in `structure`.")
        if cfg.structure[-1].thickness != 0.0:
            raise ConfigError(
                "The terminal S4 layer is semi-infinite and must have "
                "thickness: 0.")
        if any(l.thickness < 0.0 for l in cfg.structure):
            raise ConfigError("structure layer thicknesses must be >= 0.")
        if sum(l.material == "silicon" for l in cfg.structure) > 1:
            raise ConfigError("`structure` may contain at most one silicon layer.")
        if cfg.geometry.lattice.x <= 0.0 or cfg.geometry.lattice.y <= 0.0:
            raise ConfigError("geometry.lattice x and y must be > 0.")
        # Photonic + structure materials must be declared in `materials`.
        used = {cfg.geometry.photonic_material} | {l.material for l in cfg.structure}
        missing = sorted(m for m in used if m not in cfg.materials and m != "vacuum")
        if missing:
            raise ConfigError(f"Materials used but not declared in `materials`: {missing}")

    if cfg.run.optics and cfg.geometry.source == "freeform":
        if not cfg.geometry.freeform.get("file"):
            raise ConfigError("geometry.source is 'freeform' but geometry.freeform.file is not set.")

    if cfg.run.thermal:
        if (cfg.thermal.reference_temperature is not None
                and cfg.thermal.reference_temperature <= 0.0):
            raise ConfigError("thermal.reference_temperature must be > 0 K.")
        if cfg.thermal.equilibrium not in {"auto", "manual"}:
            raise ConfigError(f"thermal.equilibrium must be auto|manual, got {cfg.thermal.equilibrium!r}")
        if cfg.thermal.voltage.n < 2:
            raise ConfigError("thermal.voltage.n must be >= 2.")
        if cfg.run.mode == "cooling_curve":
            sweep = cfg.thermal.cooling_temperature
            if sweep is None or sweep.n < 2 or sweep.max <= sweep.min:
                raise ConfigError(
                    "cooling_curve mode requires thermal.cooling_temperature with max > min and n >= 2."
                )
            if cfg.thermal.solar_irradiance is not None and cfg.thermal.solar_irradiance <= 0.0:
                raise ConfigError("thermal.solar_irradiance must be positive when set.")
            if (cfg.thermal.absorbed_solar_power is not None
                    and cfg.thermal.absorbed_solar_power <= 0.0):
                raise ConfigError(
                    "thermal.absorbed_solar_power must be positive when set.")


def _require_shape_params(geom: GeometryConfig) -> None:
    needed = {
        "sphere": (geom.sphere, ["radius"]),
        "semisphere": (geom.sphere, ["radius"]),
        "triangle": (geom.triangle, ["base", "height"]),
        "cylinder": (geom.cylinder, ["radius", "height"]),
        "grating": (geom.grating, ["duty", "depth"]),
        "flat": ({}, []),
    }
    block, keys = needed[geom.shape]
    missing = [k for k in keys if k not in block]
    if missing:
        raise ConfigError(f"geometry.{geom.shape} missing required keys: {missing}")

    if geom.shape in ("sphere", "semisphere", "triangle"):
        if geom.discretization_layers < 1:
            raise ConfigError(
                f"geometry.discretization_layers must be >= 1 for shape "
                f"{geom.shape!r} (got {geom.discretization_layers})."
            )

    for block, key in (
        (geom.sphere, "radius"),
        (geom.triangle, "base"),
        (geom.triangle, "height"),
        (geom.cylinder, "radius"),
        (geom.cylinder, "height"),
    ):
        if key in block and block[key] <= 0.0:
            raise ConfigError(f"geometry parameter {key!r} must be > 0.")

    if geom.shape == "grating":
        duty = geom.grating["duty"]
        if not 0.0 < duty < 1.0:
            raise ConfigError(
                f"geometry.grating.duty must be strictly between 0 and 1 "
                f"(ridge fraction of the period); got {duty}.")
        if geom.grating["depth"] <= 0.0:
            raise ConfigError("geometry.grating.depth must be > 0.")
