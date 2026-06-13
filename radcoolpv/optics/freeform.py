"""Free-form optics input: read externally optimised structures instead of S4.

Port of the ``runFF_data`` branch of ``mainEnergyBalancePV_v11.m``. The data
file (see ``freeFormData/freeFormDataFormat.md``) is comma-separated with
columns:

    lambda, totRef, totAbs, FreeFormAbs, NILresidualAbs, SiNAbs, SiAbs, AlAbs

Only normal-incidence data is provided, so this yields a *normal* OpticsResult.
The wavelength grid is taken from the data file's span (as MATLAB does), with
``n`` points from the config.
"""

from __future__ import annotations

import numpy as np

from ..io.results import OpticsResult
from ..thermal.spectra import load_atmosphere


def load(path: str, n_lambda: int, atmosphere_path: str) -> OpticsResult:
    data = np.loadtxt(path, delimiter=",")
    lam_f = data[:, 0]
    tot_ref = data[:, 1]
    tot_abs = data[:, 2]
    si_abs = data[:, 6]

    grid = np.linspace(lam_f[0], lam_f[-1], n_lambda)
    ref = np.interp(grid, lam_f, tot_ref)
    abst = np.interp(grid, lam_f, tot_abs)
    abs_si = np.interp(grid, lam_f, si_abs)

    emit = abst
    tran = 1.0 - abst - ref
    atm = load_atmosphere(atmosphere_path, grid)
    emit_atm = 1.0 - atm
    product = emit_atm * emit

    return OpticsResult(
        lambda_um=grid, ref=ref, tran=tran, emit=emit, abs_silicon=abs_si,
        emit_atm=emit_atm, emitt_spec_times_emit_atm=product, angles="normal",
    )
