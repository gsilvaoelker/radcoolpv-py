"""Browser simulator: four thermal-management scenarios of a silicon PV panel.

Runs in Pyodide (``index.html``) and in CPython (``tests/test_webapp.py``).
The scenarios are {base front, radiative-cooling front} x {plain, enhanced
convection}, all at one operating point (plane-of-array irradiance G, ambient
temperature). Enhanced convection (a metal foam, fins, forced air) enters only
as a higher lumped h. The base module and its coolers come from one of two
papers (MODULES); a literature cooler is instead a front coating on the base
module, given by its own transmittance and emittance over the whole spectrum.
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
# Each paper's base module and the coolers it compares with it, as spectra in
# DATA, with the silicon thickness those spectra were computed for.
MODULES = {
    # Akerboom et al., ACS Photonics 9, 3831 (2022): flat silica vs silica microcylinders.
    "akerboom": {"thickness": 500.0, "base": "C2_pv_flat_silica.txt",
                 "coolers": {"C3": "C3_pv_cylinders.txt"}},
    # Silva-Oelker & Jaramillo-Fernandez, Opt. Express 30, 32965 (2022): a cell under
    # 3.2 mm glass vs flat or hemisphere-patterned soda-lime and PDMS covers.
    "oe": {"thickness": 250.0, "base": "OE_reference.txt",
           "coolers": {k: f"OE_{k}.txt" for k in ("hemisph_sodalime", "hemisph_pdms", "flat_sodalime", "flat_pdms")}},
}
COVERAGE_UM = (0.4, 13.0)           # a coating file must span the solar band and the 8-13 um window
_SOLAR = os.path.join(os.path.dirname(radcoolpv.__file__), "data", "astmg173.xlsx")
_cache = {}


def _cfg(t_amb, h, thickness, temperatures=None):
    thermal = {"ambient_temperature": t_amb, "convection_coefficient": h}
    if temperatures:
        thermal["temperatures"] = temperatures
    return config.from_dict({"optics": {"file": "spectrum"}, "thermal": thermal,
                             "cell": {"silicon_thickness": thickness}}, DATA)


def _load(module="akerboom"):
    """A module's spectra and AM1.5G on their grid; read once (the xlsx is slow)."""
    if module not in _cache:
        m = MODULES[module]
        atm = _cfg(298.15, 10.0, m["thickness"]).resolve_data("cptrans_nq_100_15.dat")
        read = lambda f: directional.from_file(os.path.join(DATA, f), atm)
        base = read(m["base"])
        _cache[module] = {"base": base, "thickness": m["thickness"],
                          "sun": spectra.load_solar(_SOLAR, base.lambda_um),
                          "coolers": {k: read(f) for k, f in m["coolers"].items()}}
    return _cache[module]


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
        span = f"{COVERAGE_UM[0]}–{COVERAGE_UM[1]} µm"
        raise ValueError(f"el archivo del recubrimiento necesita 3 columnas (λ [µm], T, ε) y cubrir al menos {span} / "
                         f"the coating file needs 3 columns (λ [µm], T, ε) and must cover at least {span}")
    if np.any(data[:, 1] + data[:, 2] > 1.01):
        raise ValueError("el recubrimiento tiene T + ε > 1: R = 1 − T − ε sería negativa / "
                         "the coating has T + ε > 1: R = 1 − T − ε would be negative")
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


def _sun(c, g):
    """AM1.5G scaled so it integrates to g W/m^2 (heat load, Jsc and eta together)."""
    s = c["sun"]
    f = g / s.total_am15
    return dataclasses.replace(s, irradiance_per_um=f * s.irradiance_per_um,
                               photon_flux=f * s.photon_flux, total_am15=float(g))


def stc_card(optics, n, area, c):
    """Datasheet values at 25 C and 1000 W/m^2, per panel, as Explorador Solar asks."""
    cfg = _cfg(298.15, 10.0, c["thickness"], {"min": 297.15, "max": 299.15, "n": 3})
    flux = _sun(c, 1000.0).photon_flux
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
    """inp: g, t_amb_c, n_cells, side_mm, h, h_foam, module, cooler (a MODULES key | 'custom'), csv."""
    c = _load(inp.get("module", "akerboom"))
    base = c["base"]
    cooler = literature_cooler(base, inp["csv"]) if inp["cooler"] == "custom" else c["coolers"][inp["cooler"]]
    n, area = int(inp["n_cells"]), (inp["side_mm"] / 1000.0) ** 2
    t_amb = inp["t_amb_c"] + 273.15
    rows = []
    for name, optics, h in [("Base", base, inp["h"]), ("Convección mejorada", base, inp["h_foam"]),
                            ("Enfriador radiativo", cooler, inp["h"]),
                            ("Enfriador + convección mejorada", cooler, inp["h_foam"])]:
        r = energy_balance.run(_cfg(t_amb, h, c["thickness"]), optics, _sun(c, inp["g"]))
        rows.append({"name": name, "t_cell": r.equil_temp - 273.15, "eta": 100.0 * r.efficiency_equil,
                     "p_panel": n * area * r.mpp_equil, "vmp": n * r.vmpp,
                     "imp": area * r.mpp_equil / r.vmpp, "voc": n * r.voc_equil, "isc": area * r.isc,
                     "q_solar": r.solar_power, "q_rad": r.rad_power_equil - r.atm_power,
                     "q_conv": h * (r.equil_temp - t_amb), "q_elec": r.mpp_equil, "beta_p": r.beta_p})
    for r in rows:
        r["dt"] = r["t_cell"] - rows[0]["t_cell"]
        r["gain"] = 100.0 * (r["p_panel"] / rows[0]["p_panel"] - 1.0)
    return {"rows": rows,
            "stc": {"Base": stc_card(base, n, area, c), "Enfriador radiativo": stc_card(cooler, n, area, c)},
            "spectrum": {"lam": base.lambda_um.tolist(), "base": base.emit.tolist(),
                         "sun": _sun(c, inp["g"]).irradiance_per_um.tolist(),
                         "cooler": cooler.emit.tolist()}}
