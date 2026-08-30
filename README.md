# radcoolpv

> **Work in progress.** This project is under active development; the API, the
> YAML schema, and the reported numbers may change without notice. One
> literature case is reproduced, and it reproduces the optics but not the
> paper's stated thermal coefficient. Read the
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

- [Run in Google Colab](#run-in-google-colab) — no local install
- [Main equations and assumptions](#main-equations-and-assumptions)
- [Supported S4 build](#supported-s4-build)
- [Install locally on macOS](#install-locally-on-macos)
- [Define and run a YAML case](#define-and-run-a-yaml-case)
- [Outputs](#outputs)
- [Validation status](#validation-status)
- [Repository layout](#repository-layout)

## Run in Google Colab

Nothing to install. Open the notebook, choose **Runtime → Run all**, and edit
the YAML in the notebook itself.

| Notebook | S4? | Purpose |
|---|---|---|
| Main tutorial | no | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/radcoolpv_colab.ipynb) — edit a case, upload data, read powers, temperatures and PV parameters |
| Validation A — optics | needed | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_a_optics.ipynb) — emittance from the geometry, against the paper's Fig. 3a |
| Validation B — cooling | no | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_b_cooling.ipynb) — the energy balance alone, and how sensitive it is to the convection coefficient |
| Validation C — full cell | needed | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_c_pv.ipynb) — optics, heat and electricity coupled |

Every notebook runs to completion with **no solver and no prompt**: the
converged optics for groups A and C were computed once with S4 and committed
under `validation/data/`, so each notebook reproduces the table in its own
introduction in seconds. Each states the physics, shows its YAML in full so it
can be edited, and carries a `MY_DATA` switch that uploads a spectrum and runs
the case on it. A and C add `RECOMPUTE_WITH_S4`, which builds the solver and
computes the optics from the geometry instead of reading them; B never needs a
solver at all.

A full run takes about a minute and needs no electromagnetic solver. It
produces the equilibrium temperature, every term in the energy balance, the
full set of PV parameters, and the figures. The notebook also accepts uploaded
optical property files — measured spectra, or an `n`/`k` table that becomes a
usable material — and has an optional section that compiles S4 and computes the
optics from the geometry instead of reading them from a file.

The teaching site is
[gsilvaoelker.github.io/radcoolpv-py](https://gsilvaoelker.github.io/radcoolpv-py/).

Colab runtimes are temporary; the setup cell must run again after a reset.

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
  with $T$. It is a weighted mean over the whole swept range, so **setting
  `thermal.cooling_temperature` moves the cut-off** and with it $J_{sc}$ and
  $\beta_P$. The default range is left at the MATLAB one, $T_{amb}$ to
  $T_{amb}+150$ K, for that reason; widen it deliberately, not incidentally.
- When the optics come from a single supplied emittance column, $A_{Si}$ is
  taken to equal $\epsilon$ below $\lambda_g$ and zero above, since parasitic
  absorption above the gap is neglected. `run.json` records that this was
  assumed rather than solved.
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

## Install locally on macOS

The thermal/PV path and stored-spectrum readers need only the Python package:

```bash
./setup.sh
source ~/.venvs/radcoolpv-py/bin/activate
```

Three things to know:

- The environment is created outside the repository, at `~/.venvs/radcoolpv-py`
  (override with `VENV_DIR`). A virtual environment placed inside an
  iCloud-synced folder such as `~/Documents` or `~/Desktop` is marked hidden by
  macOS, and Python skips hidden `.pth` files, which silently disables the
  editable install: `radcoolpv` then fails to import outside the repository root.
- Inside the activated environment use `python`, not `python3`. A `python3`
  alias in your shell profile shadows the environment even when it is active,
  and reports a missing dependency such as `No module named 'yaml'`.
- A stale `radcoolpv` console script left on `PATH` by an earlier
  `pip install -e .` into another interpreter (for a Homebrew Python,
  `/opt/homebrew/bin/radcoolpv`) still points at wherever the repository was at
  the time of that install. A console script puts its own directory on
  `sys.path` rather than the working directory, so running `radcoolpv` without
  activating the environment reports `No module named 'radcoolpv'` even from
  inside the repository. Check with `which -a radcoolpv`; remove the stale copy
  with `<interpreter> -m pip uninstall radcoolpv`.

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

```bash
radcoolpv run validation/akerboom.yaml --print-config   # resolve, print, stop
radcoolpv run validation/akerboom.yaml                  # run every case
radcoolpv run validation/akerboom.yaml --case B3_cooling_h6_cylinders
radcoolpv run examples/freeform_pv.yaml                 # full PV, no S4
```

A file may hold a top-level `cases:` list; the CLI runs them in order and
`--case` selects by name. A case that fails does not abort the others — a file
mixing solver cases with file-driven ones still runs everything it can on a
machine with no S4, and reports what it skipped.

### Choosing a wavelength range

The range is yours. It must fit inside every material table used in the same
case, and the error names the file that is too narrow:

| Model | Range (um) |
|---|---|
| `RII_Olmon_2012_ev_Au` | 0.300 – 24.93 |
| `SiliconNew`, `Akerboom_Si_lossless` | 0.280 – 30.0 |
| `Palik_Si` | 0.191 – 40.0 |
| `PalikKitamura_SiO2` | 0.280 – 100 |
| `Hagemann_Ag` | 2.48e-06 – 248 |
| `DrudeSi3N4` | analytic, unbounded |

Band averages are integrated over exactly the band requested, with the two
endpoints interpolated onto the grid, so the reported value does not depend on
whether a sample happens to land on a band edge. A band the grid does not span
is **omitted** from `run.json` rather than reported as zero.

`n` is not a free parameter. Every spectral integral is trapezoidal on your
grid, so the grid has to resolve the bands that matter — including the 8–13 um
atmospheric window. Cost scales as `n_lambda x n_theta x n_phi x n_pol`.

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
  wavelength: {min: 0.3, max: 24.9, n: 1000}
  angles: hemispherical
  polarization: unpolarized
  hemisphere_theta_points: 8
  hemisphere_azimuth_points: 1
  s4_modes: 60
```

### Live, free-form, and supplied optics

- `geometry.source: s4` runs the live optical solver.
- `geometry.source: freeform` reads an external wavelength-dependent input.
- `run.optics: false` with `run.optics_results` reads a stored spectrum, and
  **never imports S4 at all**.

S4 is the only live solver; the other two are data readers, not alternative
electromagnetic solvers. A supplied normal-incidence spectrum can drive the
thermal model, but its atmospheric term is then an explicitly angle-independent
approximation.

`run.optics_results` accepts a six-column `lambda, R, T, emit, A_Si,
<emit*emit_atm>` export, the older five-column form without that last column, a
seven-column form, or — with `run.optics_results_emittance_column` — one
emittance column of a plain table, treating the surface as opaque.

Only the six-column form reproduces the hemispherical run it came from. A live
sweep builds the atmospheric term as the angular average of
`emit_atm(λ,θ)·emit(λ,θ)`, and no spectrum carries enough information to rebuild
that, so a reader given only the averaged emittance falls back to the zenith
atmosphere. Exporting the pre-integrated product removes the approximation, and
`run.optics_export` writes it.

That last form carries no layer-resolved absorptance, so the silicon share is
inferred: **above the band gap essentially everything absorbed is absorbed in
the silicon, and below it nothing is.** This is what lets a measured emittance
spectrum drive the PV stage. It only has to be right about which side of the
gap a wavelength falls on, because `thermal/pv.py` then truncates at its own
temperature-dependent `lambda_g`. `run.json` records
`optics.silicon_from_emittance: true` so a resumed PV result is never mistaken
for a solved one. A spectrum that stops above the gap — the digitized Akerboom
traces start at 2 um — yields no photocurrent, correctly.

To chain two files, set `run.optics_export` in the optical case and point
`run.optics_results` in the thermal case at the same file.
Timestamped `optics.csv` is a reporting output and is not the resumable format.

## Outputs

An output-enabled run creates a timestamped folder containing:

- `optics.csv`, and `optics_directional.csv` for live directional data;
- `iv.csv`, `power.csv`, or `cooling_power.csv`, as applicable;
- `run.json`, with the resolved YAML, environment, Git revision, input hashes,
  S4 binary provenance when available, and the scalar results — the equilibrium
  temperature, every term of the energy balance (which closes to zero there),
  and, when a cell was actually solved, the full PV set. Quantities the run did
  not solve for are absent rather than zero: a cooling-curve run reports no
  efficiency instead of an efficiency of zero;
- `figures/` when `run.plots: true`.

Set `run.write_outputs: false` for programmatic regressions that should not
create timestamped artifacts.

## Validation status

One case: Akerboom *et al.*, *ACS Photonics* **9**, 3831–3840 (2022),
[doi:10.1021/acsphotonics.2c01389](https://doi.org/10.1021/acsphotonics.2c01389)
— hexagonal silica microcylinders (radius 1.75 um, height 2.25 um, pitch
6.125 um) on 500 um silica / 500 um silicon / 80 nm gold.
`validation/akerboom.yaml` defines twelve cases in three groups.

**Group A — optics (needs S4).** Mean emittance over 7.5–16 um, against
Figure 3a:

| Surface | radcoolpv | Digitized | Paper text |
|---|---:|---:|---:|
| Bare Au/Si | 0.032 | 0.036 | ~3.5% |
| Flat silica | 0.842 | 0.843 | — |
| Silica cylinders | 0.984 | 0.977 | — |

**Group B — cooling curve (no S4).** The thermal model alone, driven by the
digitized Figure 5a *measured* emittance, so the result depends on the energy
balance rather than on the solver. Run with `h = 6.0` W/m2-K, the value stated
in the paper's Methods:

| Surface | radcoolpv | Paper Fig. 5b |
|---|---:|---:|
| Bare Au/Si | 415.4 K | 360 K |
| Flat silica | 360.6 K | 339 K |
| Silica cylinders | 355.6 K | 336 K |

The equilibrium temperature is sensitive to the non-radiative coefficient, and
`h` lumps convection and conduction into one number whose value depends on
mounting, wind and the area assumed. A single least-squares fit to all three
digitized curves gives `h = 12.54` W/m2-K and reproduces 359.7 / 340.1 /
337.5 K. Both are kept as separate, labelled cases: the fitted agreement is a
**calibration**, so it is not evidence that the thermal model is independently
validated. `tests/test_validation_akerboom.py` pins both sets of numbers.

**Group C — full optical, thermal and electrical result (needs S4).** The
paper's headline claim is a temperature drop, and the model reproduces it:

| Surface | T_eq | Efficiency | MPP | beta_P |
|---|---:|---:|---:|---:|
| Bare Au/Si | 350.5 K | 14.17% | 142.6 W/m2 | -0.303 %/K |
| Flat silica | 329.3 K | 18.09% | 182.1 W/m2 | -0.299 %/K |
| Silica cylinders | 327.0 K | 18.64% | 187.7 W/m2 | -0.300 %/K |

Bare to flat silica is 21.2 K against the paper's 21 K, flat to cylinders 2.3 K
against 3 K, and bare to cylinders 23.5 K against 24 K. Absorbed sunlight rises
from 507.5 to 598.6 to 614.3 W/m2 across the three, so most of the efficiency
gain is antireflection rather than cooling.

Automated tests additionally cover flat-stack S4/TMM agreement to 1e-9,
patterned-structure energy closure, layer-resolved silicon absorption, archived
MATLAB/S4 parity, angular and polarization handling, band-average behavior on
arbitrary grids, and thermal/PV regressions:

```bash
PYTHONPATH=. python -m pytest -q
```

The twelve S4-dependent tests are skipped when S4 is not built, so a green run
on a default install does not exercise the optical solver.

## Repository layout

```text
radcoolpv/        the package
validation/       the one literature case: YAML, digitized data, the article
examples/         runnable starting points
tests/            automated checks
docs/site/        Jupyter Book sources and the Colab notebook
docs/manual/      printable LaTeX manual
```
