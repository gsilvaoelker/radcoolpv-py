"""Physical constants and unit conversions.

Direct port of ``settings/constants.m`` from the MATLAB code. Values are kept
identical so numerical results match. Constants the port carried over but
nothing uses have been dropped.
"""

# Fundamental constants.
CLIGHT = 299792458.0          # speed of light in vacuum, m/s
HPLANCK = 6.62607004e-34      # Planck constant, m^2 kg / s
KBOLTZ = 1.38064852e-23       # Boltzmann constant, m^2 kg / s^2 K
ECHARGE = 1.60217662e-19      # elementary charge, C

# Unit conversion factors.
MICRONTONANO = 1000.0
MICRON = 1e-6
MTOMICRON = 1e6
MICRON2TOM2 = 1e-12
