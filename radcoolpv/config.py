"""Load and validate the YAML configuration.

One YAML file is one case, or a ``cases:`` list of named cases. A case has up
to three blocks, and a block is computed when it is present::

    optics:    where the spectrum comes from. Either ``file`` (a table with
               wavelength in column 0) or ``structure`` (a layer stack, solved
               with S4). Nothing else decides the source.
    thermal:   solve the energy balance for the operating temperature.
    cell:      solve the single-diode cell as well (needs ``thermal``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import yaml


class ConfigError(ValueError):
    """Raised when the YAML is missing something or inconsistent."""


# --------------------------------------------------------------------------- #
# Dataclasses (mirror the YAML structure).
# --------------------------------------------------------------------------- #

@dataclass
class Sweep:
    min: float
    max: float
    n: int

    def array(self) -> np.ndarray:
        return np.linspace(self.min, self.max, self.n)


@dataclass
class Lattice:
    type: str = "square"              # square | hexagonal
    x: float = 20.0
    y: float = 20.0


@dataclass
class Geometry:
    shape: str = "flat"               # flat | sphere | semisphere | triangle | cylinder | grating
    photonic_material: str = "vacuum"
    lattice: Lattice = field(default_factory=Lattice)
    sphere: Dict[str, float] = field(default_factory=dict)    # {radius, layers}
    triangle: Dict[str, float] = field(default_factory=dict)  # {base, height, layers}
    cylinder: Dict[str, float] = field(default_factory=dict)  # {radius, height}
    grating: Dict[str, float] = field(default_factory=dict)   # {duty, depth}; period = lattice.x


@dataclass
class Layer:
    material: str
    thickness: float                  # um

    def __post_init__(self) -> None:
        self.thickness = float(self.thickness)


@dataclass
class Optics:
    # --- a spectrum read from a file --------------------------------------- #
    file: Optional[str] = None
    column: Optional[int] = None      # emittance column; None -> a radcoolpv optics.txt
    # --- or a structure solved with S4 ------------------------------------- #
    wavelength: Sweep = field(default_factory=lambda: Sweep(0.3, 30.0, 2000))
    angles: str = "hemispherical"     # normal | hemispherical
    polarization: str = "unpolarized"  # TE | TM | unpolarized
    hemisphere_theta_points: int = 8
    hemisphere_azimuth_points: int = 12
    s4_modes: int = 10                # S4 Fourier truncation (NumBasis)
    geometry: Geometry = field(default_factory=Geometry)
    structure: Optional[List[Layer]] = None
    substrate: str = "vacuum"         # the semi-infinite layer below the stack
    materials: Dict[str, str] = field(default_factory=dict)

    def directions(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return polar angles, azimuths, and normalized angular weights.

        A hemispherical run uses Gauss-Legendre nodes in
        ``u = sin(theta)^2`` and a uniform periodic azimuth rule. The first
        direction is an explicit zero-weight normal-incidence probe used by the
        PV luminescence model.
        """
        if self.angles == "normal":
            return np.array([0.0]), np.array([0.0]), np.array([1.0])
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
            f"optics.angles must be normal|hemispherical, got {self.angles!r}")

    def polarization_names(self) -> List[str]:
        value = self.polarization.lower()
        if value in ("te", "tm"):
            return [value]
        if value == "unpolarized":
            return ["te", "tm"]
        raise ConfigError(
            f"optics.polarization must be TE|TM|unpolarized, got {self.polarization!r}")


@dataclass
class Thermal:
    ambient_temperature: float = 298.0       # K
    convection_coefficient: float = 12.0     # W/m2-K, everything non-radiative
    temperatures: Optional[Sweep] = None     # K; default ambient .. ambient + 150
    absorbed_solar_power: Optional[float] = None   # W/m2; replaces the AM1.5 integral
    reference_temperature: Optional[float] = None  # K; report the reduction from it
    atmosphere_file: str = "cptrans_nq_100_15.dat"


@dataclass
class BandGap:
    eg0: float = 1.166
    alpha: float = 4.73e-4
    beta: float = 636.0


@dataclass
class Cell:
    silicon_thickness: Optional[float] = None   # um; required with optics.file
    series_resistance: float = 0.00011          # Ohm m2
    shunt_resistance: float = 0.1               # Ohm m2
    bandgap: BandGap = field(default_factory=BandGap)
    iqe_file: str = "siliconIQE.txt"
    voltage: Sweep = field(default_factory=lambda: Sweep(0.1, 0.8, 100))


