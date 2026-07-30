# Validation status

These cases have different evidentiary strength. "The script runs" is not the
same as "the physical model is independently validated."

| Case | Optics source | What is checked | Status |
|---|---|---|---|
| A | Published reduced spectra | PV and thermal Table 1 quantities | Conditional regression |
| A.1 | Live S4, TE at normal incidence | That a hexagonal cell solves and drives the PV stage | **Not a validation** — configuration smoke test |
| B Fig. 4d | Digitized measured spectra | Cooling balance | Conditional regression |
| B Fig. 5d | Digitized published curves | Plot comparison only | Not an independent validation |
| C | YAML-defined S4 grating cases | Normal unpolarized optics and cooling model | Partial validation |
| E | YAML-defined S4 Au/Si/silica cases | Normal unpolarized optics and thermal model | Optics agrees; thermal fails |

Source PDFs are not tracked. Each case states its DOI and limitations below.

---

## Validation A — Silva-Oelker and Jaramillo-Fernandez (2022)

*Optics Express* **30**(18), 32965, Table 1.

Five YAML files exercise the standard PV pipeline with pre-reduced optical
spectra. They do not exercise S4. The reduced inputs contain no angular TE/TM
data, so atmospheric absorption uses an angle-independent approximation.
Reflected-power discrepancies reach approximately `10%`.

```bash
PYTHONPATH=. python "validations/validation A/run_table1_validation.py"
```

The solar spectrum and atmospheric transmittance are not bundled with this case;
both resolve to the defaults inside the installed package.

Validation A never calls S4. It has no `geometry:` block at all, so the hexagonal
hemisphere array of the paper is implicit in the supplied spectra rather than
expressed in YAML. Case A.1 below exists to exercise that geometry directly.

---

## A.1 — hexagonal cell smoke test (not a validation)

No published comparison, and it must never be cited as evidence. It answers one
question: does a hexagonal cell with a discretised semisphere build and solve in
S4, and do the resulting optics drive the PV stage end to end?

The geometry mirrors Validation A's soda-lime hemisphere row — 9 µm-diameter
soda-lime hemispheres on 75 µm flat soda-lime, over the Si3N4/Si/Ag stack — with
one deliberate deviation: **the array pitch is assumed close-packed (9 µm)**
because the paper's pitch is not recorded in this repository. Together with the
TE normal-incidence optics, that is why the numbers below are not a Table 1
reproduction, even though they land near it.

The hexagonal cell is the centred-rectangular supercell, so for pitch `p`:

```text
lattice: {type: hexagonal, x: sqrt(3) * p, y: p}   # here x = 15.588457, y = 9.0
```

radcoolpv adds the second motif at `(x/2, y/2)` automatically. That second motif
appearing is the specific thing this case checks. Note that `square` ignores
`lattice.y` entirely, and that the centred motif is only added for `cylinder`,
`sphere`, and `semisphere` — `triangle` and `grating` get a plain rectangular
cell.

Two plain CLI runs, in order. Two steps are required because a live S4 run with
`run.thermal: true` is rejected unless `angles: hemispherical`:

```bash
radcoolpv run "validations/validation A.1/optics_hemisph_sodalime.yaml"   # live S4 -> spectrum
radcoolpv run "validations/validation A.1/pv_hemisph_sodalime.yaml"       # spectrum -> PV
```

Nothing happens between them. Step 1 sets `run.optics_export` to a fixed path
and step 2 reads that same path with `run.optics_results`; those two settings
are the write and read halves of the same five-column format. The timestamped
results folder cannot serve this purpose, and neither can `optics.csv`, which is
comma-separated with a text header that the resume reader rejects.

Step 2 sets `optics_results_angles: normal`. That key is provenance metadata
only — it records what the spectrum is and changes no computed value. The
angle-independent approximation comes from the spectrum itself being
normal-incidence, not from the setting.

Observed on the committed spectrum:

