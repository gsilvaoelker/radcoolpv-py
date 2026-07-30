# radcoolpv

YAML-driven optical, thermal, and electrical modelling of photonic
radiative-cooling PV structures. The implementation is based on the
MATLAB+Lua/S4 `matlab-radCoolPV` model, with direct lazy use of the Stanford S4
Python extension and automatic coupling between optics and the PV energy
balance.

## Capabilities

- S4 RCWA reflectance, transmittance, total absorptance/emittance, and
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
  rcwa_modes: 100
```

One directional TE case:

```yaml
simulation:
  wavelength: {min: 8.0, max: 13.0, n: 300}
  angles: specific
  polar_angle_deg: 35.0
  azimuth_angle_deg: 90.0
  polarization: TE
  rcwa_modes: 100
```

Hemispherical, unpolarized:

```yaml
simulation:
  wavelength: {min: 3.0, max: 30.0, n: 1000}
  angles: hemispherical
  polarization: unpolarized
  hemisphere_theta_points: 8
  hemisphere_azimuth_points: 12
  rcwa_modes: 100
```

Hemispherical runs include one zero-weight normal-incidence probe plus
`theta_points * azimuth_points` quadrature directions. Increase both angular
counts and `rcwa_modes` until the reported quantity is converged.

Live S4 thermal runs require hemispherical optics. A resumed normal-incidence
spectrum can still drive the thermal model when
`run.optics_results_angles: normal`; this is an explicit angle-independent
approximation, not a hemispherical optical calculation.

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

Validation A is a thermal/PV regression using pre-reduced published spectra.
Validation B uses digitized optical or cooling curves; its Figure 5d case is not
an independent calculation. Validation C has YAML-defined S4 optics and
reproduces the grating result, but its paper-prescribed solar absorptance and
normal-spectrum thermal approximation remain explicit limitations. Validation E
uses one YAML for live S4 emittance, paper-stated cooling-power cases, and
calibrated cooling-power reproduction. It matches the 7.5–16 µm calculated
emittance band, while its full 2–16 µm silica spectra remain conditional on a
boundary-condition mismatch. The paper-stated `h = 6.0 W/m²/K` fails both its
reported temperatures and an independent zero-emitter check. Separate YAML
cases use a documented joint fit `h_total = 12.54 W/m²/K` and label the
resulting temperatures as calibrated reproduction, not independent convection
validation.

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
