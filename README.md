# radcoolpv

`radcoolpv` is a YAML-driven simulator for photovoltaic structures with
radiative cooling. A case connects three stages:

1. **Optics:** obtain wavelength-dependent reflectance, transmittance, total
   absorptance/emittance, and silicon-layer absorptance from live S4 or a
   stored spectrum.
2. **Thermal balance:** combine the spectrum with sunlight, atmospheric
   radiation, thermal emission, and nonradiative heat transfer to solve the
   operating temperature.
3. **PV model:** calculate the IV curve, short-circuit current, open-circuit
   voltage, maximum power, fill factor, and efficiency.

The inputs are readable YAML files. Output-enabled runs write CSV data,
figures, and a `run.json` record containing the resolved configuration,
provenance, input hashes, and main scalar results.

## Run in Google Colab

Students do not need to install Python or S4 locally. Open a notebook, choose
**Runtime → Run all**, and edit the indicated YAML parameters in the temporary
Colab checkout.

| Notebook | Purpose |
|---|---|
| [Main optical and PV tutorial](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/radcoolpv_colab.ipynb) | Compile S4, run a small optical case, and obtain PV parameters and figures |
| [Validation A](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_a_colab.ipynb) | Reproduce the five stored-spectrum Table 1 comparisons |
| [Validation A.1](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_a1_colab.ipynb) | Run the soda-lime hemisphere workflow; optional live S4 rebuild |
| [Validation B](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_b_colab.ipynb) | Calculate cooling curves from digitized PDMS-based spectra |
| [Validation C](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_c_colab.ipynb) | Compare planar and grating silica; optional live S4 rebuild |
| [Validation E](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_e_colab.ipynb) | Compare Akerboom optics and paper-stated versus fitted thermal cases |

The teaching site is
[gsilvaoelker.github.io/radcoolpv-py](https://gsilvaoelker.github.io/radcoolpv-py/).
It explains the equations, YAML structure, outputs, validation results,
figures, references, and limitations.

Colab runtimes are temporary. The setup must run again after a reset. The
validation notebooks use committed spectra by default so the normal classroom
path is fast. Optional live S4 calculations are clearly marked; reduced grids
and low mode counts are smoke tests, not publishable convergence studies.

## Supported S4 build

S4 has a Python interface, but it is not a pure-Python package: its C/C++
extension must be compiled for the current operating system, architecture, and
Python runtime. `radcoolpv` imports it lazily, so stored-spectrum and
thermal-only cases work without S4.

The supported and tested Colab target is the
[`phoebe-p/S4`](https://github.com/phoebe-p/S4) `devel` fork pinned at commit
[`9569f5e555b967a4324eb1ea593d0f9f40761a61`](https://github.com/phoebe-p/S4/commit/9569f5e555b967a4324eb1ea593d0f9f40761a61).
Other S4 forks or revisions are not compatibility targets for these notebooks.

Live S4 supports normal incidence, one specified polar/azimuthal direction,
or hemispherical theta–phi quadrature with TE, TM, or unpolarized illumination.
Increase `s4_modes` and the angular grid until a named reported quantity is
converged.

## Install locally on macOS or Linux

The thermal/PV path and stored-spectrum readers need only the Python package:

```bash
./install.sh
source .venv/bin/activate
```

Live optics additionally needs the compiled S4 module. For example, on Apple
silicon:

```bash
brew install fftw suite-sparse openblas lapack boost
git clone https://github.com/phoebe-p/S4
cd S4
git checkout 9569f5e555b967a4324eb1ea593d0f9f40761a61
make -f Makefile.m1 S4_pyext
python -c "import S4; print(S4.__file__)"
```

## Define and run a YAML case

A minimal normal-incidence optical grid is:

```yaml
simulation:
  wavelength: {min: 8.0, max: 13.0, n: 101}
  angles: normal
  polarization: unpolarized
  s4_modes: 20
```

A hemispherical calculation uses:

```yaml
simulation:
  wavelength: {min: 3.0, max: 30.0, n: 1000}
  angles: hemispherical
  polarization: unpolarized
  hemisphere_theta_points: 8
  hemisphere_azimuth_points: 12
  s4_modes: 100
```

Run or inspect a case with:

```bash
radcoolpv run configs/full.yaml --print-config
radcoolpv run configs/full.yaml
radcoolpv run configs/optics_only.yaml
radcoolpv run configs/freeform.yaml
```

One YAML may contain a top-level `cases:` list. The CLI executes the named
cases in order; Validation E uses this form.

### Live, free-form, and resumed optics

- `geometry.source: s4` runs the live optical solver.
- `geometry.source: freeform` reads an external wavelength-dependent input.
- `run.optics: false` with `run.optics_results` resumes a committed or prior
  reduced spectrum.

S4 is the only live solver. The other two paths are data readers, not
alternative electromagnetic solvers. A resumed normal-incidence spectrum can
drive the thermal model, but the atmospheric term is then an explicitly
angle-independent approximation.

To chain two YAML files, set `run.optics_export` in the optical case and point
`run.optics_results` in the thermal case at the same five-column file.
Timestamped `optics.csv` is a reporting output and is not the resumable format.

## Outputs

An output-enabled run creates a timestamped folder containing:

- `optics.csv`, and `optics_directional.csv` for live directional data;
- `iv.csv`, `power.csv`, or `cooling_power.csv`, as applicable;
- `run.json`, with the resolved YAML, environment, Git revision, input hashes,
  S4 binary provenance when available, and scalar results;
- `figures/` when `run.plots: true`.

Set `run.write_outputs: false` for programmatic regressions that should not
create timestamped artifacts.

## Validation status

Automated tests cover flat-stack S4/TMM agreement, patterned-structure energy
closure, layer-resolved silicon absorption, archived MATLAB/S4 parity,
angular and polarization handling, and thermal/PV regressions.

```bash
PYTHONPATH=. python -m pytest -q
```

The literature cases are evidence-labelled rather than uniformly called
“validated.” Validation A uses pre-reduced spectra; A.1 is a smoke test;
Validation B relies on digitized inputs; Validation C is partial; and
Validation E reproduces cooling-band optics but fails the paper-stated thermal
coefficient. Read the [validation page](https://gsilvaoelker.github.io/radcoolpv-py/validations.html)
or [`validations/README.md`](validations/README.md) before citing a result.

## Repository layout

```text
radcoolpv/        active package
configs/          runnable YAML examples
tests/            automated checks
validations/      evidence-labelled literature and workflow cases
docs/site/        Jupyter Book sources, Colab notebooks, and site figures
```
