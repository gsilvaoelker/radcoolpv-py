# Validation E — Akerboom et al. (ACS Photonics 2022), silica microcylinders

End-to-end validation of **both** radcoolpv stages against one paper:

> E. Akerboom, T. Veeken, C. Hecker, J. van de Groep, A. Polman,
> **"Passive Radiative Cooling of Silicon Solar Modules with Photonic Silica
> Microcylinders,"** *ACS Photonics* **2022**, 9, 3831–3840.

Unlike the trusted resume-only validations (A and B), this one **runs the S4
RCWA optics engine**: the flat and microcylinder module-glass emissivities are
computed from first principles, then fed to the `cooling_curve` energy balance.

## What is validated

| Group | Paper source | Quantity | Stage |
|---|---|---|---|
| Theoretical bounds | Fig. 2d | Equilibrium T of idealized absorbers | thermal |
| Module optics | Fig. 5a | Band-averaged emissivity 7.5–16 µm, **computed by S4** | optics |
| Module thermal | Fig. 5b | Equilibrium T of the three real stacks | optics + thermal |

## The structure

```text
vacuum / SiO2 200 µm module glass / Si 500 µm / Ag mirror
```

The microcylinder case adds a hexagonal array of silica cylinders (radius
1.75 µm, height 2.25 µm, pitch 6.125 µm) etched into the top of the glass — the
paper's optimized geometry. radcoolpv maps a hexagonal array of pitch `p` onto a
rectangular `√3·p × p` cell with two cylinders, reproducing the true hexagonal
fill fraction `2πr²/(√3 p²) = 29.6 %` exactly.

## Result (computed here)

```
A. Theoretical bounds (Fig. 2d) — idealized emissivity [thermal engine]
   case                                 paper     calc   err K
   zero IR emissivity (upper bound)     366.5    367.5     1.0
   8-14 um window only                  341.5    345.1     3.6
   ideal 3-30 um absorber (min)         330.5    335.5     5.0

B. Real module stacks (Fig. 5) — S4 optics + cooling-curve thermal
   stack                         emis% paper/calc   T_eq K paper/calc/err
   Au-Si (bare reference)              -- /  16.2       360 / 360.6 /  0.6
   Au-Si-SiO2 (flat glass)           84.3 /  84.0       339 / 338.9 / -0.1
   Au-Si-SiO2-cylinders              97.7 /  98.3       336 / 336.0 /  0.0
```

**The S4-computed band-averaged emissivity matches the paper to 0.3 pp (flat)
and 0.6 pp (cylinders), and every equilibrium temperature to ≤0.6 K.** The
microcylinder emissivity is now a genuine RCWA result, not — as in the earlier
archived version — the flat spectrum scaled to the paper's reported 97.7 %.

## How to run

From this directory, with the package installed (`../../install.sh`, or
`pip install -e ../..`):

```bash
python run_validation.py            # rebuild the S4 optics, then validate
python run_validation.py --no-build # reuse the committed data/optics/s4_*.txt
```

`build_optics_s4.py` runs the S4 sweep and writes the three reduced spectra; the
`stack_*.yaml` configs resume from them (`run.optics: false`) so the thermal
comparison is fast and reproducible. `pytest tests/test_validation_akerboom.py`
checks the committed spectra without rebuilding.

## Documented caveats

* **RCWA mode truncation.** RCWA expands a circular, high-index-contrast, lossy
  scatterer in a Fourier basis, which converges slowly and *non-monotonically*
  for this structure — the band-averaged cylinder emissivity sits near 98 % but
  scatters ~0.5 % across 40–100 modes (`build_optics_s4.CYL_MODES = 60`). This
  truncation uncertainty is exactly why the paper used FDTD; it is far smaller
  than the flat→cylinder emissivity jump under test, and the equilibrium
  temperature is insensitive to it (the cylinder T_eq lands on 336.0 K). The
  ~0.6 pp gap to the paper's 97.7 % is consistent with an RCWA-vs-FDTD method
  difference on a Mie resonance.
* **Back mirror.** The paper uses an 80 nm gold film; only silver optical
  constants (`Hagemann_Ag`) are bundled here. Both are near-perfect IR mirrors
  (T ≈ 0), so this affects only the small parasitic-absorption tail of the bare
  Au-Si reference, not the silica-bearing stacks.
* **Normal incidence.** The paper reports normal-incidence emissivity (Fig. 5a)
  and folds the angular dependence into an effective convection coefficient
  (`hc = 12` W/m²K here; Methods states 6). The optics files therefore carry the
  normal-incidence S4 emissivity, matching the 84.3 % / 97.7 % being compared.
* **Fixed solar input.** The paper fixes absorbed solar power at ≈808 W/m²
  (AM1.5G above the Si bandgap), independent of the IR design. The optical files
  enforce this with `emit = 1` for λ ≤ 1.107 µm and `emit = 0` in the below-gap
  solar tail; the IR band carries the S4 result.
