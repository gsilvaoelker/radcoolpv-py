"""Physical constants and unit conversions.

Direct port of ``settings/constants.m`` from the MATLAB code. Values are kept
identical so numerical results match.
"""

import math

# Fundamental constants.
CLIGHT = 299792458.0          # speed of light in vacuum, m/s
HPLANCK = 6.62607004e-34      # Planck constant, m^2 kg / s
HBAR = HPLANCK / (2 * math.pi)
KBOLTZ = 1.38064852e-23       # Boltzmann constant, m^2 kg / s^2 K
KBOLTZ_EV = 8.617333262e-5    # Boltzmann constant, eV/K
ECHARGE = 1.60217662e-19      # elementary charge, C

# Blackbody radiation constants (wavelength in um).
C1 = 2 * math.pi * HPLANCK * CLIGHT ** 2 * 1e24   # W um^4 / m^2
C2 = HPLANCK * CLIGHT / KBOLTZ * 1e6              # um K

# Unit conversion factors.
MICRONTONANO = 1000.0
MICRON = 1e-6
MILI = 1e-3
M2TOCM2 = 10000.0
MTOCM = 100.0
MTOMICRON = 1e6
M2TOMICRON2 = 1e12
MICRON2TOM2 = 1e-12
