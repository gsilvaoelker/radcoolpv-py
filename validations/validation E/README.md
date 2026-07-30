# Validation E — Akerboom et al. (2022)

Reference: E. Akerboom et al., “Passive Radiative Cooling of Silicon Solar
Modules with Photonic Silica Microcylinders,” *ACS Photonics* **9**,
3831–3840 (2022), https://doi.org/10.1021/acsphotonics.2c01389.

## Run

One YAML file defines three optical cases, three cooling-power cases using the
paper-stated convection coefficient, and three calibrated cooling-power cases:

```bash
radcoolpv run "validations/validation E/validation.yaml"
```

Students change only `validation.yaml`. It directly references the digitized
paper data in `data/digitized/`.

## Paper geometry and boundary conditions

| Quantity | Calculated design | Fabricated sample |
|---|---:|---:|
| Silica cylinder radius | 1.75 µm | 1.825 µm mean |
| Silica cylinder height | 2.25 µm | 2.20 µm mean |
| Hexagonal pitch | 6.125 µm | 6.125 µm target |
| Silica wafer thickness | semi-infinite in Figure 3 calculation | 500 µm |
| Silicon thickness | not part of the Figure 3 silica-interface model | 500 µm |
| Gold thickness | — | 80 nm |

The fabricated silicon is lightly phosphorus-doped n-type double-side-polished
Si. The paper's calculated Figure 3 model places periodic silica cylinders at
an air/semi-infinite-silica interface and assumes all IR power transmitted into
silica is eventually absorbed. The active YAML instead uses the complete
fabricated 500 µm SiO2 / 500 µm Si / 80 nm Au stack so that S4 reports
`R`, `T`, and `A` for one explicit structure. These are not identical optical
boundary conditions.

The hexagonal lattice is represented by the rectangular primitive cell used by
the inherited S4 geometry: `x = sqrt(3) * 6.125 = 10.608811 µm`,
`y = 6.125 µm`.

## Materials

- Au: unmodified refractiveindex.info Olmon evaporated-gold record, matching
  both the paper citation and the evaporation fabrication method.
- SiO2: inherited `matlab-radCoolPV` Palik/Kitamura table.
- Si: inherited refractive-index table with `k = 0`, because the paper explicitly
  models silicon as nonabsorbing in the infrared.

Current refractiveindex.info has the exact Olmon Au record but not the
paper-cited Palik/Kitamura Si or SiO2 records. Replacing them with different
records would not reproduce the paper. The unresolved source provenance is
documented in `radcoolpv/materials/SOURCES.md`.

## Digitized comparison data

The repository paper PDF was rendered at 180 dpi. Curves were traced on the
published axes and resampled at 0.05 µm or 1 K:

- `fig3a_calculated_emittance.txt`: calculated normal emittance, 2–16 µm;
- `fig5a_measured_emittance.txt`: measured hemispherical emittance, 2–16 µm;
- `fig5b_cooling_power.txt`: calculated cooling power, 260–380 K.

These are comparison data, not primary measurements. Figure-line thickness,
overlap, rasterization, and axis calibration limit their precision. The
digitized Figure 5a band averages are 0.841 for flat silica and 0.975 for the
cylinders, versus the reported 0.843 and 0.977. The digitized Figure 5b zero
crossings are 359.5 K, 338.6 K, and 336.3 K, consistent with the reported
360 K, 339 K, and 336 K.

## Optical result

Fresh 60-mode, normal, unpolarized S4 results are:

| Stack | Paper 7.5–16 µm mean | S4 mean | 7.5–16 µm RMSE | 2–16 µm RMSE |
|---|---:|---:|---:|---:|
| Bare Au/Si | 0.036 | 0.032 | 0.030 | 0.030 |
| Flat silica | 0.843 | 0.842 | 0.029 | 0.174 |
| Silica cylinders | 0.976 | 0.984 | 0.025 | 0.174 |

The radiative-cooling-band result is supported. Full-range reproduction is not:
the finite stack diverges from the paper's semi-infinite-silica absorption
convention over roughly 2–5 µm. No fresh Fourier-mode convergence sweep was
performed, so the 60-mode patterned result is not a converged reference.

## Cooling power and convection coefficient

All cooling cases use the digitized *measured hemispherical emittance* from
Figure 5a, as the paper states for Figure 5b. They impose the paper's absorbed
solar power `808 W/m²`, ambient temperature `300 K`, and calculate

`P_cool = P_rad - P_atm + h_total(T - T_amb) - 808 W/m²`.

Here `h_total` is the total effective nonradiative coefficient for the area
used by the energy balance. The library does not silently multiply a
per-surface coefficient by the number of exposed surfaces.

The paper also reports `366.5 K` for a zero-emissivity surface. For that case,
the published equation reduces exactly to
`T_eq = 300 K + 808 W/m² / h_total`. The paper-stated
`h_total = 6.0 W/m²/K` therefore gives `434.67 K`; the reported `366.5 K`
requires `h_total = 12.15 W/m²/K`. This contradiction is independent of the
optical and atmospheric inputs.

With the paper-stated `h = 6.0 W/m²/K`, the model gives:

| Stack | Paper equilibrium | Calculated equilibrium |
|---|---:|---:|
| Bare Au/Si | 360.0 K | 415.4 K |
| Flat silica | 339.0 K | 360.6 K |
| Silica cylinders | 336.0 K | 355.6 K |

The three `cooling_paper_h6_*` YAML cases preserve this failed reproduction.
After fixing every other paper parameter, a single least-squares fit to all
three digitized cooling-power curves gives
`h_total = 12.54 W/m²/K`. The three `cooling_calibrated_*` cases use that
fitted value:

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
