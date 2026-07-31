# Working with YAML

YAML is the experiment definition. It selects the stages to run, wavelength and
angle grids, geometry, layer stack, material models, thermal parameters, data
files, and outputs.

## Classroom smoke test

The Colab notebook creates an editable `student.yaml` similar to this:

```yaml
run:
  optics: true
  thermal: false
  plots: true
  results_dir: results
  write_outputs: true

simulation:
  wavelength: {min: 8.0, max: 13.0, n: 21}
  angles: normal
  polarization: unpolarized
  s4_modes: 30

geometry:
  source: s4
  shape: cylinder
  photonic_material: sio2
  lattice: {type: square, x: 20.0, y: 20.0}
  discretization_layers: 1
  cylinder: {radius: 5.0, height: 30.0}
```

These values are deliberately cheap. `s4_modes: 30`, 21 wavelengths, and
normal incidence do not establish convergence or a hemispherical thermal
balance.

## Run and inspect

Validate the resolved configuration before spending time on S4:

```bash
radcoolpv run student.yaml --print-config
```

Then run it:

```bash
radcoolpv run student.yaml
```

Each run writes a timestamped folder containing `run.json`, optical or thermal
CSV files, and figures when requested. Keep `run.json`; it records the resolved
configuration and provenance needed to interpret the output.

## `run.json` manifest

The top-level blocks are `resolved_config`, `provenance`, `optics`,
`thermal_results`, and, for PV runs, `band_averages_percent`. Blocks that do
not apply to a case are omitted rather than populated with invented values.

`provenance` records `python`, `platform`, `git_commit`, `git_dirty`, hashed
`inputs`, and the loaded `s4` binary when live optics was used. `optics`
records `angles`, `polarization`, and `n_lambda`.

The thermal scalar keys are `equilibrium_temperature_K`,
`temperature_reduction_K`, `vmpp_V`, `short_circuit_current_A_per_m2`,
`mpp_ambient_W_per_m2`, `mpp_equilibrium_W_per_m2`, `voc_ambient_V`,
`voc_equilibrium_V`, `fill_factor_ambient`, `fill_factor_equilibrium`,
`atmospheric_power_W_per_m2`, `absorbed_solar_power_W_per_m2`,
`temperature_coefficient_perc_per_K`, `efficiency_equilibrium`,
`saturation_current_equilibrium_A_per_m2`, and
`auger_current_equilibrium_at_vmpp_A_per_m2`.

The PV-weighted spectral summary contains `solar_absorptance_silicon`,
`solar_reflectance`, `subgap_reflectance`, `emittance_8_13um`, and
`emittance_4_30um`. Ambient-voltage quantities may be `null` when the voltage
sweep does not bracket the ambient open-circuit voltage.

## From demonstration to scientific calculation

Do not just replace the teaching grid with the largest values that fit in
memory. That is a runtime rabbit hole, not a convergence study.

1. Choose one physical observable, such as band-averaged emittance or
   equilibrium temperature.
2. Refine one discretization at a time: S4 modes, wavelengths, theta points,
   then azimuthal points.
3. Stop when the observable meets a stated tolerance and energy balance remains
   acceptable.

For expensive studies, run live optics once, export the reduced spectrum, and
resume thermal parameter sweeps from that file. A stored hemispherical spectrum
does not retain the full directional field; the atmospheric term is then an
angle-independent approximation. State that limitation.

The repository provides complete examples in [`configs/`](https://github.com/gsilvaoelker/radcoolpv-py/tree/main/configs).
