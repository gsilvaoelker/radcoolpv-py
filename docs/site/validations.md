# Validation evidence

The repository contains six comparison groups. They do not have equal
evidentiary strength. A successful run proves that a workflow executes; it
does not prove solver convergence, correctness of every physical term, or
agreement with a publication.

```{admonition} Use the status labels
:class: warning
Validation A is a stored-spectrum regression, A.1 and A.2 test the optical
backend at normal incidence for the stated hemisphere geometries, B contains
digitized-data comparisons, C is partial, and E exposes a thermal-model
contradiction. Do not describe them all as fully validated.
```

## Status at a glance

| Case | Main input | Strongest defensible claim |
|---|---|---|
| A | Published reduced spectra | Conditional regression of Table 1 PV and thermal outputs |
| A.1 | Live S4 from the paper's stated soda-lime geometry plus published reduced spectrum | Fig. 3(b) normal-incidence optics and Table 1 thermal/PV row |
| A.2 | Live S4 from the paper's stated PDMS geometry | Optical backend reproduces the published spectrum at normal incidence |
| B | Digitized measured spectra and curves | Conditional cooling regression; one plot-only reproduction |
| C | Committed or live S4 grating spectra | Partial validation of grating emittance and temperature |
| E | Digitized measurements and optional live S4 | Cooling-band optics agree; paper-parameter thermal result fails |

(validation-a)=
## Validation A — Table 1 PV and thermal regression

[Run Validation A in Google Colab](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_a_colab.ipynb)

The five cases use the reduced spectra supplied with the original work. They
exercise the PV and thermal pipeline but do not run S4. Because the source
files contain no direction-resolved TE/TM data, the atmospheric contribution
uses the documented angle-independent approximation.

### Main results

| Observable | Comparison with published Table 1 |
|---|---|
| Short-circuit current density, $J_{sc}$ | Within 3% for all structures |
| Maximum power, $P_{mpp}$ | Within 3% for all structures |
| Equilibrium temperature | Within 3 K |
| Open-circuit voltage, $V_{oc}$ | Within 0.02 V |
| Reflected power | Weakest quantity; discrepancies reach about 10% |

```{figure} _static/validations/validation_a_table1_errors_preview.png
:alt: Maximum error by output quantity for Validation A
:width: 760px

Validation A error envelope across the five Table 1 structures. Reflected
power is visibly the weakest matched quantity.
```

Run from a checkout:

```bash
PYTHONPATH=. python "validations/validation A/run_table1_validation.py"
```

**Status:** conditional regression. It supports the stored-spectrum thermal/PV
implementation under the stated angular approximation; it does not validate
the live S4 backend.

