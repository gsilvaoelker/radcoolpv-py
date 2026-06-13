"""Small cross-version compatibility shims.

``numpy.trapz`` was renamed to ``numpy.trapezoid`` and removed in NumPy 2.0.
Expose a single ``trapz`` that works on both NumPy 1.x and 2.x.
"""

import numpy as np

trapz = getattr(np, "trapezoid", None)
if trapz is None:  # NumPy < 2.0
    trapz = np.trapz
