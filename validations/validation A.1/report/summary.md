# Validation A.1 Report

Validation A.1 uses the soda-lime hemisphere geometry reported in the Optics Express paper and compares the rebuilt normal-incidence S4 optics against the published Fig. 3(b) blue normal-incidence columns. The thermal/PV stage uses the published hemispherical Fig. 3(b) blue spectrum to reproduce the Table 1 soda-lime row.

## Optical Band Averages

| Band | Published | Computed | Diff | Rel. error |
| --- | ---: | ---: | ---: | ---: |
| Emittance 8-13 um | 0.9716 | 0.9729 | +0.0013 | +0.13% |
| Emittance 17-24 um | 0.9625 | 0.9537 | -0.0088 | -0.91% |
| Emittance 4-30 um | 0.9352 | 0.9290 | -0.0062 | -0.66% |
| Si absorptance 0.3-1.12 um | 0.8069 | 0.8067 | -0.0002 | -0.03% |
| Reflectance 0.3-1.12 um | 0.1728 | 0.1732 | +0.0003 | +0.19% |
| Reflectance 1.12-4 um | 0.9220 | 0.9352 | +0.0132 | +1.43% |

## Thermal/PV Table 1 Comparison

| Quantity | Published | Computed | Diff | Rel. error |
| --- | ---: | ---: | ---: | ---: |
| equilibrium_temperature_K | 319 | 317.779 | -1.22095 | -0.38% |
| short_circuit_current_A_per_m2 | 355 | 354.975 | -0.0249822 | -0.01% |
| mpp_equilibrium_W_per_m2 | 222 | 222.91 | +0.910291 | +0.41% |
| subgap_reflected_power_W_per_m2 | 170 | 174.93 | +4.92979 | +2.90% |
| radiated_power_W_per_m2 | 472 | 464.398 | -7.60168 | -1.61% |
| voc_equilibrium_V | 0.722 | 0.724573 | +0.00257278 | +0.36% |

## Figures

- `figures/spectral_comparison.png`
- `figures/band_errors.png`
- `figures/pv_curves.png`
