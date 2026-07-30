# Validation status

These cases have different evidentiary strength. “The script runs” is not the
same as “the physical model is independently validated.”

| Case | Optics source | What is checked | Status |
|---|---|---|---|
| A | Published reduced spectra | PV and thermal Table 1 quantities | Conditional regression |
| B Fig. 4d | Digitized measured spectra | Cooling balance | Conditional regression |
| B Fig. 5d | Digitized published curves | Plot comparison only | Not an independent validation |
| C | YAML-defined S4 grating cases | Normal unpolarized optics and cooling model | Partial validation |
| E | YAML-defined S4 Au/Si/silica cases | Normal unpolarized optics and thermal model | Optics agrees; thermal fails |

Source PDFs are not tracked. Each case identifies its DOI and limitations in its
local README.

## Validation A

Silva-Oelker and Jaramillo-Fernandez, *Optics Express* (2022), Table 1.

Five YAML files exercise the standard PV pipeline with pre-reduced optical
spectra. They do not exercise S4. The reduced inputs contain no angular TE/TM
data, so atmospheric absorption uses an angle-independent approximation.
Reflected-power discrepancies reach approximately `10%`.

```bash
PYTHONPATH=. python "validations/validation A/run_table1_validation.py"
```

## Validation B

Le et al., *ACS Photonics* (2026), Figures 4d and 5d.

Figure 4d uses digitized film spectra with `800 W m^-2` solar input and
`h_c = 9 W m^-2 K^-1`. Figure 5d contains only digitized comparison curves;
raw module optics are unavailable.

```bash
for f in fig4d_pdms fig4d_sds fig4d_ads fig5d_cooling_family; do
  radcoolpv run "validations/validation B/$f.yaml"
done
```

## Validation C

Zhao et al., “Radiative cooling of solar cells with micro-grating photonic
cooler,” *Renewable Energy* **191** (2022) 662–668,
https://doi.org/10.1016/j.renene.2022.04.063.

The four `optics_*.yaml` files define the planar, grating, bare-cell, and
grating-cell S4 cases. Normal-incidence TE and TM are both calculated and
averaged. The grating gives an `8–13 µm` emissivity of `0.938` versus the
paper's approximate `0.90`; the thermal adapter gives `337.82 K` versus
`337.5 K`.

Limitations:

- the paper-prescribed solar absorptance `0.95` is imposed in the validation
  adapter rather than derived from the idealized untextured Si stack;
- a normal-incidence spectrum is used as an angle-independent thermal
  approximation;
- the bare-cell temperature is sensitive to the selected Si optical model.

```bash
PYTHONPATH=. python "validations/validation C/run_validation.py"
```

## Validation E

Akerboom et al., “Passive Radiative Cooling of Silicon Solar Modules with
Photonic Silica Microcylinders,” *ACS Photonics* **9** (2022) 3831–3840,
https://doi.org/10.1021/acsphotonics.2c01389.

One YAML defines nine named cases: three live S4 normal-emittance cases, three
cooling-power cases using the paper-stated `h = 6.0 W/m²/K`, and three
calibrated cooling-power cases. All thermal cases use digitized measured
hemispherical emittance. The radiative-cooling-band S4 RMSE is 0.025–0.030.
Full 2–16 µm reproduction fails for the silica cases (RMSE about 0.174)
because the finite fabricated stack differs from the paper's
semi-infinite-silica absorption convention.

The paper-stated coefficient produces 415.4 K, 360.6 K, and 355.6 K, so it
does not reproduce Figure 5b. Its zero-emitter equation independently predicts
434.67 K instead of the reported 366.5 K. A joint curve fit gives
`h_total = 12.54 W/m²/K`; the calibrated YAML cases then predict 359.7 K,
340.1 K, and 337.5 K versus reported 360.0 K, 339.0 K, and 336.0 K. This is
a calibrated reproduction, not an independent convection validation. See the
case README for geometry, digitization, materials, and residual limitations.

```bash
radcoolpv run "validations/validation E/validation.yaml"
```

## Archived

Validation D and superseded validation implementations are under the local,
gitignored `archive/`. Validation D lacks required layer thicknesses and material
models; inventing them would not be validation.
