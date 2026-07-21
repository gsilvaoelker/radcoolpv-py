# radcoolpv validations

This folder holds literature-reproduction checks for `radcoolpv`.

**Trusted (verified to run):** Validations A, B, C and E.

* **A** and **B** resume from precomputed spectra (`run.optics: false`) and so
  validate the **thermal / PV** stage independently of the optics engine.
* **C** and **E** additionally run the **S4 RCWA optics** engine end to end,
  computing a patterned structure's emissivity from first principles and feeding
  it to the thermal balance — **C** a 1-D silica micro-grating, **E** a 2-D
  microcylinder array.

Validation **D** (Li et al., ACS Photonics 2017) **cannot be reproduced** and
stays in the gitignored `../archive/` folder: its photonic cooler is an aperiodic
multilayer whose thicknesses are in a supplementary table not included with the
paper, two of its materials (Al₂O₃, TiO₂) are not in the bundled material set,
and its thermal model is a multilayer conduction FDM rather than radcoolpv's
lumped balance. See `../archive/validation D/README.md`.

Source papers are **not** redistributed with this repository — they are
copyrighted publisher PDFs. Each validation below names its paper; cite by DOI.

All commands below are run from the repository root (`.../radcoolpv-py/`) with
the package installed (`./install.sh`, or `pip install -e .`). Both trusted
validations **resume from precomputed optical spectra** (`run.optics: false`), so
they never invoke the RCWA engine and need no S4 build.

---

## Validation A — Silva-Oelker & Jaramillo-Fernandez (Opt. Express 2022), Table 1

Hemisphere photonic structures (soda-lime / PDMS, flat / hemispherical) for
radiative cooling of a silicon solar cell.

* **Purpose.** Reproduce every row of Table 1 — the full-PV figures of merit —
  from precomputed, hemispherically-reduced optical spectra.
* **Inputs.** Five configs (`table1_reference.yaml`, `table1_flat_sodalime.yaml`,
  `table1_hemisph_sodalime.yaml`, `table1_flat_pdms.yaml`,
  `table1_hemisph_pdms.yaml`), each pointing `run.optics_results` at a reduced
  spectrum under `validation A/data/Fig. *`. Bundled defaults supply the AM1.5G
  solar spectrum, the Cerro-Pachón atmosphere, and the silicon IQE.
* **Mode.** `standard` (full PV energy balance + diode I–V).
* **Expected output.** A table of Published / Computed / Rel-err for
  `Jsc, Pmpp, ΔP%, Tequil, Refl, Radiat, Voc`. Agreement is good: most rows are
  within ~2 %. Known larger residuals are `Radiat` (~1–2 %, definition of the
  radiated-power band) and `Refl` for the PDMS rows (~8–10 %, the sub-bandgap
  reflected-power definition — see the notes in `run_table1_validation.py`).
* **What it validates.** The full electrical + thermal energy balance
  (short-circuit current, MPP, Voc, equilibrium temperature, radiated power)
  against published values.
* **Assumptions / limitations (from `run_table1_validation.py`).** Only
  hemispherically-reduced spectra are available, so the atmospheric-power term
  `P_atm` is computed treating emissivity as angle-independent; the Reference
  row's normal-incidence silicon absorptance falls back to the hemispherical
  value.

Run:

```bash
python "validations/validation A/run_table1_validation.py"
```

## Validation B — Le et al. (ACS Photonics 2026), Fig. 4d / Fig. 5d

Silica-particle/PDMS films for passive radiative cooling of solar panels.

* **Purpose.** Reproduce the bare-film cooling-power-vs-temperature curves
  (Fig. 4d) and compare the panel-level heat-transfer family (Fig. 5d).
* **Inputs.** Four configs (`fig4d_pdms.yaml`, `fig4d_sds.yaml`,
  `fig4d_ads.yaml`, `fig5d_cooling_family.yaml`). Fig. 4d configs read digitized
  optical spectra from `validation B/data/digitized_optics/`; bundled AM1.5G and
  atmosphere are used, with `solar_irradiance: 800` W/m² and `hc = 9` W/m²K.
  `fig5d_cooling_family.yaml` is a digitized-curve comparison only.
* **Mode.** `cooling_curve` (PV-free radiative balance over a temperature sweep).
* **Expected output.** For each Fig. 4d film, a `cooling_power.csv`, a cooling
  curve figure, and a printed equilibrium temperature. As verified here:
  PDMS `T_eq ≈ 329.9 K`, SDS `≈ 328.3 K`, ADS `≈ 325.4 K`. All four configs
  complete ("Done").
* **What it validates.** The radiative-cooling energy balance
  (`P_rad − P_atm + P_conv − P_sun = 0`) and the equilibrium-temperature solve
  from measured optical spectra.
* **Assumptions / limitations (from `validation B/README.md`).** Films treated as
  opaque; the 14–30 µm emissivity is held at its 14 µm value; ambient
  temperature is a validation default (unconfirmed by the paper); the bundled
  Cerro-Pachón atmosphere is not Hiroshima's climate. Fig. 5d is a digitized
  comparison — the paper does not provide the raw module optics needed for an
  independent calculation.

Run:

```bash
for f in fig4d_pdms fig4d_sds fig4d_ads fig5d_cooling_family; do
  radcoolpv run "validations/validation B/$f.yaml"
done
```

---

## Validation C — Zhao et al. (Renewable Energy 2022), silica micro-grating

A 1-D silica micro-grating (period 7 µm, ridge 1.4 µm, depth 10 µm) etched into
a silica cooler, the first validation to run radcoolpv's `grating` shape.
`build_optics_s4.py` computes the planar and grating emissivity with S4; the
`cell_*.yaml` configs run the `cooling_curve` balance. The grating fills silica's
9 µm reststrahlen dip, raising the window emissivity to 0.93 (paper ~0.9), and
the grating-silica cell lands at 37.8 °C above ambient (paper 37.5 °C). See
`validation C/README.md` for the bare-cell / silicon-model caveat.

```bash
cd "validation C" && python run_validation.py          # rebuild optics + validate
python run_validation.py --no-build                     # reuse committed spectra
```

## Validation E — Akerboom et al. (ACS Photonics 2022), silica microcylinders

Silica-microcylinder module glass for radiative cooling of a Si solar module.
`build_optics_s4.py` computes the flat and microcylinder emissivity with S4 RCWA,
and the `stack_*.yaml` configs feed it to the `cooling_curve` balance. Reproduces
the paper's band-averaged emissivity to ≤0.6 pp and every equilibrium temperature
to ≤0.6 K. See `validation E/README.md` for the two method caveats (RCWA vs the
paper's FDTD on the Mie-resonant cylinders; Ag vs Au back mirror).

```bash
cd "validation E" && python run_validation.py          # rebuild optics + validate
python run_validation.py --no-build                     # reuse committed spectra
```

## Archived

Moved to `../archive/` (local, gitignored): Validation **D** (see its README for
why it cannot be reproduced), the earlier fitted-optics version of the Akerboom
reproduction (superseded by the S4 Validation E above), and the source PDFs for
all of these plus Validations A and C.
