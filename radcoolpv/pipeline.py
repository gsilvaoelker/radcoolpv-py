"""Top-level orchestrator: optics -> thermal -> cell, coupled in memory."""

from __future__ import annotations

import os

from .config import Config, Thermal
from .io.results import RunContext, make_results_dir

SOLAR_SPECTRUM = os.path.join(os.path.dirname(__file__), "data", "astmg173.xlsx")


def print_resolved(cfg: Config) -> None:
    """Print the resolved settings (defaults applied, derived values computed)."""
    o = cfg.optics
    print(f"radcoolpv — {cfg.case_name or 'case'}")
    print("-" * 50)
    if o.file is not None:
        column = "radcoolpv optics.txt" if o.column is None else f"column {o.column}"
        print(f"  optics       : file {o.file} ({column})")
    else:
        w = o.wavelength
        theta, _, _ = cfg.direction_arrays()
        print(f"  optics       : S4, {w.min}-{w.max} um, n={w.n}, "
              f"{o.angles} ({len(theta)} direction(s), {o.polarization}), "
              f"{o.s4_modes} modes")
        print(f"  geometry     : {o.geometry.shape}, photonic={o.geometry.photonic_material}")
        print(f"  structure    : {len(o.structure)} layer(s) on {o.substrate}")
    if cfg.thermal is not None:
        print(f"  thermal      : T_amb={cfg.thermal.ambient_temperature} K, "
              f"h={cfg.thermal.convection_coefficient} W/m2K")
    if cfg.cell is not None:
        print(f"  cell         : silicon {cfg.silicon_thickness()} um")
    print("-" * 50)


def _optics(cfg: Config, ctx: RunContext):
    """Read the spectrum from the file, or solve the structure with S4."""
    from .optics import directional

    atmosphere = cfg.resolve_data((cfg.thermal or Thermal()).atmosphere_file)
    o = cfg.optics
    if o.file is not None:
        path = cfg.resolve_data(o.file)
        print(f"[optics]  reading {os.path.basename(path)}")
        return directional.from_file(path, atmosphere, o.column)

    # Imported here, not at module scope, so a file-driven run never needs S4.
    from .optics import s4_backend

    grid = cfg.wavelength_array()
    print(f"[optics]  S4 sweep: {len(grid)} wavelengths "
          f"x {len(cfg.direction_arrays()[0])} direction(s) "
          f"x {len(o.polarization_names())} polarization(s)")
    raw = s4_backend.sweep(cfg, grid)
    ctx.extras["raw"] = raw
    return directional.reduce(raw, atmosphere, lambda_grid=grid)


def run(cfg: Config, results_dir: str = "results", plots: bool = True) -> RunContext:
    """Run the configured blocks; write ``results_dir/<case>_<time>/``."""
    print_resolved(cfg)
    ctx = RunContext(config=cfg, results_dir=make_results_dir(
        results_dir, cfg.case_name or "case"))
    print(f"Results folder: {ctx.results_dir}")

    ctx.optics = _optics(cfg, ctx)

    if cfg.thermal is not None:
        from .thermal import energy_balance
        from .thermal.spectra import load_solar
        solar = load_solar(SOLAR_SPECTRUM, ctx.optics.lambda_um)
        ctx.extras["solar_per_um"] = solar.irradiance_per_um
        print("[thermal] energy balance + equilibrium solve")
        ctx.thermal = energy_balance.run(cfg, ctx.optics, solar)
        if cfg.cell is None:
            print(f"[thermal] zero cooling power at T = {ctx.thermal.equil_temp:.2f} K")
        else:
            print(f"[thermal] T_eq = {ctx.thermal.equil_temp:.2f} K, "
                  f"Vmpp = {ctx.thermal.vmpp:.4f} V, "
                  f"MPP = {ctx.thermal.mpp_equil:.2f} W/m2")

    from .io import clean_writers
    clean_writers.write_all(ctx)
    if plots:
        from .plotting import figures
        written = figures.make_all(ctx)
        print(f"[plots]   wrote {len(written)} figure(s)")

    print(f"Done. Results in: {ctx.results_dir}")
    return ctx
