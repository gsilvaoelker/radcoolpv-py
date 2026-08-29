# Validation evidence

There is one literature case, reproduced in three groups: the optics, the
cooling balance, and the full cell. The optics agree closely. The cooling
balance is sensitive to a coefficient the paper reports but that this model
cannot check independently, so that group is presented with both values rather
than only the one that matches.

**Akerboom, Doeleman, Scherer, Zeman, Smith, Isabella and Garnett, "Passive
Radiative Cooling of Silicon Solar Modules with Photonic Silica
Microcylinders", *ACS Photonics* 9 (2022) 3831–3840.**
[doi:10.1021/acsphotonics.2c01389](https://doi.org/10.1021/acsphotonics.2c01389)

## The structure

A hexagonal array of silica microcylinders — radius 1.75 µm, height 2.25 µm,
pitch 6.125 µm — on 500 µm of silica over 500 µm of silicon over 80 nm of gold.
Two references accompany it: the bare Au/Si module, and the same module under an
unpatterned silica slab. The gold blocks transmission, so emissivity is
1 − *R*.

`validation/akerboom.yaml` defines twelve cases in three groups.

```bash
radcoolpv run validation/akerboom.yaml
radcoolpv run validation/akerboom.yaml --case B3_cooling_h6_cylinders
```

Group B needs no solver and runs in seconds. Groups A and C call S4 and are
expensive — roughly four minutes and two hours respectively at the converged
settings in the file. A case that cannot run does not abort the others.

## Group A — optics

Normal-incidence emittance, 2–16 µm in steps of 0.05 µm, 60 Fourier modes,
compared against Figure 3a. Silicon is modeled as nonabsorbing, which is the
paper's own stated assumption for the cooling band.

| Surface | radcoolpv | Digitized Fig. 3a | Paper text |
|---|---:|---:|---:|
| Bare Au/Si | 0.032 | 0.036 | ~3.5% |
| Flat silica | 0.842 | 0.843 | — |
| Silica cylinders | 0.984 | 0.977 | — |

Mean over 7.5–16 µm. The optics agree.

## Group B — cooling curve

This group runs the **thermal model alone**, driven by the *measured* emittance
digitized from Figure 5a. No geometry, no materials, no solver. That isolation
is deliberate: what this group tests is the energy balance, with the optics
held fixed at measured values.

Run with the convection coefficient the paper's Methods state,
*h* = 6.0 W/m²/K:

| Surface | radcoolpv | Paper Fig. 5b |
|---|---:|---:|
| Bare Au/Si | 415.4 K | 360 K |
| Flat silica | 360.6 K | 339 K |
| Silica cylinders | 355.6 K | 336 K |

A single least-squares fit to all three digitized curves gives *h* = 12.54
W/m²/K, which reproduces 359.7 / 340.1 / 337.5 K — all three at once.

```{admonition} The fitted agreement is a calibration
:class: warning
Fitting one coefficient to the curves you are trying to reproduce cannot
validate the model that produced them. Cases `B4`–`B6` exist so the fit is
labeled rather than folded silently into the default.
```

Why the equilibrium moves so much: *h* is a single lumped coefficient standing
for all non-radiative exchange, and its value depends on mounting, wind speed,
and how many surfaces are counted as exchanging heat. The balance is
correspondingly sensitive to it. A useful limiting case, which needs no optics
at all, is a surface that does not radiate: it must settle at

$$T = T_\mathrm{amb} + \frac{P_\mathrm{sun}}{h},$$

which is 434.67 K at *h* = 6 and 364.4 K at *h* = 12.54. Every real emitter
lands below the line for its own *h*, so that expression brackets the whole
family and is worth evaluating before reading any equilibrium temperature.
`tests/test_validation_akerboom.py` pins both sets of numbers.

## Group C — full optical, thermal and electrical result

0.3–24.9 µm hemispherical, with the lossy silicon table. The upper limit is set
by gold: `RII_Olmon_2012_ev_Au` is tabulated to 24.93 µm and the loader refuses
to extrapolate.

This group needs the **lossy** `Palik_Si`, not the `Akerboom_Si_lossless` used
by groups A and B. Lossless silicon absorbs no sunlight, so the photocurrent
integrates to zero and the cell reports a few millivolts — a failure mode that
looks like a solver bug and is a materials choice.

| Surface | *T*<sub>eq</sub> | Efficiency | MPP | *β*<sub>P</sub> |
|---|---:|---:|---:|---:|
| Bare Au/Si | 350.5 K | 14.17% | 142.6 W/m² | −0.303 %/K |
| Flat silica | 329.3 K | 18.09% | 182.1 W/m² | −0.299 %/K |
| Silica cylinders | 327.0 K | 18.64% | 187.7 W/m² | −0.300 %/K |

The temperature drops agree with the paper: 21.2 K bare → flat silica against
21 K, 2.3 K flat → cylinders against 3 K, 23.5 K bare → cylinders against 24 K.

Note what the efficiency column does *not* say. Absorbed sunlight rises from
507.5 to 598.6 to 614.3 W/m² across the three surfaces, so most of the gain is
the silica acting as an antireflection layer, not as a radiative cooler. Of the
efficiency gained from flat silica to cylinders, only a small part is thermal.

## What to retain

* The optics are validated against the published spectra.
* The thermal model is **not** independently validated by this case, because
  the coefficient that dominates the result was fitted rather than measured.
* A model that only matches after one coefficient is fitted has been calibrated,
  not confirmed — and saying so is part of the result.
* Before reading an equilibrium temperature, evaluate the limiting case. Here
  it costs one line of arithmetic and bounds every possible answer.
