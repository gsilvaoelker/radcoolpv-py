"""Load and validate the YAML configuration.

A single YAML file drives the whole run. It is parsed into typed dataclasses
with defaults, light validation, and a few derived helpers (wavelength grid,
angle list, silicon thickness). The ``simulation`` section is shared by both
stages so the optics and thermal calculations can never drift apart.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional

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
    mode: str = "standard"            # standard | test | cooling_curve
    results_dir: str = "results"
    outputs: List[str] = field(default_factory=lambda: ["legacy", "clean"])
    optics_results: Optional[str] = None  # resume a prior optics run


@dataclass
class Wavelength(_LinspaceSweep):
    min: float = 0.3
    max: float = 30.0
    n: int = 2000


@dataclass
class SimulationConfig:
    wavelength: Wavelength = field(default_factory=Wavelength)
    angles: str = "hemispherical"     # normal | hemispherical
    rcwa_modes: int = 10              # S4 Fourier truncation (NumBasis)

    def angle_array_deg(self) -> np.ndarray:
        if self.angles == "normal":
            return np.array([0.0])
        if self.angles == "hemispherical":
            # Matches MATLAB: round(linspace(0,85,18),1).
            return np.round(np.linspace(0.0, 85.0, 18), 1)
        raise ConfigError(f"simulation.angles must be 'normal' or 'hemispherical', got {self.angles!r}")


@dataclass
class Lattice:
    type: str = "square"              # square | hexagonal
    x: float = 20.0
    y: float = 20.0


@dataclass
class GeometryConfig:
    source: str = "s4"               # s4 | freeform
    shape: str = "flat"              # flat | sphere | semisphere | triangle | cylinder
    photonic_material: str = "sio2"
    lattice: Lattice = field(default_factory=Lattice)
    discretization_layers: int = 1
    sphere: Dict[str, float] = field(default_factory=dict)
    triangle: Dict[str, float] = field(default_factory=dict)
    cylinder: Dict[str, float] = field(default_factory=dict)
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
    convection_coefficient: float = 12.0
    voltage: VoltageSweep = field(default_factory=VoltageSweep)
    equilibrium: str = "auto"        # auto | manual
    cooling_temperature: Optional[TemperatureSweep] = None
    solar_irradiance: Optional[float] = None  # W/m2; cooling_curve-only normalization
    reference_curve_file: Optional[str] = None
    reference_curve_column: int = 1
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
    base_dir: str = "."              # directory the config was loaded from

    # ----- derived helpers ------------------------------------------------- #
    def wavelength_array(self) -> np.ndarray:
        return self.simulation.wavelength.array()

    def angle_array_deg(self) -> np.ndarray:
        return self.simulation.angle_array_deg()

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


def load(path: str) -> Config:
    """Load a YAML config file into a validated :class:`Config`."""
    if not os.path.isfile(path):
        raise ConfigError(f"Config file not found: {path}")
    with open(path, "r") as fh:
        raw = yaml.safe_load(fh)
    return from_dict(raw, base_dir=os.path.dirname(os.path.abspath(path)))


# --------------------------------------------------------------------------- #
# Validation (light, fail fast with clear messages).
# --------------------------------------------------------------------------- #

_SHAPES = {"flat", "sphere", "semisphere", "triangle", "cylinder"}
_SOURCES = {"s4", "freeform"}


def validate(cfg: Config) -> None:
    if cfg.run.mode not in {"standard", "test", "cooling_curve", "spectral_compare"}:
        raise ConfigError(
            f"run.mode must be standard|test|cooling_curve|spectral_compare, got {cfg.run.mode!r}"
        )
    for o in cfg.run.outputs:
        if o not in {"legacy", "clean"}:
            raise ConfigError(f"run.outputs items must be 'legacy' or 'clean', got {o!r}")
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

    if cfg.simulation.wavelength.n < 2:
        raise ConfigError("simulation.wavelength.n must be >= 2.")
    cfg.simulation.angle_array_deg()  # raises if angles invalid

    if cfg.run.optics and cfg.geometry.source not in _SOURCES:
        raise ConfigError(
            f"geometry.source must be one of {sorted(_SOURCES)}, "
            f"got {cfg.geometry.source!r}")

    if cfg.run.optics and cfg.geometry.source == "s4":
        if cfg.geometry.shape not in _SHAPES:
            raise ConfigError(f"geometry.shape must be one of {sorted(_SHAPES)}, got {cfg.geometry.shape!r}")
        _require_shape_params(cfg.geometry)
        if not cfg.structure:
            raise ConfigError("`structure` must list at least the terminal layer when running RCWA optics.")
        if not any(l.terminal for l in cfg.structure):
            raise ConfigError("`structure` must mark exactly one layer as terminal: true (the substrate).")
        # Photonic + structure materials must be declared in `materials`.
        used = {cfg.geometry.photonic_material} | {l.material for l in cfg.structure}
        missing = sorted(m for m in used if m not in cfg.materials and m != "vacuum")
        if missing:
            raise ConfigError(f"Materials used but not declared in `materials`: {missing}")

    if cfg.run.optics and cfg.geometry.source == "freeform":
        if not cfg.geometry.freeform.get("file"):
            raise ConfigError("geometry.source is 'freeform' but geometry.freeform.file is not set.")

    if cfg.run.thermal:
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


def _require_shape_params(geom: GeometryConfig) -> None:
    needed = {
        "sphere": (geom.sphere, ["radius"]),
        "semisphere": (geom.sphere, ["radius"]),
        "triangle": (geom.triangle, ["base", "height"]),
        "cylinder": (geom.cylinder, ["radius", "height"]),
        "flat": ({}, []),
    }
    block, keys = needed[geom.shape]
    missing = [k for k in keys if k not in block]
    if missing:
        raise ConfigError(f"geometry.{geom.shape} missing required keys: {missing}")

    if geom.shape == "semisphere" and geom.discretization_layers % 2 == 0:
        # The dome is built by slicing a full sphere and stopping at the
        # equator, so an even slice count has no slab centred there and the
        # structure comes out `radius / discretization_layers` too short -
        # 50% short at 2 layers. The MATLAB original carries the same
        # constraint as a bare comment ("Use odd numbers for semipsheres");
        # here it is enforced rather than left to the reader.
        raise ConfigError(
            "geometry.discretization_layers must be ODD for shape 'semisphere' "
            f"(got {geom.discretization_layers}); an even count builds a dome "
            "radius/discretization_layers shorter than requested."
        )
