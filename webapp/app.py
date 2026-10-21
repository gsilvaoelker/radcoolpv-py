"""Browser simulator: four thermal-management scenarios of a silicon PV panel.

Runs in Pyodide (``index.html``) and in CPython (``tests/test_webapp.py``).
The scenarios are {base front, radiative-cooling front} x {plain convection,
metal foam}, all at one operating point (plane-of-array irradiance G, ambient
temperature). The foam enters only as a higher lumped h. A literature cooler is
a front coating on the base module, given by its own transmittance and
emittance over the whole spectrum.
"""

import dataclasses
import io
import os

import numpy as np

import radcoolpv
from radcoolpv import config
from radcoolpv.constants import ECHARGE, MICRON
from radcoolpv.optics import directional
from radcoolpv.thermal import energy_balance, pv, spectra

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BASE = "C2_pv_flat_silica.txt"      # flat silica: stands in for a glass-covered module
COOLER = "C3_pv_cylinders.txt"      # Akerboom et al. (2022) silica microcylinders
COVERAGE_UM = (0.4, 13.0)           # a coating file must span the solar band and the 8-13 um window
THICKNESS_UM = 500.0                # silicon thickness the C2/C3 spectra were computed for
_SOLAR = os.path.join(os.path.dirname(radcoolpv.__file__), "data", "astmg173.xlsx")
_cache = {}


def _cfg(t_amb, h, temperatures=None):
    thermal = {"ambient_temperature": t_amb, "convection_coefficient": h}
    if temperatures:
        thermal["temperatures"] = temperatures
    return config.from_dict({"optics": {"file": BASE}, "thermal": thermal,
                             "cell": {"silicon_thickness": THICKNESS_UM}}, DATA)


def _load():
    """Base and C3 spectra, AM1.5G on their grid; read once (the xlsx is slow)."""
    if not _cache:
        atm = _cfg(298.15, 10.0).resolve_data("cptrans_nq_100_15.dat")
        _cache["atm"] = atm
        _cache["base"] = directional.from_file(os.path.join(DATA, BASE), atm)
        _cache["C3"] = directional.from_file(os.path.join(DATA, COOLER), atm)
        _cache["sun"] = spectra.load_solar(_SOLAR, _cache["base"].lambda_um)
    return _cache


def literature_cooler(base, csv_text):
    """Base module under a coating; CSV columns lambda_um, T, emit (R = 1 - T - emit).

    Single pass at every wavelength: the coating absorbs (and so emits) emit_c
    and transmits T_c to the module, whose reflection leaves without returning.
    Coating-module inter-reflections, second order in R_c * R_base, are
    neglected. Outside the file's range its edge values are held.
    """
    text = csv_text.replace(",", ".").replace(";", " ") if ";" in csv_text else csv_text.replace(",", " ")
    data = np.genfromtxt(io.StringIO(text.replace("\t", " ")), invalid_raise=False)
    data = data[~np.isnan(data).any(axis=1)]
    data = data[np.argsort(data[:, 0])]
    if data.shape[1] < 3 or data[0, 0] > COVERAGE_UM[0] or data[-1, 0] < COVERAGE_UM[1]:
        raise ValueError("el archivo del recubrimiento necesita 3 columnas (λ [µm], T, ε) "
                         f"y cubrir al menos {COVERAGE_UM[0]}–{COVERAGE_UM[1]} µm")
    if np.any(data[:, 1] + data[:, 2] > 1.01):
        raise ValueError("el recubrimiento tiene T + ε > 1: R = 1 − T − ε sería negativa")
    lam = base.lambda_um
    t_c, e_c = (np.interp(lam, data[:, 0], np.clip(data[:, k], 0.0, 1.0)) for k in (1, 2))
    emit = np.minimum(e_c + t_c * base.emit, 1.0)
    # Keep the base's angle-averaged sky term, rescaled by the emittance ratio.
    ratio = np.divide(emit, base.emit, out=np.zeros_like(emit), where=base.emit > 0)
    return dataclasses.replace(
        base, ref=1.0 - emit, tran=np.zeros_like(emit), emit=emit,
        abs_silicon=t_c * base.abs_silicon,
        emitt_spec_times_emit_atm=ratio * base.emitt_spec_times_emit_atm,
        ref_norm=None, emit_norm=None, abs_silicon_norm=None)


