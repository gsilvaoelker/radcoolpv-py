# radcoolpv

Radiative cooling of silicon photovoltaics: from a module's emittance spectrum
to its operating temperature and its PV parameters. The spectrum can be one
you measured, one digitized from a paper, or one computed here with the S4
RCWA solver from a layer stack and a photonic pattern.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/radcoolpv.ipynb)
— nothing to install. **Runtime → Run all**, then edit a case and run it again.

> Work in progress. One literature case is reproduced; read [validation](#validation) before citing a number.

## A case is a YAML file with three blocks

A block is computed when it is present.

```yaml
optics:                            # where the spectrum comes from ...
  file: my_emittance.txt           #   a table: wavelength in um in column 0,
  column: 3                        #   emittance in this column
thermal:                           # present -> solve the energy balance
  ambient_temperature: 300.0       # K
  convection_coefficient: 6.0      # W/m2-K, everything non-radiative
cell:                              # present -> solve the single-diode cell
  silicon_thickness: 500.0         # um
```

Delete `cell:` and you get the cooling curve alone. Replace `file:` with a
structure and S4 computes the spectrum:

```yaml
optics:
  wavelength: {min: 0.3, max: 24.9, n: 1000}
  angles: hemispherical            # normal | hemispherical (thermal needs hemispherical)
  hemisphere_theta_points: 8
  hemisphere_azimuth_points: 1
  s4_modes: 60
  geometry:
    shape: cylinder                # flat | cylinder | sphere | semisphere | triangle | grating
    photonic_material: sio2
    lattice: {type: hexagonal, x: 10.608811, y: 6.125}
    cylinder: {radius: 1.75, height: 2.25}
  structure:                       # top to bottom, um
    - {material: sio2,    thickness: 500.0}
    - {material: silicon, thickness: 500.0}
    - {material: gold,    thickness: 0.08}
  substrate: vacuum                # the semi-infinite layer below
  materials:                       # every name used above -> a model in radcoolpv/materials
    sio2: PalikKitamura_SiO2
    silicon: Palik_Si
    gold: RII_Olmon_2012_ev_Au
thermal: {ambient_temperature: 300.0, convection_coefficient: 6.0}
cell: {}                           # silicon_thickness is read from the structure
```

`examples/` holds these as runnable files; a file may also hold a `cases:` list
of named cases (`validation/akerboom.yaml` does).

### Every key

| key | default | meaning |
|---|---|---|
| `optics.file` | — | table with wavelength (um) in column 0 |
| `optics.column` | none | emittance column; omit for an `optics.txt` radcoolpv wrote |
| `optics.wavelength` | 0.3–30 um, n=2000 | the grid every integral is taken on; must stay inside every material table |
| `optics.angles` | hemispherical | `normal` for a quick optics-only look |
| `optics.polarization` | unpolarized | TE, TM, unpolarized |
| `optics.hemisphere_theta_points` / `_azimuth_points` | 8 / 12 | angular quadrature; azimuth 1 is exact for a lattice-symmetric structure |
| `optics.s4_modes` | 10 | Fourier truncation; patterned layers need 60–100+ |
| `optics.geometry.shape` | flat | `cylinder {radius, height}`, `sphere` / `semisphere {radius, layers}`, `triangle {base, height, layers}`, `grating {duty, depth}` |
| `optics.geometry.photonic_material` | vacuum | material of the pattern |
| `optics.geometry.lattice` | square, x=y=20 | `square {x}` or `hexagonal {x, y}` with x = y·√3 |
| `optics.structure` | — | list of `{material, thickness}` (um), top to bottom |
| `optics.substrate` | vacuum | semi-infinite layer below the stack |
| `optics.materials` | — | logical name → model name (`radcoolpv/materials/SOURCES.md`) |
| `thermal.ambient_temperature` | 298 K | |
| `thermal.convection_coefficient` | 12 W/m²·K | convection and conduction lumped; the most sensitive input |
| `thermal.temperatures` | ambient … ambient+150 K | sweep `{min, max, n}`; also sets the band-gap cut-off (see `docs/model.md`) |
| `thermal.absorbed_solar_power` | from AM1.5G | W/m²; replaces the spectral integral |
| `thermal.reference_temperature` | none | K; reports the reduction from it |
| `thermal.atmosphere_file` | bundled clear sky | zenith transmittance table |
| `cell.silicon_thickness` | from the structure | um; required with `optics.file` |
| `cell.series_resistance` / `shunt_resistance` | 1.1e-4 / 0.1 Ω·m² | |
| `cell.bandgap` | Varshni Si | `{eg0, alpha, beta}` |
| `cell.iqe_file` | bundled Si IQE | `lambda_um IQE` table |
| `cell.voltage` | 0.1–0.8 V, n=100 | I–V sweep |

## Run it

```bash
radcoolpv run examples/pv_from_spectrum.yaml          # no solver needed
radcoolpv run validation/akerboom.yaml --case C3_pv_cylinders
radcoolpv run case.yaml --print-config --no-plots --results-dir out
```

In Python: `report.summary(pipeline.run(config.load("case.yaml")))`.

Every run writes `results/<case>_<time>/` with `optics.txt` (the spectrum:
`lambda R T emit abs_si emit*emit_atm`, which `optics.file` reads back
exactly), `iv.csv` and `power.csv` or `cooling_power.csv`, `figures/`, and
`run.json` — the resolved case, input hashes, and every scalar result.
Quantities a run did not solve for are absent, not zero.

## Install locally

```bash
./setup.sh
source ~/.venvs/radcoolpv-py/bin/activate
```

That covers everything except computing a spectrum, which needs S4. It has no
PyPI package; the notebook builds it from source on Linux, and on a Mac:

```bash
brew install fftw suite-sparse openblas lapack boost
git clone https://github.com/phoebe-p/S4 && cd S4
git checkout 9569f5e555b967a4324eb1ea593d0f9f40761a61
make -f Makefile.m1 S4_pyext        # Apple silicon; else: make S4_pyext
```

The venv lives outside the repository on purpose: inside an iCloud-synced
folder macOS marks it hidden and the editable install silently breaks.

## Validation

Akerboom *et al.*, *ACS Photonics* **9**, 3831 (2022),
[doi:10.1021/acsphotonics.2c01389](https://doi.org/10.1021/acsphotonics.2c01389):
hexagonal silica microcylinders on silica / silicon / gold.
`validation/akerboom.yaml` holds twelve cases in three groups; the spectra
groups A and C compute are committed under `validation/data/` so everything
below reproduces without a solver.

| | bare Au/Si | flat silica | cylinders |
|---|---:|---:|---:|
| A. mean emittance 7.5–16 um, radcoolpv / paper Fig. 3a | 0.032 / 0.036 | 0.842 / 0.843 | 0.984 / 0.977 |
| B. T_eq from the *measured* emittance, h = 6.0 (paper) | 415.4 K | 360.6 K | 355.6 K |
| B. same, h = 12.54 fitted to Fig. 5b | 359.7 K | 340.1 K | 337.5 K |
| C. full model: T_eq | 350.5 K | 329.3 K | 327.0 K |
| C. efficiency | 14.17 % | 18.09 % | 18.64 % |

The paper reports 360 / 339 / 336 K and a 24 K drop from bare to cylinders;
the model gives 23.5 K. Group B shows the thermal model is only as good as
`h`, which lumps mounting, wind and area: the fitted value is a calibration,
not evidence. `tests/test_validation_akerboom.py` pins every number here.

```bash
PYTHONPATH=. python -m pytest -q      # S4-dependent tests skip without S4
```

The model, its assumptions and its sign convention: [`docs/model.md`](docs/model.md).
