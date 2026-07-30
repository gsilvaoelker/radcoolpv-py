"""Top-level orchestrator.

Reads the ``run`` toggles and runs the optics and/or thermal stages, coupling
them in memory (no manual results-folder path to keep in sync). Clean outputs
and plots are gated by ``run.write_outputs`` / ``run.plots``.
"""

from __future__ import annotations

import os

from .config import Config
from .io.results import RunContext, make_results_dir


def print_resolved(cfg: Config) -> None:
    """Print the resolved settings (defaults applied, derived values computed)."""
    w = cfg.simulation.wavelength
    print("radcoolpv — resolved configuration")
    print("-" * 50)
    print(f"  run.optics   : {cfg.run.optics}")
    print(f"  run.thermal  : {cfg.run.thermal}")
    print(f"  run.plots    : {cfg.run.plots}")
    print(f"  run.mode     : {cfg.run.mode}")
    print(f"  write outputs: {cfg.run.write_outputs}")
    print(f"  results_dir  : {cfg.resolve(cfg.run.results_dir)}")
    print(f"  wavelength   : {w.min}-{w.max} um, n={w.n}")
    if cfg.run.mode == "spectral_compare":
        print(f"  comparison   : {len(cfg.comparison.spectra)} series")
    elif not cfg.run.optics and cfg.run.optics_results:
        print(f"  optics input : reduced/resumed {cfg.run.optics_results_angles} spectrum")
    else:
        theta, _, _ = cfg.direction_arrays()
        print(f"  directions   : {cfg.simulation.angles} "
              f"({len(theta)} direction(s), {cfg.simulation.polarization})")
    if cfg.run.optics:
        print(f"  geometry     : source={cfg.geometry.source}, shape={cfg.geometry.shape}, "
              f"photonic={cfg.geometry.photonic_material}")
        if cfg.structure:
            print(f"  structure    : {len(cfg.structure)} layers, thickSi={cfg.thick_si()} um")
    if cfg.run.thermal:
        print(f"  thermal      : T_amb={cfg.thermal.ambient_temperature} K, "
              f"h={cfg.thermal.convection_coefficient} W/m2K, "
              f"equilibrium={cfg.thermal.equilibrium}")
    print("-" * 50)


def _run_optics(cfg: Config, ctx: RunContext):
    """Run (or resume) the optics stage, returning an OpticsResult."""
    from .optics import directional, freeform

    atmosphere = cfg.resolve_data(cfg.data.atmosphere)
    n_lambda = cfg.simulation.wavelength.n

    if not cfg.run.optics:
        # Historical MATLAB/S4 folders remain readable only for parity and
        # archived validation inputs. New runs write clean CSV.
        source = cfg.resolve_data(cfg.run.optics_results)
        if os.path.isfile(source):
            return directional.from_reduced_file(
                source, atmosphere, cfg.run.optics_results_angles,
                cfg.run.optics_results_emittance_column)
        raw = directional.from_folder(source, n_lambda)
        return directional.reduce(raw, atmosphere, lambda_grid=cfg.wavelength_array())

    if cfg.geometry.source == "freeform":
        ff = cfg.resolve_data(cfg.geometry.freeform["file"])
        print(f"[optics]  reading free-form data: {os.path.basename(ff)}")
        return freeform.load(ff, n_lambda, atmosphere)

    # Imported here, not at module scope, so the rest of the package works
    # without a compiled S4 (freeform and resume paths need no optics engine).
    from .optics import s4_backend

    grid = cfg.wavelength_array()
    print(f"[optics]  S4 sweep: {len(grid)} wavelengths "
          f"x {len(cfg.direction_arrays()[0])} direction(s) "
          f"x {len(cfg.simulation.polarization_names())} polarization(s)")
    raw = s4_backend.sweep(cfg, grid)
    ctx.extras["raw"] = raw
    return directional.reduce(raw, atmosphere, lambda_grid=grid)


def _write_outputs(cfg: Config, ctx: RunContext) -> None:
    from .io import clean_writers

    optics, thermal = ctx.optics, ctx.thermal
    if not cfg.run.write_outputs:
        return
    if optics is not None:
        clean_writers.write_optics_csv(ctx.results_dir, optics)
    if "raw" in ctx.extras:
        clean_writers.write_directional_csv(
            ctx.results_dir, ctx.extras["raw"])
    if thermal is not None and thermal.iv is not None:
        clean_writers.write_iv_csv(ctx.results_dir, thermal)
        clean_writers.write_power_csv(ctx.results_dir, thermal)
    elif thermal is not None and cfg.run.mode == "cooling_curve":
        clean_writers.write_cooling_curve_csv(ctx.results_dir, thermal)
    clean_writers.write_run_json(ctx.results_dir, cfg, optics, thermal)


def run(cfg: Config) -> RunContext:
    """Run the configured stages and return the populated run context."""
    print_resolved(cfg)

    prefix = "PV-results" if cfg.run.thermal else "results"
    results_dir = make_results_dir(cfg.resolve(cfg.run.results_dir), prefix)
    ctx = RunContext(config=cfg, results_dir=results_dir)
    print(f"Results folder: {results_dir}")

    # --- optics (run live, freeform, or resume from a prior folder) -------- #
    if cfg.run.optics or cfg.run.thermal:
        ctx.optics = _run_optics(cfg, ctx)

    # --- thermal (auto-coupled to the optics result in memory) ------------ #
    if cfg.run.thermal:
        from .thermal import energy_balance
        from .thermal.spectra import load_solar
        solar = load_solar(cfg.resolve_data(cfg.data.solar_spectrum), ctx.optics.lambda_um)
        ctx.extras["solar_per_um"] = solar.irradiance_per_um
        print("[thermal] energy balance + equilibrium solve")
        ctx.thermal = energy_balance.run(cfg, ctx.optics, solar)
        if cfg.run.mode == "cooling_curve":
            print(f"[thermal] zero cooling power at T = "
                  f"{ctx.thermal.equil_temp:.2f} K")
        else:
            print(f"[thermal] T_eq = {ctx.thermal.equil_temp:.2f} K, "
                  f"Vmpp = {ctx.thermal.vmpp:.4f} V, "
                  f"MPP = {ctx.thermal.mpp_equil:.2f} W/m2")

    # --- outputs + plots -------------------------------------------------- #
    _write_outputs(cfg, ctx)
    if cfg.run.plots:
        from .plotting import figures
        written = figures.make_all(ctx)
        print(f"[plots]   wrote {len(written)} figure(s)")

    print(f"Done. Results in: {results_dir}")
    return ctx