def _sun(g):
    """AM1.5G scaled so it integrates to g W/m^2 (heat load, Jsc and eta together)."""
    s = _load()["sun"]
    f = g / s.total_am15
    return dataclasses.replace(s, irradiance_per_um=f * s.irradiance_per_um,
                               photon_flux=f * s.photon_flux, total_am15=float(g))


def stc_card(optics, n, area):
    """Datasheet values at 25 C and 1000 W/m^2, per panel, as Explorador Solar asks."""
    cfg = _cfg(298.15, 10.0, {"min": 297.15, "max": 299.15, "n": 3})
    flux = _sun(1000.0).photon_flux
    iv = pv.solve_iv(cfg, optics, flux)
    voc = [pv.open_circuit_voltage(iv.current_dens[i], iv.volt) for i in range(3)]
    vmp, pmp = pv.refine_peak(iv.volt, iv.cell_power[:, 1])
    dvoc = (voc[2] - voc[0]) / 2.0
    # Jsc depends on T only through its cut-off lambda_g(T), which pv.py snaps
    # to the wavelength grid (a ~0.025 um step against ~2.6e-4 um/K), so a
    # finite difference of iv.isc is zero. Leibniz rule on the same integral:
    # dJsc/dT = q * IQE*A_Si*flux at lambda_g * dlambda_g/dT.
    bg = cfg.cell.bandgap
    lg = pv._bandgap_wavelength_um(np.array([297.15, 298.15, 299.15]), bg.eg0, bg.alpha, bg.beta)
    edge = np.interp(lg[1], optics.lambda_um, iv.iqe * iv.abs_pv * flux)
    disc = ECHARGE * edge * (lg[2] - lg[0]) / 2.0 * MICRON
    return {"n": n, "vmp": n * vmp, "imp": area * pmp / vmp, "pmp": n * area * pmp,
            "voc": n * voc[1], "voc_pct": 100.0 * dvoc / voc[1], "voc_mv": 1000.0 * n * dvoc,
            "isc": area * iv.isc[1], "isc_pct": 100.0 * disc / iv.isc[1],
            "isc_ma": 1000.0 * area * disc}


def simulate(inp):
    """inp: g, t_amb_c, n_cells, side_mm, h, h_foam, cooler ('C3' | 'custom'), csv."""
    c = _load()
    base = c["base"]
    cooler = c["C3"] if inp["cooler"] == "C3" else literature_cooler(base, inp["csv"])
    n, area = int(inp["n_cells"]), (inp["side_mm"] / 1000.0) ** 2
    t_amb = inp["t_amb_c"] + 273.15
    rows = []
    for name, optics, h in [("Base", base, inp["h"]), ("Espuma metálica", base, inp["h_foam"]),
                            ("Enfriador radiativo", cooler, inp["h"]),
                            ("Enfriador + espuma", cooler, inp["h_foam"])]:
        r = energy_balance.run(_cfg(t_amb, h), optics, _sun(inp["g"]))
        rows.append({"name": name, "t_cell": r.equil_temp - 273.15, "eta": 100.0 * r.efficiency_equil,
                     "p_panel": n * area * r.mpp_equil, "vmp": n * r.vmpp,
                     "imp": area * r.mpp_equil / r.vmpp, "voc": n * r.voc_equil, "isc": area * r.isc,
                     "q_solar": r.solar_power, "q_rad": r.rad_power_equil - r.atm_power,
                     "q_conv": h * (r.equil_temp - t_amb), "q_elec": r.mpp_equil, "beta_p": r.beta_p})
    for r in rows:
        r["dt"] = r["t_cell"] - rows[0]["t_cell"]
        r["gain"] = 100.0 * (r["p_panel"] / rows[0]["p_panel"] - 1.0)
    return {"rows": rows,
            "stc": {"Base": stc_card(base, n, area), "Enfriador radiativo": stc_card(cooler, n, area)},
            "spectrum": {"lam": base.lambda_um.tolist(), "base": base.emit.tolist(),
                         "sun": _sun(inp["g"]).irradiance_per_um.tolist(),
                         "cooler": cooler.emit.tolist()}}
