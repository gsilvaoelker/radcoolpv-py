"""Validate radcoolpv against Table 1 of:

  Silva-Oelker & Jaramillo-Fernandez, "Numerical study of sodalime and PDMS
  hemisphere photonic structures for radiative cooling of silicon solar
  cells," Opt. Express 30(18), 32965 (2022).

Each Table 1 row is driven by its own YAML config (table1_*.yaml) through
``pipeline.run()``, exactly as ``radcoolpv run`` does. The configs point
``run.optics_results`` at a pre-computed, hemispherically-reduced
optical-property file bundled in data/Fig. 1D, data/Fig. 3B, or data/Fig. 3C
instead of requesting a live S4 sweep.

Known approximation (agreed with the user): none of the provided optical
files carry per-(wavelength, angle) data, only the hemispherically-integrated
spectra. The atmospheric-power term P_atm needs the emitter's angle-resolved
emissivity; lacking that, this script uses radcoolpv's existing fallback
(see radcoolpv/optics/freeform.py) of treating the emitter as angle-
independent for that term only: emit_atm = 1 - atm(lambda),
emitt_spec_times_emit_atm = emit_atm * emit. Every quantity that depends on
this (Tequil, Radiat. power, and anything downstream of the equilibrium
solve) inherits that approximation.

The Reference row's optical file has no separate normal-incidence column;
per the same agreement, its normal-incidence silicon absorptance is left
defaulted to the hemispherical value (OpticsResult's built-in fallback).
"""

from __future__ import annotations

import os

from radcoolpv import config as config_module
from radcoolpv._compat import trapz
from radcoolpv.optics.averages import _find_first, pv_band_averages
from radcoolpv import pipeline

BASE = os.path.dirname(os.path.abspath(__file__))

# Published Table 1 values (Optics Express 30(18), 32965, Table 1).
TABLE1 = {
    "Reference":          dict(Jsc=306, Pmpp=188, incr=None, Tequil=323, Refl=133, Radiat=471, Voc=0.708),
    "Flat soda-lime":     dict(Jsc=337, Pmpp=210, incr=11.7,  Tequil=319, Refl=179, Radiat=434, Voc=0.715),
    "Hemisph. soda-lime": dict(Jsc=355, Pmpp=222, incr=18.1,  Tequil=319, Refl=170, Radiat=472, Voc=0.722),
    "Flat PDMS":          dict(Jsc=342, Pmpp=214, incr=13.8,  Tequil=318, Refl=162, Radiat=456, Voc=0.722),
    "Hemisph. PDMS":      dict(Jsc=360, Pmpp=225, incr=19.7,  Tequil=319, Refl=153, Radiat=483, Voc=0.722),
}

# Row -> YAML config (each sets run.optics_results to that row's reduced optical-property file).
YAML_FILES = {
    "Reference":          os.path.join(BASE, "table1_reference.yaml"),
    "Flat soda-lime":     os.path.join(BASE, "table1_flat_sodalime.yaml"),
    "Hemisph. soda-lime": os.path.join(BASE, "table1_hemisph_sodalime.yaml"),
    "Flat PDMS":          os.path.join(BASE, "table1_flat_pdms.yaml"),
    "Hemisph. PDMS":      os.path.join(BASE, "table1_hemisph_pdms.yaml"),
}


def run_row(name: str) -> dict:
    cfg = config_module.load(YAML_FILES[name])
    ctx = pipeline.run(cfg)
    optics = ctx.optics
    thermal = ctx.thermal
    solar_per_um = ctx.extras["solar_per_um"]

    # "Refl. power" = solar-weighted reflected power in the sub-bandgap band
    # (lambda_g .. 4 um) only, via radcoolpv's own pv_band_averages (port of
    # averagePropsFunc.m). Order-of-magnitude check against Table 1 confirmed
    # this definition (Reference: 133.24 vs 133 published; Flat soda-lime:
    # 179.88 vs 179) -- a full-spectrum reflected-power integral is ~2x too
    # high because it also counts the (intentionally large) UV/active-band
    # reflectance these structures are designed to have.
    lam = optics.lambda_um
    avg = pv_band_averages(lam, optics.abs_silicon, optics.ref, optics.emit,
                            solar_per_um, thermal.equil_temp)
    gp = _find_first(lam, 1.12, 1.2e-2)
    esp = _find_first(lam, 4.0, 1.5e-2)
    s_subgap = trapz(solar_per_um[gp:esp + 1], lam[gp:esp + 1])
    refl_power = avg.subgap_ref / 100.0 * s_subgap

    radiat_power = thermal.rad_power_equil

    return dict(
        Jsc=thermal.isc, Pmpp=thermal.mpp_equil, Tequil=thermal.equil_temp,
        Refl=refl_power, Radiat=radiat_power, Voc=thermal.voc_equil,
    )


def main() -> None:
    computed = {name: run_row(name) for name in YAML_FILES}

    ref_pmpp = computed["Reference"]["Pmpp"]
    for name, c in computed.items():
        c["incr"] = None if name == "Reference" else (c["Pmpp"] - ref_pmpp) / ref_pmpp * 100.0

    cols = ["Jsc", "Pmpp", "incr", "Tequil", "Refl", "Radiat", "Voc"]
    print(f"{'Structure':<20}{'Qty':<8}{'Published':>12}{'Computed':>12}{'Rel.err %':>12}")
    print("-" * 64)
    for name in YAML_FILES:
        pub, comp = TABLE1[name], computed[name]
        for col in cols:
            p, c = pub[col], comp[col]
            if p is None or c is None:
                print(f"{name:<20}{col:<8}{'--':>12}{'--':>12}{'--':>12}")
                continue
            rel = (c - p) / p * 100.0
            pstr = f"{p:.3f}" if isinstance(p, float) else f"{p:g}"
            print(f"{name:<20}{col:<8}{pstr:>12}{c:>12.3f}{rel:>12.2f}")
        print()


if __name__ == "__main__":
    main()