| Quantity | Value |
|---|---:|
| max \|R+T+A−1\| | 1.1e-16 |
| Solar-band (0.3–1.1 µm) absorptance in Si | 0.823 |
| 8–13 µm window emittance | 0.973 |
| Equilibrium temperature | 317.09 K |
| Isc | 365.92 A/m² |
| Voc at equilibrium | 0.7264 V |
| MPP at equilibrium | 230.61 W/m² |
| Fill factor | 0.868 |
| Efficiency at equilibrium | 0.2314 |

`s4_modes: 10` and `discretization_layers: 9` are smoke-test settings, not
converged ones. Sweep both before using this geometry for anything quantitative.

---

## Validation B — Le et al. (2026)

*ACS Photonics*, Figures 4d and 5d. "Enhancing Passive Radiative Cooling
Performance on Solar Panels via Multiple Scattering Effects in Aggregated Silica
Particles/Polydimethylsiloxane Films."

Figure 4d is calculated by `cooling_curve` mode from the bundled digitized
optical spectra, `800 W m^-2` solar irradiance, and `h_c = 9 W m^-2 K^-1`. The
digitized Figure 4d curves are plotted only as reference.

Figure 5d is a digitized curve comparison. The paper does not provide the raw
commercial-module stack optics needed for an independent calculation of this
panel-level heat-transfer-coefficient family.

```bash
for f in fig4d_pdms fig4d_sds fig4d_ads fig5d_cooling_family; do
  radcoolpv run "validations/validation B/$f.yaml"
done
```

All inputs required by these YAML files are under `data/`; generated outputs are
written under `results/` and are not part of the validation.

---

## Validation C — Zhao et al. (2022)

"Radiative cooling of solar cells with micro-grating photonic cooler,"
*Renewable Energy* **191** (2022) 662–668,
https://doi.org/10.1016/j.renene.2022.04.063.

The first case to exercise radcoolpv's 1-D `grating` shape: a silica
micro-grating etched into the top of a 500 µm fused-silica cooler.

```text
period p = 7 µm,  silica ridge width w = 1.4 µm  (duty r = w/p = 0.2),
etch depth d = 10 µm
```

### The physics

Bulk silica has a strong phonon–polariton resonance near 9 µm where its
permittivity goes negative (near-metallic), giving a high-reflectivity,
low-emissivity dip right inside the 8–13 µm atmospheric window. The
micro-grating acts as an effective-medium antireflection layer for thermal
emission — it overcomes the silica/air impedance mismatch and fills the 9 µm
dip, raising the window-averaged emissivity from ~0.77 to ~0.94.

### What is validated

| Stage | Paper source | Quantity |
|---|---|---|
| Optics | Fig. 1c / 2d | Window-averaged (8–13 µm) emissivity, planar vs grating |
| Thermal | Fig. 3 | Equilibrium temperature of the 200 µm Si cell, bare vs grating |

```text
A. Cooler optics (Fig. 1c) — S4 window-averaged emissivity 8–13 µm
   cooler               paper      S4
   planar silica        (dip)     77%
   grating silica         90%     94%

B. Cell temperature (Fig. 3) — cooling_curve, 800 W/m², hc = 6, Ta = 300 K
   cell                    paper dT   calc dT
   bare 200 µm Si            77.5 C     93.9 C
   + grating cooler          37.5 C     37.8 C
```

The grating raises the window emittance to 0.938 (paper approximately 0.90), and
the coupled model gives 37.8 °C above ambient versus the paper's 37.5 °C. Both
normal-incidence polarizations are evaluated; the checked 20–80-mode window
average varies by less than 0.001.

```bash
cd "validations/validation C"
python run_validation.py            # rebuild the S4 optics, then validate
python run_validation.py --no-build # reuse the committed data/optics/*.txt
```

`pytest tests/test_validation_zhao_grating.py` checks the committed spectra. The
four `optics_*.yaml` files contain every S4 geometry, material, wavelength,
polarization, and mode setting used by `build_optics_s4.py`.

