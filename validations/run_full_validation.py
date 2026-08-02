"""Server driver for the FULL hemispherical validation runs (hours, not minutes).

Runs live S4 optics, the thermal balance and the PV model in ONE process, at
hemispherical incidence, then compares the result against Table 1 of:

  Silva-Oelker & Jaramillo-Fernandez, Opt. Express 30(18), 32965 (2022).

WHY ONE PROCESS
    The cheap A.1 workflow exports a spectrum and resumes it in a second run.
    That must not be used here. ``write_optics_export`` writes five columns
    (lambda, R, T, emit, abs_si), which drops the normal-incidence columns and
    the angle-resolved atmospheric term. Resuming such a file silently degrades
    the thermal stage to emit_atm = 1 - atm and the product-of-averages form
    emit_atm * emit, while the correct hemispherical term is the angular
    average of the product, <emit * emit_atm>. Keeping both stages in one
    process preserves the in-memory OpticsResult, which carries the right term.

WHICH CASE TO RUN
    pdms      The paper states this geometry in full ("a periodic cell of
              (17.3, 10) um"), so a disagreement is attributable to the code.
              This is the run worth citing.
    sodalime  The pitch is ASSUMED close-packed; the paper never states it.
              Converging this does not make it a Table 1 reproduction. Run it
              to converge the soda-lime geometry itself, not to validate.

Differences are reported; nothing is asserted. The script exits 0 either way.

Examples
--------
    # Size the job first -- prints estimates and exits without computing.
    python validations/run_full_validation.py --case both --dry-run

    # The citable run, detached, with a log.
    nohup python validations/run_full_validation.py --case pdms \
        > full_pdms.log 2>&1 &

    # Cheaper exploratory pass.
    python validations/run_full_validation.py --case pdms --modes 20 \
        --wavelengths 500
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import sys
import time

import numpy as np

from radcoolpv import config as config_module
from radcoolpv import pipeline
from radcoolpv._compat import trapz
from radcoolpv.optics.averages import _find_first, pv_band_averages

BASE = os.path.dirname(os.path.abspath(__file__))

CASES = {
    "sodalime": {
        "yaml": os.path.join(BASE, "validation A.1", "full_hemisph_sodalime.yaml"),
        "row": "Hemisph. soda-lime",
        "citable": False,
        "caveat": "pitch is ASSUMED close-packed; not a Table 1 reproduction",
    },
    "pdms": {
        "yaml": os.path.join(BASE, "validation A.2", "full_hemisph_pdms.yaml"),
        "row": "Hemisph. PDMS",
        "citable": True,
        "caveat": "geometry fully stated by the paper",
    },
}

#: Published Table 1 values (Optics Express 30(18), 32965).
TABLE1 = {
    "Hemisph. soda-lime": dict(Jsc=355, Pmpp=222, Tequil=319, Refl=170,
                               Radiat=472, Voc=0.722),
    "Hemisph. PDMS": dict(Jsc=360, Pmpp=225, Tequil=319, Refl=153,
                          Radiat=483, Voc=0.722),
}

#: Measured seconds per single S4 solve vs s4_modes, from the A.2 convergence
#: sweep on an M-series laptop at this geometry class. Used only to estimate
#: runtime; a server will differ, so treat the estimate as an order of
#: magnitude, not a promise.
SOLVE_SECONDS = {10: 0.0030, 20: 0.0155, 30: 0.0378, 45: 0.133, 60: 0.250}


def _log(msg: str) -> None:
    stamp = _dt.datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)


def _per_solve(modes: int) -> float:
    """Interpolate the measured cost model in log-log space."""
    xs = np.array(sorted(SOLVE_SECONDS))
    ys = np.array([SOLVE_SECONDS[x] for x in xs])
    return float(np.exp(np.interp(np.log(modes), np.log(xs), np.log(ys))))


def _solve_count(cfg) -> int:
    theta, _, _ = cfg.simulation.directions()
    return len(cfg.simulation.wavelength.array()) * len(theta) * len(
        cfg.simulation.polarization_names())


def _fmt_hours(seconds: float) -> str:
    if seconds < 90:
        return f"{seconds:.0f} s"
    if seconds < 5400:
        return f"{seconds / 60:.0f} min"
    return f"{seconds / 3600:.1f} h"


def _load(case: str, args) -> object:
    cfg = config_module.load(CASES[case]["yaml"])
    if args.modes is not None:
        cfg.simulation.s4_modes = args.modes
    if args.theta is not None:
        cfg.simulation.hemisphere_theta_points = args.theta
    if args.azimuth is not None:
        cfg.simulation.hemisphere_azimuth_points = args.azimuth
    if args.wavelengths is not None:
        cfg.simulation.wavelength.n = args.wavelengths
    if args.layers is not None:
        cfg.geometry.discretization_layers = args.layers
    config_module.validate(cfg)
    return cfg


def _reflected_power(optics, thermal, solar_per_um) -> float:
    """Sub-bandgap solar-weighted reflected power, as Validation A defines it.

    Kept identical to run_table1_validation.py so the two cannot drift: a
    full-spectrum reflected integral is about twice this and is not what
    Table 1 reports.
    """
    lam = optics.lambda_um
    avg = pv_band_averages(lam, optics.abs_silicon, optics.ref, optics.emit,
                           solar_per_um, thermal.equil_temp)
    gp = _find_first(lam, 1.12, 1.2e-2)
    esp = _find_first(lam, 4.0, 1.5e-2)
    if gp is None or esp is None:
        return float("nan")
    return avg.subgap_ref / 100.0 * trapz(solar_per_um[gp:esp + 1], lam[gp:esp + 1])


def run_case(case: str, args) -> None:
    meta = CASES[case]
    cfg = _load(case, args)
    solves = _solve_count(cfg)
    estimate = solves * _per_solve(cfg.simulation.s4_modes)

    _log(f"=== {case} ({meta['row']}) ===")
    _log(f"    {meta['caveat']}")
    _log(f"    s4_modes={cfg.simulation.s4_modes}, "
         f"theta={cfg.simulation.hemisphere_theta_points}, "
         f"azimuth={cfg.simulation.hemisphere_azimuth_points}, "
         f"layers={cfg.geometry.discretization_layers}, "
         f"wavelengths={cfg.simulation.wavelength.n}")
    _log(f"    {solves:,} S4 solves; rough estimate {_fmt_hours(estimate)} "
         f"(laptop cost model -- your server will differ)")

    if args.dry_run:
        _log("    dry run: nothing computed")
        return

    t0 = time.time()
    ctx = pipeline.run(cfg)
    elapsed = time.time() - t0
    _log(f"    finished in {_fmt_hours(elapsed)} "
         f"({elapsed / max(solves, 1) * 1000:.2f} ms per solve)")

    optics, thermal = ctx.optics, ctx.thermal
    closure = float(np.abs(optics.ref + optics.tran + optics.emit - 1.0).max())
    _log(f"    energy closure, max |R+T+A-1| = {closure:.2e}")
    if ctx.results_dir:
        _log(f"    results: {ctx.results_dir}")

    computed = dict(
        Jsc=thermal.isc, Pmpp=thermal.mpp_equil, Tequil=thermal.equil_temp,
        Refl=_reflected_power(optics, thermal, ctx.extras["solar_per_um"]),
        Radiat=thermal.rad_power_equil, Voc=thermal.voc_equil,
    )
    published = TABLE1[meta["row"]]

    print(flush=True)
    print(f"{'Quantity':<10}{'Published':>12}{'Computed':>12}{'Rel.err %':>12}",
          flush=True)
    print("-" * 46, flush=True)
    for key in ("Jsc", "Pmpp", "Tequil", "Refl", "Radiat", "Voc"):
        pub, com = published[key], computed[key]
        if not np.isfinite(com):
            print(f"{key:<10}{pub:>12g}{'n/a':>12}{'--':>12}", flush=True)
            continue
        rel = (com - pub) / pub * 100.0 if pub else float("nan")
        print(f"{key:<10}{pub:>12g}{com:>12.3f}{rel:>+12.2f}", flush=True)
    print(flush=True)

    if not np.isfinite(computed["Refl"]):
        _log("    Refl is n/a: its 1.12 and 4.0 um band edges are located with "
             "the MATLAB find() tolerance,")
        _log("    which needs a fine wavelength grid. Expected on a reduced "
             "--wavelengths run; fine at 2000.")

    if not meta["citable"]:
        _log("    REMINDER: this row's pitch is assumed. Agreement here is not "
             "evidence, and disagreement is not a code defect.")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", choices=("sodalime", "pdms", "both"),
                    default="pdms", help="which full run (default: pdms)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the cost estimate and exit without computing")
    ap.add_argument("--modes", type=int, help="override simulation.s4_modes")
    ap.add_argument("--theta", type=int,
                    help="override simulation.hemisphere_theta_points")
    ap.add_argument("--azimuth", type=int,
                    help="override simulation.hemisphere_azimuth_points")
    ap.add_argument("--layers", type=int,
                    help="override geometry.discretization_layers")
    ap.add_argument("--wavelengths", type=int,
                    help="override simulation.wavelength.n")
    args = ap.parse_args()

    cases = ("sodalime", "pdms") if args.case == "both" else (args.case,)
    _log(f"radcoolpv full validation | python {sys.version.split()[0]} | "
         f"cases: {', '.join(cases)}")
    for case in cases:
        run_case(case, args)
    _log("done")


if __name__ == "__main__":
    main()
