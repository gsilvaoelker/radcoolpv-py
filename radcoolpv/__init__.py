"""radcoolpv: YAML-driven radiative-cooling photovoltaics simulator.

Python port of the MATLAB+Lua/S4 ``radCoolPV`` toolchain. A single YAML config
drives a two-stage pipeline: an optics stage (RCWA via the S4 Python bindings,
or free-form data) and a thermal/electrical energy-balance stage. The two
stages share one wavelength grid and are coupled in memory, so there is no
manual connection to keep in sync.
"""

__version__ = "0.1.0"
