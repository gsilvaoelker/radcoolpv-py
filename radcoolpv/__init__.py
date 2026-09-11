"""radcoolpv: radiative cooling of silicon photovoltaics.

Python port of the MATLAB+Lua/S4 ``radCoolPV`` toolchain. One YAML case has
three blocks: ``optics`` (a spectrum from a file, or a structure solved with
the lazily imported S4 extension), ``thermal`` (the energy balance), and
``cell`` (the single-diode I-V). The blocks share one wavelength grid and are
coupled in memory.
"""

__version__ = "0.2.0"