### Limitations

- **Bare-cell temperature is model-sensitive.** Silicon is nearly transparent in
  the mid-IR, so the bare slab's emissivity (`SiliconNew`, window average 5.6 %)
  — and hence its temperature — is set almost entirely by the silicon optical
  model, not by the cooler. It runs hotter here (93.9 °C vs 77.5 °C above
  ambient), consistent with a less mid-IR-absorbing (undoped) silicon than the
  paper's cell. The grating result is dominated by the strong silica emissivity.
  The test checks the grating temperature tightly and the bare case only as a
  large relative cooling.
- **Fixed solar absorptivity.** A bare 200 µm Si slab without the cell's
  antireflection and texturing absorbs only ~0.5 of AM1.5, versus the paper's
  cell ~0.95 (Fig. 2d). `build_optics_s4.py` therefore fixes the solar band
  (λ ≤ 1.1 µm) to α = 0.95 for the cell stacks, isolating the grating's mid-IR
  emissivity effect from that front-surface artefact. The cooler-alone spectra
  are left untouched.
- **Angular approximation.** The calculated spectrum is normal-incidence,
  unpolarized; the thermal adapter treats it as angle-independent. It is not a
  hemispherical S4 calculation.
- **Back mirror.** Silver (`Hagemann_Ag`) replaces any real cell back contact; it
  only matters for the below-bandgap tail (T ≈ 0 in the mid-IR).
- **Atmosphere.** The paper uses MODTRAN; the bundled Cerro-Pachón
  transmittance is used here.

---

## Validation E — Akerboom et al. (2022)

"Passive Radiative Cooling of Silicon Solar Modules with Photonic Silica
Microcylinders," *ACS Photonics* **9** (2022) 3831–3840,
https://doi.org/10.1021/acsphotonics.2c01389.

One YAML defines nine named cases: three live S4 normal-emittance cases, three
cooling-power cases using the paper-stated `h = 6.0 W/m²/K`, and three
calibrated cooling-power cases. Students change only `validation.yaml`.

```bash
radcoolpv run "validations/validation E/validation.yaml"
```

### Paper geometry and boundary conditions

| Quantity | Calculated design | Fabricated sample |
|---|---:|---:|
| Silica cylinder radius | 1.75 µm | 1.825 µm mean |
| Silica cylinder height | 2.25 µm | 2.20 µm mean |
| Hexagonal pitch | 6.125 µm | 6.125 µm target |
| Silica wafer thickness | semi-infinite in Figure 3 calculation | 500 µm |
| Silicon thickness | not part of the Figure 3 silica-interface model | 500 µm |
| Gold thickness | — | 80 nm |

The paper's calculated Figure 3 model places periodic silica cylinders at an
air/semi-infinite-silica interface and assumes all IR power transmitted into
silica is eventually absorbed. The active YAML instead uses the complete
fabricated 500 µm SiO2 / 500 µm Si / 80 nm Au stack so that S4 reports `R`, `T`,
and `A` for one explicit structure. These are not identical optical boundary
conditions.

The hexagonal lattice is represented by the rectangular primitive cell used by
the inherited S4 geometry: `x = sqrt(3) * 6.125 = 10.608811 µm`, `y = 6.125 µm`.

### Materials

- Au: unmodified refractiveindex.info Olmon evaporated-gold record, matching both
  the paper citation and the evaporation fabrication method.
- SiO2: inherited `matlab-radCoolPV` Palik/Kitamura table.
- Si: inherited refractive-index table with `k = 0`, because the paper explicitly
  models silicon as nonabsorbing in the infrared.

Current refractiveindex.info has the exact Olmon Au record but not the
paper-cited Palik/Kitamura Si or SiO2 records. Replacing them with different
records would not reproduce the paper. The unresolved source provenance is
documented in `radcoolpv/materials/SOURCES.md`.