**Reference:** G. Silva-Oelker and J. Jaramillo-Fernandez, “Numerical study of
sodalime and PDMS hemisphere photonic structures for radiative cooling of
silicon solar cells,” *Optics Express* 30, 32965–32977 (2022),
[doi:10.1364/OE.466335](https://doi.org/10.1364/OE.466335).

(validation-a1)=
## Validation A.1 — soda-lime hemisphere workflow

[Run Validation A.1 in Google Colab](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_a1_colab.ipynb)

A.1 validates the soda-lime hemisphere row from Fig. 3(b) blue / Table 1. The
paper states 9 µm-diameter soda-lime hemispheres on a 75 µm soda-lime layer in
a `(17.3, 10)` µm periodic cell. The live optics check computes that geometry
at normal incidence and compares against the normal-incidence columns in the
published spectrum. The fast thermal/PV step reads the published reduced
hemispherical spectrum and compares against Table 1.

### Main results from the Table 1 spectrum

| Quantity | Result |
|---|---:|
| Maximum $|R+T+A-1|$ | 0 |
| Solar-band silicon absorptance | 0.801 |
| Mean 8–13 µm emittance | 0.881 |
| Equilibrium temperature | 317.78 K |
| $I_{sc}$ | 354.98 A/m² |
| Equilibrium $V_{oc}$ | 0.7246 V |
| Equilibrium maximum power | 222.91 W/m² |
| Fill factor | 0.8667 |
| Efficiency | 0.2237 |

### Live normal-incidence optical comparison

`s4_modes: 30`, twelve dome slices, unpolarized, normal incidence, 2000
wavelengths, 419 s on a local workstation.

| Band average | Published | Computed | Rel. err |
|---|---:|---:|---:|
| Emittance 8–13 µm | 0.9716 | 0.9729 | +0.13% |
| Emittance 17–24 µm | 0.9625 | 0.9537 | −0.91% |
| Emittance 4–30 µm | 0.9352 | 0.9290 | −0.66% |
| Si absorptance 0.3–1.12 µm | 0.8069 | 0.8067 | −0.03% |
| Reflectance 0.3–1.12 µm | 0.1728 | 0.1732 | +0.19% |
| Reflectance 1.12–4 µm | 0.9220 | 0.9352 | +1.43% |

```{figure} _static/validations/validation_a1_spectral_comparison.png
:alt: Validation A.1 published versus live S4 optical spectra
:width: 760px

Published normal-incidence optical columns compared with the live S4 spectrum
for emittance, reflectance, and silicon absorptance.
```

```{figure} _static/validations/validation_a1_band_errors.png
:alt: Validation A.1 relative errors in optical band averages
:width: 760px

Relative error in the six optical band averages. The largest band-level
difference is the 1.12–4 µm sub-gap reflectance row.
```

```{figure} _static/validations/validation_a1_pv_curves.png
:alt: Validation A.1 current-voltage and power-voltage curves
:width: 760px

The published hemispherical spectrum gives $J_{sc}=354.98$ A/m²,
$V_{oc}=0.7246$ V, and a maximum-power point of 222.91 W/m² at 0.6577 V.
```

Run from a checkout:

```bash
# Optional: rebuild normal-incidence S4 optics and compare with Fig. 3(b).
PYTHONPATH=. python "validations/validation A.1/run_sodalime_optics_validation.py"

# Fast path used by default in Colab.
radcoolpv run "validations/validation A.1/pv_hemisph_sodalime.yaml"

# Write the report summary and plots shown above.
PYTHONPATH=. python "validations/validation A.1/report_validation.py"
```

**Status:** literature validation with a documented angular limitation. The
live optical comparison is normal-incidence only. The thermal/PV comparison
uses the paper's reduced hemispherical spectrum, which lacks per-angle
emissivity, so the atmospheric term uses Validation A's angle-independent
fallback.

**Reference geometry context:** G. Silva-Oelker and J.
Jaramillo-Fernandez (2022),
[doi:10.1364/OE.466335](https://doi.org/10.1364/OE.466335).

(validation-a2)=
## Validation A.2 — live S4 optics against the published PDMS spectrum

Same paper as Validation A, Fig. 3(c) blue. This is the case that tests the
optical backend. Validation A *reads* the published spectra and exercises only
the thermal and PV stages; A.2 *computes* the spectrum from the YAML geometry
and compares it against the published one.

It uses the PDMS row from Fig. 3(c) blue. Since $\sqrt{3}\times10=17.32$, the
paper's `(17.3, 10)` µm cell is represented as the centred-rectangular
supercell of a hexagonal lattice of pitch 10 µm.

### Main results

Live S4, `s4_modes: 30`, twelve dome slices, unpolarized, normal incidence,
2000 wavelengths, about 2.5 minutes; compared against the published
normal-incidence columns.

| Band average | Published | Computed | Rel. err |
|---|---:|---:|---:|
| Emittance 8–13 µm | 0.9868 | 0.9864 | −0.04% |
| Emittance 17–24 µm | 0.8963 | 0.8962 | −0.01% |
| Emittance 4–30 µm | 0.9209 | 0.9195 | −0.15% |
| Silicon absorptance 0.3–1.12 µm | 0.8092 | 0.8057 | −0.43% |
| Reflectance 0.3–1.12 µm | 0.1753 | 0.1789 | +2.02% |
| Reflectance 1.12–4 µm | 0.8393 | 0.8444 | +0.61% |

Maximum $|R+T+A-1|$ is $2.2\times10^{-16}$.

The three emittance rows are converged and agree to better than 0.2%. The
solar-band rows are **not** converged in `s4_modes`: silicon absorptance moves
non-monotonically across modes 30, 45 and 60 (0.8057, 0.8048, 0.8089), because
at $\lambda=0.3$ µm the 10 µm pitch is more than thirty wavelengths wide. Their
−0.43% and +2.02% differences therefore lie inside the numerical scatter and
are not evidence of a physical disagreement. The full convergence table is in
[`validations/README.md`](https://github.com/gsilvaoelker/radcoolpv-py/blob/main/validations/README.md).

Run from a checkout:

```bash
PYTHONPATH=. python "validations/validation A.2/run_pdms_optics_validation.py"
```

The script reports differences and always exits 0. It never asserts a
tolerance, so a reader sees the numbers rather than a pass or fail they cannot
interpret.

**Status:** validation of the optical backend at normal incidence. It does not
touch the hemispherical average the thermal model consumes, so it establishes
nothing about Table 1 temperatures or PV quantities — that comparison costs 194
S4 solves per wavelength instead of one, and has not been run. The paper states
neither its mode count nor its dome discretisation, so those are established by
the convergence table in
[`validations/README.md`](https://github.com/gsilvaoelker/radcoolpv-py/blob/main/validations/README.md)
rather than reproduced.

**Reference:** G. Silva-Oelker and J. Jaramillo-Fernandez, *Optics Express*
30, 32965–32977 (2022),
[doi:10.1364/OE.466335](https://doi.org/10.1364/OE.466335).

(validation-b)=
## Validation B — PDMS-based radiative-cooling layers

[Run Validation B in Google Colab](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_b_colab.ipynb)

The Figure 4d cases calculate cooling-power curves from digitized optical
spectra for three films. The Figure 5d case is different: it redraws digitized
published curves because the raw commercial-module optical stack is not
available.

### Main results

| Figure 4d film | Calculated zero-cooling-power temperature |
|---|---:|
| PDMS | 329.92 K |
| SDS/PDMS | 328.28 K |
| ADS/PDMS | 325.44 K |

```{figure} _static/validations/validation_b_fig4d_preview.png
:alt: Cooling power curves for the three Validation B films
:width: 760px

Calculated cooling-power curves from digitized film spectra. The zero
crossing is the predicted equilibrium temperature.
```

```{figure} _static/validations/validation_b_fig5d_preview.png
:alt: Digitized Figure 5d cooling power family
:width: 760px

Figure 5d is a digitized-curve reproduction, not an independently calculated
commercial-module result.
```

Run from a checkout:

```bash
for case in fig4d_pdms fig4d_sds fig4d_ads fig5d_cooling_family; do
  radcoolpv run "validations/validation B/${case}.yaml"
done
```

**Status:** Figure 4d is a conditional regression. The calculation assumes an
unconfirmed ambient temperature of 298.0 K and uses the bundled Cerro Pachón
atmosphere instead of Hiroshima conditions. Figure 5d is plot reproduction
only.

**Reference:** T. H. Le et al., *ACS Photonics* 13, 1108–1121 (2026),
[doi:10.1021/acsphotonics.5c02627](https://doi.org/10.1021/acsphotonics.5c02627).

(validation-c)=
## Validation C — silica micro-grating cooler

[Run Validation C in Google Colab](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_c_colab.ipynb)

This case compares planar silica with a one-dimensional silica grating and
then applies the spectra to bare and grating-equipped silicon cells. Colab
uses committed spectra by default; students may explicitly enable the live S4
rebuild.

### Main results

| Quantity | Paper | radcoolpv |
|---|---:|---:|
| Grating mean emittance, 8–13 µm | approximately 0.90 | 0.938 |
| Grating-equipped cell temperature rise | 37.5 °C | 37.8 °C |
| Bare-cell temperature rise | 77.5 °C | 93.9 °C |

```{figure} _static/validations/validation_c_emittance_preview.png
:alt: Planar and grating silica emittance in the atmospheric window
:width: 760px

The grating fills the planar silica dip near 9 µm and raises the unweighted
8–13 µm mean emittance from 0.767 to 0.938.
```

Run from a checkout:

```bash
cd "validations/validation C"
python run_validation.py --no-build  # committed spectra
python run_validation.py             # live S4 rebuild
```

**Status:** partial validation. The grating result agrees closely, but the bare
cell does not. Solar absorptance is fixed at 0.95, normal optics are treated as
angle-independent, and the bare-silicon result is material-model sensitive.

**Reference:** B. Zhao et al., “Radiative cooling of solar cells with
micro-grating photonic cooler,” *Renewable Energy* 191, 662–668 (2022),
[doi:10.1016/j.renene.2022.04.063](https://doi.org/10.1016/j.renene.2022.04.063).

(validation-e)=
## Validation E — Akerboom silica emitters

[Run Validation E in Google Colab](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/validation_e_colab.ipynb)

One YAML defines three optional live-optics cases, three thermal cases using
the paper-stated nonradiative coefficient, and three cases using one fitted
effective coefficient. The fitted cases are retained to localize the
disagreement, not to erase it.

### Optical results

| Emitter | Paper mean, 7.5–16 µm | S4 mean | RMSE, 7.5–16 µm |
|---|---:|---:|---:|
| Bare silicon | 0.036 | 0.032 | 0.030 |
| Flat silica | 0.843 | 0.842 | 0.029 |
| Silica cylinders | 0.976 | 0.984 | 0.025 |

The cooling-band averages agree closely. Across the broader 2–16 µm range,
the flat-silica RMSE rises to 0.174. No fresh S4 mode-convergence result is
claimed here.

### Thermal results

| Emitter | Paper | $h=6.0$ W/m²/K | Fitted $h=12.54$ W/m²/K |
|---|---:|---:|---:|
| Bare silicon | 360.0 K | 415.4 K | 359.7 K |
| Flat silica | 339.0 K | 360.6 K | 340.1 K |
| Silica cylinders | 336.0 K | 355.6 K | 337.5 K |

```{figure} _static/validations/validation_e_temperatures_preview.png
:alt: Paper and calculated Validation E temperatures
:width: 760px

The paper-stated coefficient fails. The fitted coefficient reproduces the
temperatures because it was calibrated to them.
```

Run all nine cases from a checkout:

```bash
radcoolpv run "validations/validation E/validation.yaml"
```

The default Colab notebook runs only the six fast thermal cases; live S4
optics is an explicit option.

**Status:** the cooling-band optical comparison is good, subject to the stated
convergence limit. The thermal model does not reproduce the paper using
$h=6.0$ W/m²/K. A zero-emitter check gives 434.67 K from the stated balance,
whereas the paper reports 366.5 K. The $h=12.54$ W/m²/K match is calibration,
not independent validation.

**Reference:** S. Akerboom et al., “Passive radiative cooling of silicon solar
modules with photonic silica microcylinders,” *ACS Photonics* 9, 3831–3840
(2022), [doi:10.1021/acsphotonics.2c01389](https://doi.org/10.1021/acsphotonics.2c01389).

## What students should retain

For every calculation, preserve `run.json` and report:

1. the YAML inputs and solver or data provenance;
2. numerical checks, including energy closure and convergence of a named
   observable when live S4 is used;
3. the exact reference and every approximation that limits the claim.

The complete case definitions and diagnostic notes are in the repository's
[validation README](https://github.com/gsilvaoelker/radcoolpv-py/blob/main/validations/README.md).
