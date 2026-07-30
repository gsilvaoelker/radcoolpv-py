# radcoolpv

YAML-driven optical, thermal, and electrical modelling of photonic
radiative-cooling PV structures. The implementation is based on the
MATLAB+Lua/S4 `matlab-radCoolPV` model, with direct lazy use of the Stanford S4
Python extension and automatic coupling between optics and the PV energy
balance.

## Capabilities

- S4 reflectance, transmittance, total absorptance/emittance, and
  silicon-layer absorptance.
- Normal incidence, one arbitrary polar/azimuthal direction, or a
  hemispherical theta-phi quadrature.
- TE, TM, or unpolarized illumination.
- Steady-state operating temperature, diode I-V characteristics, MPP, output
  power, efficiency, and temperature reduction relative to a YAML-defined
  reference temperature.
- Clean CSV outputs and a JSON reproducibility manifest. MATLAB-style output
  compatibility has been removed.

S4 is the only live optical solver. Free-form and reduced-spectrum inputs are
readers for external or historical data, not alternative solvers.

## Installation

```bash
./install.sh
source .venv/bin/activate
```

The thermal/electrical path and spectrum readers require only the Python
dependencies installed by `install.sh`. Live optics additionally requires the
compiled S4 Python module:

```bash
brew install fftw suite-sparse openblas lapack boost
git clone https://github.com/phoebe-p/S4
cd S4
make -f Makefile.m1 S4_pyext      # Apple silicon
```

S4 is imported only when `geometry.source: s4` is executed. Verify the active
interpreter with:

```bash
python -c "import S4; print(S4.__file__)"
```

## YAML directions and polarization

Normal, unpolarized:

```yaml
simulation:
  wavelength: {min: 0.3, max: 30.0, n: 2000}
  angles: normal
  polarization: unpolarized
  s4_modes: 100
```

One directional TE case:

```yaml
simulation:
  wavelength: {min: 8.0, max: 13.0, n: 300}
  angles: specific
  polar_angle_deg: 35.0
  azimuth_angle_deg: 90.0
  polarization: TE
  s4_modes: 100
```

Hemispherical, unpolarized:

```yaml
simulation:
  wavelength: {min: 3.0, max: 30.0, n: 1000}
  angles: hemispherical
  polarization: unpolarized
  hemisphere_theta_points: 8
  hemisphere_azimuth_points: 12
  s4_modes: 100
```

Hemispherical runs include one zero-weight normal-incidence probe plus
`theta_points * azimuth_points` quadrature directions. Increase both angular
counts and `s4_modes` until the reported quantity is converged.

Live S4 thermal runs require hemispherical optics. A resumed normal-incidence
spectrum can still drive the thermal model, but its atmospheric term is then an
angle-independent approximation rather than a hemispherical calculation. Note
that `run.optics_results_angles` records what the stored spectrum is; it does
not change any computed value.

## Run

```bash
radcoolpv run configs/full.yaml
radcoolpv run configs/optics_only.yaml
radcoolpv run configs/freeform.yaml
radcoolpv run configs/full.yaml --print-config
```

One YAML may contain a top-level `cases:` list. The CLI executes those named
cases in order. Validation E uses this form so students configure one file
without running helper scripts.

Each output-enabled run writes:

- `optics.csv`: the requested directional or hemispherically reduced spectrum;
- `iv.csv`, `power.csv`, or `cooling_power.csv`, when applicable;
- `run.json`: full resolved YAML, runtime information, Git revision, S4 binary
  hash, input hashes, and scalar results;
- `figures/`, when `run.plots: true`.

Live S4 runs additionally write `optics_directional.csv` with every computed
direction and polarization.

To chain an optics run into a later thermal run with no intermediate step, set
`run.optics_export` to a fixed path and point the second config's
`run.optics_results` at it; they are the write and read halves of the same
five-column format. `optics.csv` cannot be reused for this — it is
comma-separated with a text header, in a timestamped folder.

Set `run.write_outputs: false` for programmatic validation runs.

For temperature reduction relative to a known reference:

```yaml
thermal:
  reference_temperature: 360.0
```

The result is `reference_temperature - equilibrium_temperature`. The reference
must be physically defined by the user; the library does not invent a baseline.

## Scientific status

The test suite includes:

- S4 against analytic TMM for flat TE/TM stacks;
- patterned-structure energy conservation;
- layer-resolved silicon absorption with a lossy downstream layer;
- archived MATLAB/Lua/S4 patterned-case parity;
- theta-phi quadrature and polarization handling;
- thermal and PV unit/regression checks;
- literature diagnostics in `validations/`.

Run:

```bash
PYTHONPATH=. python -m pytest -q
```

The literature cases in `validations/` differ in evidentiary strength, from
conditional regressions against pre-reduced published spectra to live S4 optics.
Some reproduce their paper only under stated approximations, and one fails its
paper's convection coefficient outright. Each case states its DOI, results, and
limitations in `validations/README.md`; read that before citing any of them.

See `docs/manual/radcoolpv_manual.pdf` for equations, conventions, validation
tables, and complete examples.

## Repository layout

```text
radcoolpv/       active package
configs/         runnable YAML examples
tests/           automated checks
validations/     active, evidence-labelled validation cases
docs/manual/     source and compiled manual
archive/         local historical MATLAB and superseded code; gitignored
```