@dataclass
class Config:
    optics: Optics = field(default_factory=Optics)
    thermal: Optional[Thermal] = None
    cell: Optional[Cell] = None
    case_name: Optional[str] = None
    base_dir: str = "."              # directory the config was loaded from
    config_path: Optional[str] = None

    # ----- derived helpers ------------------------------------------------- #
    def wavelength_array(self) -> np.ndarray:
        return self.optics.wavelength.array()

    def direction_arrays(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.optics.directions()

    def temperature_array(self) -> np.ndarray:
        """Temperature sweep shared by the energy balance and the PV I-V.

        The default is deliberately left at the MATLAB range, T_amb to
        T_amb + 150 K. It is not merely a search window: ``pv.py`` collapses
        the Varshni gap over this whole array into the single scalar
        ``lambda_g`` that cuts off every photogeneration integral, so widening
        the default would move Jsc and the temperature coefficient.
        """
        if self.thermal.temperatures is not None:
            return self.thermal.temperatures.array()
        return self.thermal.ambient_temperature + np.arange(151, dtype=float)

    def silicon_thickness(self) -> float:
        """From ``cell.silicon_thickness``, else from the silicon layer."""
        if self.cell.silicon_thickness is not None:
            return self.cell.silicon_thickness
        return next(l.thickness for l in self.optics.structure
                    if l.material == "silicon")

    def resolve_data(self, path: Optional[str]) -> Optional[str]:
        """Resolve an input data file.

        Tries, in order: an existing absolute path, a path relative to the
        config's directory, then a file of the same basename bundled in the
        package's ``data/`` folder. This lets configs reference bundled defaults
        (atmosphere, IQE) by name while still allowing user-provided files.
        """
        if path is None:
            return None
        if os.path.isabs(path) and os.path.exists(path):
            return path
        cand = os.path.normpath(os.path.join(self.base_dir, path))
        if os.path.exists(cand):
            return cand
        bundled = os.path.join(os.path.dirname(__file__), "data",
                               os.path.basename(path))
        if os.path.exists(bundled):
            return bundled
        return cand   # let the caller raise a clear "not found" error


# --------------------------------------------------------------------------- #
# Parsing.
# --------------------------------------------------------------------------- #

def _build(cls, raw: Any, where: str):
    """Instantiate a dataclass from a YAML mapping, naming the bad key if any."""
    if not isinstance(raw, dict):
        raise ConfigError(f"`{where}` must be a mapping, got {type(raw).__name__}")
    try:
        return cls(**raw)
    except TypeError as exc:
        valid = [f.name for f in fields(cls)]
        raise ConfigError(f"{where}: {exc}. Valid keys: {valid}") from None


def from_dict(raw: Dict[str, Any], base_dir: str = ".") -> Config:
    """Build a :class:`Config` from a parsed YAML mapping, applying defaults."""
    raw = raw or {}
    unknown = sorted(set(raw) - {"name", "optics", "thermal", "cell"})
    if unknown:
        raise ConfigError(
            f"unknown top-level keys {unknown}; a case has optics, thermal, cell")

    def nested(block, key, cls, where):
        if block.get(key) is not None:
            block[key] = _build(cls, block[key], where)

    o = dict(raw.get("optics") or {})
    nested(o, "wavelength", Sweep, "optics.wavelength")
    if o.get("geometry") is not None:
        o["geometry"] = dict(o["geometry"])
        nested(o["geometry"], "lattice", Lattice, "optics.geometry.lattice")
        nested(o, "geometry", Geometry, "optics.geometry")
    if o.get("structure") is not None:
        o["structure"] = [_build(Layer, l, "optics.structure") for l in o["structure"]]
    optics = _build(Optics, o, "optics")

    thermal = cell = None
    if "thermal" in raw:
        t = dict(raw["thermal"] or {})
        nested(t, "temperatures", Sweep, "thermal.temperatures")
        thermal = _build(Thermal, t, "thermal")
    if "cell" in raw:
        c = dict(raw["cell"] or {})
        nested(c, "bandgap", BandGap, "cell.bandgap")
        nested(c, "voltage", Sweep, "cell.voltage")
        cell = _build(Cell, c, "cell")

    cfg = Config(optics=optics, thermal=thermal, cell=cell, base_dir=base_dir)
    validate(cfg)
    return cfg


def load_cases(path: str) -> List[Config]:
    """Load one config or a list of named configs from one YAML file."""
    if not os.path.isfile(path):
        raise ConfigError(f"Config file not found: {path}")
    with open(path, "r") as fh:
        raw = yaml.safe_load(fh) or {}
    absolute = os.path.abspath(path)
    cases = raw.get("cases")
    stem = os.path.splitext(os.path.basename(path))[0]
    if cases is None:
        cases = [raw]
    elif not isinstance(cases, list) or not cases:
        raise ConfigError("`cases` must be a non-empty list.")

    configs = []
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise ConfigError(f"cases[{index - 1}] must be a mapping.")
        cfg = from_dict(case, base_dir=os.path.dirname(absolute))
        cfg.case_name = case.get("name") or (stem if len(cases) == 1 else f"{stem}_{index}")
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
# Validation (fail fast with a message that names the key to fix).
# --------------------------------------------------------------------------- #

_SHAPES = {"flat", "sphere", "semisphere", "triangle", "cylinder", "grating"}


def validate(cfg: Config) -> None:
    o = cfg.optics
    if (o.file is None) == (o.structure is None):
        raise ConfigError(
            "optics needs exactly one of `file` (a spectrum to read) or "
            "`structure` (a layer stack to solve with S4).")

    if o.file is not None:
        if o.column is not None and o.column < 1:
            raise ConfigError(
                "optics.column must be >= 1: column 0 is the wavelength.")
        if cfg.cell is not None and cfg.cell.silicon_thickness is None:
            raise ConfigError(
                "cell.silicon_thickness (um) is required when the spectrum "
                "comes from a file: nothing else says how thick the silicon is.")
    else:
        _validate_structure(cfg)

    if cfg.cell is not None and cfg.thermal is None:
        raise ConfigError(
            "cell needs thermal: the cell is solved at the operating temperature.")

    if cfg.thermal is not None:
        t = cfg.thermal
        if t.reference_temperature is not None and t.reference_temperature <= 0.0:
            raise ConfigError("thermal.reference_temperature must be > 0 K.")
        if t.absorbed_solar_power is not None and t.absorbed_solar_power <= 0.0:
            raise ConfigError("thermal.absorbed_solar_power must be > 0 W/m2.")
        sweep = t.temperatures
        if sweep is not None and (sweep.n < 2 or sweep.max <= sweep.min):
            raise ConfigError(
                "thermal.temperatures needs max > min and n >= 2.")
        if cfg.cell is not None:
            if cfg.cell.voltage.n < 2:
                raise ConfigError("cell.voltage.n must be >= 2.")
            # The PV stage reports an ambient operating point alongside the
            # equilibrium one, so the sweep has to contain ambient. Without
            # this the ambient column would be a silent extrapolation to the
            # nearest swept temperature.
            if sweep is not None and not (sweep.min <= t.ambient_temperature <= sweep.max):
                raise ConfigError(
                    f"thermal.temperatures ({sweep.min}-{sweep.max} K) must "
                    f"include the ambient temperature ({t.ambient_temperature} K), "
                    "because the cell is also reported at ambient.")


def _validate_structure(cfg: Config) -> None:
    o = cfg.optics
    w = o.wavelength
    if w.n < 2:
        raise ConfigError("optics.wavelength.n must be >= 2.")
    if w.min <= 0.0 or w.max <= w.min:
        raise ConfigError("optics.wavelength requires 0 < min < max.")
    if o.s4_modes < 1:
        raise ConfigError("optics.s4_modes must be >= 1.")
    if o.hemisphere_theta_points < 1 or o.hemisphere_azimuth_points < 1:
        raise ConfigError("optics.hemisphere_*_points must be >= 1.")
    o.directions()
    o.polarization_names()
    if cfg.thermal is not None and o.angles != "hemispherical":
        raise ConfigError(
            "thermal needs optics.angles: hemispherical; a normal-incidence "
            "spectrum cannot feed the radiative energy balance.")

    g = o.geometry
    if g.shape not in _SHAPES:
        raise ConfigError(
            f"optics.geometry.shape must be one of {sorted(_SHAPES)}, got {g.shape!r}")
    if g.lattice.type not in ("square", "hexagonal"):
        raise ConfigError(
            f"optics.geometry.lattice.type must be square|hexagonal, got {g.lattice.type!r}")
    if g.lattice.x <= 0.0 or g.lattice.y <= 0.0:
        raise ConfigError("optics.geometry.lattice x and y must be > 0.")
    _require_shape_params(g)

    if not o.structure:
        raise ConfigError("optics.structure must list at least one layer.")
    if any(l.thickness <= 0.0 for l in o.structure):
        raise ConfigError(
            "optics.structure thicknesses must be > 0; the semi-infinite "
            "layer below the stack is `substrate`, and a layer you do not "
            "want is simply deleted.")
    if sum(l.material == "silicon" for l in o.structure) > 1:
        raise ConfigError("optics.structure may contain at most one silicon layer.")
    if cfg.cell is not None:
        if cfg.cell.silicon_thickness is not None:
            raise ConfigError(
                "cell.silicon_thickness is read from the silicon layer in "
                "optics.structure; do not set it as well.")
        if not any(l.material == "silicon" for l in o.structure):
            raise ConfigError(
                "cell needs a layer with material `silicon` in optics.structure.")

    used = {g.photonic_material, o.substrate} | {l.material for l in o.structure}
    missing = sorted(m for m in used if m not in o.materials and m != "vacuum")
    if missing:
        raise ConfigError(
            f"materials used but not declared in optics.materials: {missing}")


def _require_shape_params(g: Geometry) -> None:
    needed = {
        "sphere": (g.sphere, ["radius", "layers"]),
        "semisphere": (g.sphere, ["radius", "layers"]),
        "triangle": (g.triangle, ["base", "height", "layers"]),
        "cylinder": (g.cylinder, ["radius", "height"]),
        "grating": (g.grating, ["duty", "depth"]),
        "flat": ({}, []),
    }
    block, keys = needed[g.shape]
    missing = [k for k in keys if k not in block]
    if missing:
        raise ConfigError(f"optics.geometry.{g.shape} missing required keys: {missing}")
    for key in keys:
        if key == "duty":
            if not 0.0 < block[key] < 1.0:
                raise ConfigError(
                    "optics.geometry.grating.duty must be strictly between 0 "
                    f"and 1 (ridge fraction of the period); got {block[key]}.")
        elif block[key] <= 0:
            raise ConfigError(f"optics.geometry.{g.shape}.{key} must be > 0.")
