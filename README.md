# radcoolpv

> **Work in progress.** This project is under active development. The API, the
> YAML schema, the notebooks, and the reported numbers may change without
> notice, and several literature cases are only partially reproduced. Read the
> [validation status](#validation-status) before citing or reusing a result.

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

## Contents

- [Run in Google Colab](#run-in-google-colab) — notebook index, no local install
- [Main equations and assumptions](#main-equations-and-assumptions)
- [Supported S4 build](#supported-s4-build)
- [Install locally on macOS or Linux](#install-locally-on-macos-or-linux)
- [Define and run a YAML case](#define-and-run-a-yaml-case)
- [Outputs](#outputs)
- [Validation status](#validation-status)
- [Repository layout](#repository-layout)

## Run in Google Colab

Students do not need to install Python or S4 locally. Open a notebook, choose
**Runtime → Run all**, and edit the indicated YAML parameters in the temporary
Colab checkout.

| Notebook | Open | Purpose |
|---|---|---|
| Main optical and PV tutorial | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/radcoolpv_colab.ipynb) | Compile S4, run a small optical case, and obtain PV parameters and figures |
| Validation A | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_a_colab.ipynb) | Reproduce the five stored-spectrum Table 1 comparisons |
| Validation A.1 | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_a1_colab.ipynb) | Run the soda-lime hemisphere workflow; optional live S4 rebuild |
| Validation B | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_b_colab.ipynb) | Calculate cooling curves from digitized PDMS-based spectra |
| Validation C | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_c_colab.ipynb) | Compare planar and grating silica; optional live S4 rebuild |
| Validation E | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_e_colab.ipynb) | Compare Akerboom optics and paper-stated versus fitted thermal cases |

The teaching site is
[gsilvaoelker.github.io/radcoolpv-py](https://gsilvaoelker.github.io/radcoolpv-py/).
It explains the equations, YAML structure, outputs, validation results,
figures, references, and limitations.

Colab runtimes are temporary. The setup must run again after a reset. The
validation notebooks use committed spectra by default so the normal classroom
path is fast. Optional live S4 calculations are clearly marked; reduced grids
and low mode counts are smoke tests, not publishable convergence studies.

## Main equations and assumptions

A fuller treatment, with the numerical checks a result must pass, is on the
[theory page](https://gsilvaoelker.github.io/radcoolpv-py/theory.html).

### Optics

From the S4 flux amplitudes at the top and bottom of the stack,

$$
R=-\frac{P^-_{\mathrm{top}}}{P_{\mathrm{inc}}},\qquad
T=\frac{P^+_{\mathrm{bottom}}}{P_{\mathrm{inc}}},\qquad
A=1-R-T,
$$

and the silicon absorptance $A_{\mathrm{Si}}$ follows from the net flux
difference across the two silicon interfaces. Unpolarized illumination is the
mean of the two polarizations, $X_{\mathrm{unpol}}=(X_{\mathrm{TE}}+X_{\mathrm{TM}})/2$,
and the hemispherical average, written $\langle X\rangle$, uses projected
solid-angle weighting,

$$
\langle X\rangle(\lambda)=\frac{1}{\pi}\int_0^{2\pi}\!\!\int_0^{\pi/2}
X(\lambda,\theta,\phi)\cos\theta\sin\theta\,\mathrm{d}\theta\,\mathrm{d}\phi .
$$

A superscript $\perp$ denotes the same quantity at normal incidence, so
$A_{\mathrm{Si}}^{\perp}=A_{\mathrm{Si}}(\lambda,\theta=0)$. Emittance is
identified with absorptance by Kirchhoff's law,
$\epsilon(\lambda,\theta,\phi)=A(\lambda,\theta,\phi)$.

### Atmosphere and energy balance

The directional atmospheric emittance is built from the tabulated zenith
transmittance $\tau_{\mathrm{atm}}$,

$$
\epsilon_{\mathrm{atm}}(\lambda,\theta)=1-\tau_{\mathrm{atm}}(\lambda)^{1/\cos\theta},
$$

and the radiative terms are Planck-weighted integrals over wavelength and the
hemisphere,

$$
P_{\mathrm{rad}}(T)=\int\!\mathrm{d}\Omega\cos\theta\!\int\!\mathrm{d}\lambda\,
B_\lambda(T)\,\epsilon(\lambda,\theta),
\qquad
P_{\mathrm{atm}}=\int\!\mathrm{d}\Omega\cos\theta\!\int\!\mathrm{d}\lambda\,
B_\lambda(T_{\mathrm{amb}})\,\epsilon(\lambda,\theta)\,
\epsilon_{\mathrm{atm}}(\lambda,\theta),
$$

where $B_\lambda$ is the Planck spectral radiance. Since
$\int\mathrm{d}\Omega\cos\theta=\pi$ over the hemisphere, the code evaluates
both from pre-averaged spectra,

$$
P_{\mathrm{rad}}(T)=\pi\!\int\!\langle\epsilon\rangle B_\lambda(T)\,\mathrm{d}\lambda,
\qquad
P_{\mathrm{atm}}=\pi\!\int\!\langle\epsilon\,\epsilon_{\mathrm{atm}}\rangle\,
B_\lambda(T_{\mathrm{amb}})\,\mathrm{d}\lambda .
$$

The atmospheric term averages the **product**. Because
$\epsilon_{\mathrm{atm}}$ varies steeply with $\theta$,
$\langle\epsilon\,\epsilon_{\mathrm{atm}}\rangle\neq\langle\epsilon\rangle\langle\epsilon_{\mathrm{atm}}\rangle$,
and only the former is correct.

Absorbed sunlight and non-radiative exchange are

$$
P_{\mathrm{sun}}=\int\!\langle\epsilon\rangle\,I_{\mathrm{AM1.5}}(\lambda)\,\mathrm{d}\lambda,
\qquad
P_{\mathrm{conv}}(T)=h\,(T-T_{\mathrm{amb}}).
$$

The solar term uses the same angle-averaged absorptance as the thermal terms
rather than the absorptance at one solar direction.

The balance solved for the operating temperature is

$$
P_{\mathrm{cool}}(T)=P_{\mathrm{rad}}(T)-P_{\mathrm{atm}}+P_{\mathrm{conv}}(T)
-P_{\mathrm{sun}}+P_{\mathrm{MPP}}(T)+P_{\mathrm{nt}}(T),
$$

with the equilibrium temperature the root of $P_{\mathrm{cool}}(T_{\mathrm{eq}})=0$.
Check this sign convention before comparing with another paper or program.

### PV model

The band gap follows Varshni, and its wavelength sets the upper limit of every
photogeneration integral:

$$
E_g(T)=E_{g0}-\frac{\alpha T^2}{T+\beta},\qquad \lambda_g=\frac{hc}{E_g}.
$$

Short-circuit and saturation current densities come from the measured internal
quantum efficiency, the silicon absorptance, and the solar and blackbody photon
fluxes $\Phi$:

$$
J_{\mathrm{sc}}=q\!\int_0^{\lambda_g}\!\mathrm{IQE}\,\langle A_{\mathrm{Si}}\rangle\,
\Phi_{\mathrm{sun}}\,\mathrm{d}\lambda,
\qquad
J_0(T)=q\!\int_0^{\lambda_g}\!\mathrm{IQE}\,\langle A_{\mathrm{Si}}\rangle\,
\Phi_{\mathrm{bb}}(T)\,\mathrm{d}\lambda .
$$

Auger recombination adds a bias-dependent term with a tabulated, temperature-
interpolated coefficient $C_{\mathrm{A}}$ and intrinsic concentration $n_i$,

$$
J_{\mathrm{Aug}}(V,T)=2q\,C_{\mathrm{A}}(T)\,n_i^3(T)\,d_{\mathrm{Si}}
\exp\!\left(\frac{3qV}{2k_BT}\right),
$$

and the single-diode I-V with series and shunt resistance is solved implicitly
for $J$ at each voltage, writing $V_d=V-JR_s$:

$$
J=\frac{V_d}{R_{\mathrm{sh}}}
+J_0\!\left[\exp\!\left(\frac{qV_d}{k_BT}\right)-1\right]
+J_{\mathrm{Aug}}-J_{\mathrm{sc}} .
$$

The output power density is $P=-JV$; $P_{\mathrm{MPP}}$ and $V_{\mathrm{MPP}}$
are its sub-grid maximum, $V_{\mathrm{oc}}$ the interpolated zero crossing of
$-J$, and

$$
\mathrm{FF}=\frac{P_{\mathrm{MPP}}}{J_{\mathrm{sc}}V_{\mathrm{oc}}},
\qquad
\eta=\frac{P_{\mathrm{MPP}}}{P_{\mathrm{AM1.5}}},
\qquad
\beta_P=\frac{P_{\mathrm{MPP}}(T_{\mathrm{amb}})-P_{\mathrm{MPP}}(T_{\mathrm{eq}})}
{T_{\mathrm{amb}}-T_{\mathrm{eq}}}\cdot\frac{100}{P_{\mathrm{MPP}}(T_{\mathrm{amb}})} .
$$

Luminescent (non-thermal) emission from the cell depends on the operating
point, so $V_{\mathrm{MPP}}$ and $T_{\mathrm{eq}}$ are obtained together by
fixed-point iteration:

$$
P_{\mathrm{nt}}(T)=\pi\exp\!\left(\frac{qV_{\mathrm{MPP}}}{k_BT}\right)
\int_0^{\lambda_g}\!\mathrm{IQE}\,A_{\mathrm{Si}}^{\perp}\,
B_\lambda(T)\,\mathrm{d}\lambda .
$$

This is the only term that uses the normal-incidence absorptance rather than
the hemispherical average.

### Assumptions

Optical:

- Media are linear, passive, reciprocal, non-magnetic, and in local thermal
  equilibrium, which is what licenses $\epsilon=A$.
- S4 solves RCWA: the structure is laterally infinite and strictly periodic,
  layers are coherent, and the Fourier basis is truncated at `s4_modes`. A
  result is only meaningful once it is converged in modes, wavelength grid, and
  angular quadrature.
- Material data are tabulated or analytic dispersions from the sources listed
  in `radcoolpv/materials/SOURCES.md`; extrapolation outside their range is not
  performed.

Thermal:

- Steady state, with one lumped temperature for the whole stack — no in-plane
  or through-thickness gradient.
- Radiative exchange is one-sided, per unit area, into a plane-parallel sky at
  ambient temperature, using a single stored clear-sky transmittance. Clouds,
  ground exchange, and site-specific atmospheres are not modelled.
- All non-radiative exchange is one temperature-independent coefficient $h$
  lumping convection and conduction.
- The full absorptance $\epsilon$ heats the module, while only $A_{\mathrm{Si}}$
  generates carriers: parasitic absorption is a thermal load and no more.
- $P_{\mathrm{MPP}}$ is subtracted from the balance, so the module is assumed to
  run at its maximum power point with the electrical energy exported rather
  than dissipated.
- A resumed normal-incidence spectrum can drive the thermal model, but the
  atmospheric term is then an explicitly angle-independent approximation.

PV:

- Single-diode model with constant $R_s$ and $R_{\mathrm{sh}}$, ideality one,
  and radiative saturation current from detailed balance below $\lambda_g$.
- $\lambda_g$ is reduced to a single scalar over the temperature sweep,
  reproducing the MATLAB original, so the integration cut-off does not move
  with $T$.
- IQE is read from a measured file and set to zero outside its range.
- Sunlight is the AM1.5 global spectrum, absorbed through the hemispherically
  averaged absorptance rather than at a single solar direction — consistent
  with AM1.5G including a diffuse component. There is no explicit sun
  position, spectral shift, or concentration.

Numerical:

- All spectral integrals are trapezoidal on the user's wavelength grid, so the
  grid must resolve the bands that matter, including the 8-13 um atmospheric
  window.
- Cost scales roughly as $n_\lambda n_\theta n_\phi n_{\mathrm{pol}}$; the
  default full YAML is not a free-Colab exercise without reducing the grid.

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
“validated.” Validation A uses pre-reduced spectra; A.1 is a smoke test; A.2
reproduces the published PDMS spectrum from live S4 at normal incidence only;
Validation B relies on digitized inputs; Validation C is partial; and
Validation E reproduces cooling-band optics but fails the paper-stated thermal
coefficient. Read the [validation page](https://gsilvaoelker.github.io/radcoolpv-py/validations.html)
or [`validations/README.md`](validations/README.md) before citing a result.

A.2 is the case that tests the optical solver itself: it computes the spectrum
from YAML geometry that the paper states in full, then compares it against the
published one. The 8–13 µm window emittance agrees to 0.04%.

## Repository layout

```text
radcoolpv/        active package
configs/          runnable YAML examples
tests/            automated checks
validations/      evidence-labelled literature and workflow cases
docs/site/        Jupyter Book sources, Colab notebooks, and site figures
```
