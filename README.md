# radcoolpv

YAML-driven radiative-cooling photovoltaics simulator — a modular Python port of
the MATLAB + Lua/S4 `radCoolPV` toolchain.

A single YAML config drives a two-stage pipeline:

1. **Optics** — spectral / directional reflectance, transmittance, absorptance,
   and silicon-layer absorption of a photonic structure on a multilayer PV
   stack, via RCWA (the **S4** engine), free-form data, or a resumed previous
   run.
2. **Thermal** — the energy balance (radiative, atmospheric, convective, solar,
   electrical, and luminescence terms), the steady-state cell temperature, and
   the PV I–V / MPP / Voc / FF / efficiency / temperature coefficient.

The two stages share one wavelength grid and are coupled **in memory**, so there
is no manual results-folder path to keep in sync. The old manual two-step ritual
(read the equilibrium temperature and MPP voltage off a plot, paste them back,
re-run) is replaced by an automatic fixed-point solve.

`radcoolpv-py/` is **fully self-contained**: all material, spectral, and
validation reference data is bundled inside the package, so it can be copied or
installed anywhere with no dependency on the original `radCoolPV` MATLAB tree.

## Install

```bash
./install.sh             # creates a .venv and installs everything into it
./install.sh --system    # install into the current Python instead of a venv
```

The installer creates a local virtual environment (`.venv`) so it works on
managed system Pythons (Homebrew / PEP 668), installs `requirements.txt`
(numpy / scipy / matplotlib / pyyaml / openpyxl — NumPy 1.x and 2.x both
supported), then `pip install -e .`. Activate it with
`source .venv/bin/activate`.

Equivalently, by hand:

```bash
pip install -r requirements.txt && pip install -e .
```

### The S4 optics engine

The **live RCWA optics stage additionally requires the Stanford S4 module.**
Everything else — the thermal/PV stage, free-form optics, and resuming from an
existing `OUTPUTS4` folder — runs without it.

S4 has **no PyPI package** and must be compiled. Use the maintained fork; the
upstream `victorliu/S4` Python binding still calls the Python 2 C API and no
longer matches its own `libS4` signatures, so it will not build against
Python 3.

```bash
brew install fftw suite-sparse openblas lapack boost   # macOS
git clone https://github.com/phoebe-p/S4 && cd S4
make -f Makefile.m1 S4_pyext      # Apple silicon
make S4_pyext                     # Linux / Intel macOS
```

On Debian/Ubuntu the dependencies are
`libopenblas-dev libfftw3-dev libsuitesparse-dev libboost-all-dev`.

Verify with `python -c "import S4; print(S4)"`. If S4 is missing, any config
with `geometry.source: s4` fails with a message repeating these steps.

## Run

```bash
radcoolpv run configs/full.yaml                 # optics (S4 RCWA) + thermal
radcoolpv run configs/full.yaml --print-config  # just show resolved settings
radcoolpv run configs/optics_only.yaml          # optics only (S4 RCWA)
radcoolpv run configs/freeform.yaml             # free-form optics + PV
radcoolpv run configs/test_perrakis_fig2.yaml   # validation: Perrakis 2020 Fig. 2
```

A live RCWA sweep of a *patterned* structure is the expensive part of a run:
cost scales with wavelengths x angles x `simulation.rcwa_modes`. For a quick
run reduce `simulation.wavelength.n`, lower `rcwa_modes`, or set
`simulation.angles: normal`.

Each run creates a timestamped folder under `results/` containing legacy
MATLAB-style files (`OUTPUTS4-*.txt`, `opticalProps-PVcode.txt`,
`IV-PVcode.txt`, `Power-PVcode.txt`, `simulParam*.log`), clean files
(`optics.csv`, `iv.csv`, `power.csv`, `run.json`), and `figures/` (gated by
`run.plots`).

## Configuration

See `configs/full.yaml` for the annotated reference. Key toggles:

| Key | Meaning |
| --- | --- |
| `run.optics` / `run.thermal` | turn each stage on/off (auto-coupled when both on) |
| `run.plots` | generate figures |
| `run.mode` | `standard` / `cooling_curve` / `test` / `spectral_compare` |
| `run.outputs` | any of `legacy`, `clean` |
| `geometry.source` | `s4` (RCWA) or `freeform` (read optimised data) |
| `geometry.shape` | `flat` / `sphere` / `semisphere` / `triangle` / `cylinder` / `grating` |
| `thermal.equilibrium` | `auto` (fixed point) or `manual` (`emit_temp` + `vmpp`) |

`structure` is an ordered list of flat layers below the photonic structure; the
silicon layer there is the single source of truth for the cell thickness, so the
optics and thermal stages cannot disagree.

## Materials

`materials` maps a logical name (e.g. `sio2`) to a model in the registry
(`radcoolpv/materials`). Tabulated models live as CSVs in
`radcoolpv/materials/data` (converted from the MATLAB tables by
`scripts/convert_permittivity.py`); analytic Drude/Lorentz models live in
`radcoolpv/materials/analytic.py`. Adding a material is a one-liner: drop a CSV,
or register a function.

## Tests

```bash
pytest -q
```

The suite validates the material models against the MATLAB tables, the
directional reduction + band averages against the committed quartz `OUTPUTS4`
log (to all digits), the radiative term against Stefan–Boltzmann, the energy
balance against Perrakis 2020 Fig. 2 (to a few W/m²), and a full free-form +
PV run end-to-end.

## Layout

```
radcoolpv/
  cli.py               `radcoolpv run ...` entry point
  config.py            YAML -> typed config + validation + derived helpers
  constants.py         physical constants / unit conversions
  pipeline.py          orchestrator (stage coupling, outputs, plots)
  materials/           registry + tabulated loader + analytic models + data/
  optics/              geometry, s4_backend, directional, averages, freeform
  thermal/             spectra, radiative, pv, energy_balance
  io/                  results context + legacy/clean writers
  plotting/            figures
  validation/          literature reference loaders + bundled data/
  data/                bundled solar / atmosphere / IQE / free-form example
configs/               example YAML configs
scripts/               convert_permittivity.py
tests/                 pytest suite
validations/           literature reproductions (see validations/README.md)
```

Not tracked: `archive/` holds the original MATLAB toolchain, the one-off
MATLAB-vs-Python comparison, untrusted validations, and the non-redistributable
source PDFs. It is gitignored — see `archive/README.md`.