### Digitized comparison data

The paper PDF was rendered at 180 dpi. Curves were traced on the published axes
and resampled at 0.05 µm or 1 K:

- `fig3a_calculated_emittance.txt`: calculated normal emittance, 2–16 µm;
- `fig5a_measured_emittance.txt`: measured hemispherical emittance, 2–16 µm;
- `fig5b_cooling_power.txt`: calculated cooling power, 260–380 K.

These are comparison data, not primary measurements. Figure-line thickness,
overlap, rasterization, and axis calibration limit their precision. The digitized
Figure 5a band averages are 0.841 for flat silica and 0.975 for the cylinders,
versus the reported 0.843 and 0.977. The digitized Figure 5b zero crossings are
359.5 K, 338.6 K, and 336.3 K, consistent with the reported 360 K, 339 K, 336 K.

### Optical result

Fresh 60-mode, normal, unpolarized S4 results:

| Stack | Paper 7.5–16 µm mean | S4 mean | 7.5–16 µm RMSE | 2–16 µm RMSE |
|---|---:|---:|---:|---:|
| Bare Au/Si | 0.036 | 0.032 | 0.030 | 0.030 |
| Flat silica | 0.843 | 0.842 | 0.029 | 0.174 |
| Silica cylinders | 0.976 | 0.984 | 0.025 | 0.174 |

The radiative-cooling-band result is supported. Full-range reproduction is not:
the finite stack diverges from the paper's semi-infinite-silica absorption
convention over roughly 2–5 µm. No fresh Fourier-mode convergence sweep was
performed, so the 60-mode patterned result is not a converged reference.

### Cooling power and convection coefficient

All cooling cases use the digitized *measured hemispherical emittance* from
Figure 5a, as the paper states for Figure 5b. They impose the paper's absorbed
solar power `808 W/m²`, ambient temperature `300 K`, and calculate

`P_cool = P_rad - P_atm + h_total(T - T_amb) - 808 W/m²`.

Here `h_total` is the total effective nonradiative coefficient for the area used
by the energy balance. The library does not silently multiply a per-surface
coefficient by the number of exposed surfaces.

The paper also reports `366.5 K` for a zero-emissivity surface. For that case the
published equation reduces exactly to `T_eq = 300 K + 808 W/m² / h_total`, so the
paper-stated `h_total = 6.0 W/m²/K` gives `434.67 K`; the reported `366.5 K`
requires `h_total = 12.15 W/m²/K`. This contradiction is independent of the
optical and atmospheric inputs.

With the paper-stated `h = 6.0 W/m²/K` the model gives:

| Stack | Paper equilibrium | Calculated equilibrium |
|---|---:|---:|
| Bare Au/Si | 360.0 K | 415.4 K |
| Flat silica | 339.0 K | 360.6 K |
| Silica cylinders | 336.0 K | 355.6 K |

The three `cooling_paper_h6_*` cases preserve this failed reproduction. After
fixing every other paper parameter, a single least-squares fit to all three
digitized cooling-power curves gives `h_total = 12.54 W/m²/K`. The three
`cooling_calibrated_*` cases use that fitted value:

| Stack | Paper equilibrium | YAML equilibrium | Curve RMSE |
|---|---:|---:|---:|
| Bare Au/Si | 360.0 K | 359.7 K | 22.8 W/m² |
| Flat silica | 339.0 K | 340.1 K | 39.0 W/m² |
| Silica cylinders | 336.0 K | 337.5 K | 42.7 W/m² |

This reproduces the temperatures and cooling-power curves, but it is a
calibration, not an independent validation of convection. The most plausible
explanations are an undocumented two-surface factor or a typo in the paper's
reported coefficient; the available article and supporting information do not
distinguish them.

---

## Archived

Validation D and superseded validation implementations are under the local,
gitignored `archive/`. Validation D lacks required layer thicknesses and material
models; inventing them would not be validation.
