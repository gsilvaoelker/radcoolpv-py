"""Results-folder management and the in-memory hand-off between stages.

``RunContext`` is what removes the manual optics->thermal coupling from the old
MATLAB code: instead of pasting a results-folder path into the second script,
the optics stage drops its spectral results into the context and the thermal
stage reads them straight back.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np

from ..config import Config


@dataclass
class OpticsResult:
    """Spectral optical properties produced by the optics stage.

    Mirrors the outputs of ``hemisphPropsFunc.m`` / ``normalPropsFunc.m`` plus
    the normal-incidence quantities the thermal stage needs for the
    non-thermal (luminescence) term.
    """

    lambda_um: np.ndarray
    ref: np.ndarray                       # reflectance (hemispherical or normal)
    tran: np.ndarray                      # transmittance
    emit: np.ndarray                      # total absorptance == emittance
    abs_silicon: np.ndarray               # absorptance in the silicon layer
    emit_atm: np.ndarray                  # atmospheric emissivity
    emitt_spec_times_emit_atm: np.ndarray  # emit * emit_atm (pre-integrated)
    # Normal-incidence copies (equal to the above for angles == normal).
    ref_norm: np.ndarray = None
    emit_norm: np.ndarray = None
    abs_silicon_norm: np.ndarray = None
    angles: str = "normal"                # normal | hemispherical

    def __post_init__(self) -> None:
        if self.ref_norm is None:
            self.ref_norm = self.ref
        if self.emit_norm is None:
            self.emit_norm = self.emit
        if self.abs_silicon_norm is None:
            self.abs_silicon_norm = self.abs_silicon


@dataclass
class RunContext:
    config: Config
    results_dir: str
    optics: Optional[OpticsResult] = None
    thermal: Optional[Any] = None                          # ThermalResult (avoid import cycle)
    scalars: Dict[str, Any] = field(default_factory=dict)   # named scalar results for logs
    extras: Dict[str, Any] = field(default_factory=dict)    # arrays kept for writers/plots


def make_results_dir(parent: str, prefix: str) -> str:
    """Create a timestamped results subfolder and return its path.

    The legacy MATLAB code named folders ``results_<date>_<HH:MM:SS>``; we keep
    the same flavour but use filesystem-safe separators.
    """
    stamp = datetime.now().strftime("%d-%b-%Y_%H-%M-%S")
    path = os.path.join(parent, f"{prefix}_{stamp}")
    os.makedirs(path, exist_ok=True)
    return path
