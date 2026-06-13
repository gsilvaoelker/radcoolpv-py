"""Top-level orchestrator.

Reads the ``run`` toggles and runs the optics and/or thermal stages, coupling
them in memory (no manual results-folder path to keep in sync). Outputs and
plots are gated by ``run.outputs`` / ``run.plots``.
"""

from __future__ import annotations

import os

from .config import Config
from .io.results import RunContext, make_results_dir


def print_resolved(cfg: Config) -> None:
    """Print the resolved settings (defaults applied, derived values computed)."""
    w = cfg.simulation.wavelength
    angles = cfg.angle_array_deg()
    print("radcoolpv — resolved configuration")
    print("-" * 50)
    print(f"  run.optics   : {cfg.run.optics}")
    print(f"  run.thermal  : {cfg.run.thermal}")
    print(f"  run.plots    : {cfg.run.plots}")
    print(f"  run.mode     : {cfg.run.mode}")
    print(f"  run.outputs  : {cfg.run.outputs}")
    print(f"  results_dir  : {cfg.resolve(cfg.run.results_dir)}")
    print(f"  wavelength   : {w.min}-{w.max} um, n={w.n}")
    print(f"  angles       : {cfg.simulation.angles} "
          f"({len(angles)} angle(s): {angles[0]}..{angles[-1]} deg)")
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
    from .optics import directional, freeform, s4_backend

    atmosphere = cfg.resolve_data(cfg.data.atmosphere)
    n_lambda = cfg.simulation.wavelength.n

    if not cfg.run.optics:
        # Resume: read a previous optics results folder (OUTPUTS4 files).
        folder = cfg.resolve_data(cfg.run.optics_results)
        raw = directional.from_folder(folder, n_lambda)
        return directional.reduce(raw, atmosphere, lambda_grid=cfg.wavelength_array())

    if cfg.geometry.source == "freeform":
        ff = cfg.resolve_data(cfg.geometry.freeform["file"])
        print(f"[optics]  reading free-form data: {os.path.basename(ff)}")
        return freeform.load(ff, n_lambda, atmosphere)

    grid = cfg.wavelength_array()
    angles = cfg.angle_array_deg()
    print(f"[optics]  S4 sweep: {len(grid)} wavelengths x {len(angles)} angle(s)")
    raw = s4_backend.sweep(cfg, grid, angles)
    ctx.extras["raw"] = raw
    return directional.reduce(raw, atmosphere, lambda_grid=grid)


def _write_outputs(cfg: Config, ctx: RunContext) -> None:
    from .io import clean_writers, legacy_writers
    from .optics import averages

    optics, thermal = ctx.optics, ctx.thermal
    opt_avg = pv_avg = None
    if optics is not None:
        opt_avg = averages.optical_band_averages(
            optics.lambda_um, optics.ref, optics.emit, optics.abs_silicon)
    if thermal is not None and thermal.iv is not None:
        solar_per_um = ctx.extras.get("solar_per_um")
        if solar_per_um is not None:
            pv_avg = averages.pv_band_averages(
                optics.lambda_um, optics.abs_silicon, optics.ref, optics.emit,
                solar_per_um, thermal.equil_temp)

    if "legacy" in cfg.run.outputs:
        if "raw" in ctx.extras:
            legacy_writers.write_raw_optics(ctx.results_dir, ctx.extras["raw"])
        if optics is not None:
            legacy_writers.write_optical_log(ctx.results_dir, cfg, optics, opt_avg)
            legacy_writers.write_pv_optical_props(ctx.results_dir, optics)
        if thermal is not None and thermal.iv is not None:
            legacy_writers.write_iv(ctx.results_dir, thermal)
            legacy_writers.write_power(ctx.results_dir, thermal)
            legacy_writers.write_pv_log(ctx.results_dir, cfg, thermal, pv_avg)

    if "clean" in cfg.run.outputs:
        if optics is not None:
            clean_writers.write_optics_csv(ctx.results_dir, optics)
        if thermal is not None and thermal.iv is not None:
            clean_writers.write_iv_csv(ctx.results_dir, thermal)
            clean_writers.write_power_csv(ctx.results_dir, thermal)
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
        print(f"[thermal] T_eq = {ctx.thermal.equil_temp:.2f} K, "
              f"Vmpp = {ctx.thermal.vmpp:.4f} V, MPP = {ctx.thermal.mpp_equil:.2f} W/m2")

    # --- outputs + plots -------------------------------------------------- #
    _write_outputs(cfg, ctx)
    if cfg.run.plots:
        from .plotting import figures
        written = figures.make_all(ctx)
        print(f"[plots]   wrote {len(written)} figure(s)")

    print(f"Done. Results in: {results_dir}")
    return ctx
