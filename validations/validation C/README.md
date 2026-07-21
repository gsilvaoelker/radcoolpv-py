# Validation C — Zhao et al. (Renewable Energy 2022), silica micro-grating

End-to-end validation of **both** radcoolpv stages against

> B. Zhao, K. Lu, M. Hu, J. Liu, L. Wu, C. Xu, Q. Xuan, G. Pei,
> **"Radiative cooling of solar cells with micro-grating photonic cooler,"**
> *Renewable Energy* **191** (2022) 662–668.

This is the first validation to exercise radcoolpv's **1-D `grating` shape**: a
silica micro-grating etched into the top of a 500 µm fused-silica cooler.

```text
period p = 7 µm,  silica ridge width w = 1.4 µm  (duty r = w/p = 0.2),
etch depth d = 10 µm
```

## The physics

Bulk silica has a strong phonon–polariton resonance near 9 µm where its
permittivity goes negative (near-metallic), giving a high-reflectivity, **low-
emissivity dip** right inside the 8–13 µm atmospheric window. The micro-grating
acts as an effective-medium antireflection layer for thermal emission — it
overcomes the silica/air impedance mismatch and **fills the 9 µm dip**, raising
the window-averaged emissivity from ~0.77 (planar wafer) to ~0.9.

## What is validated

| Stage | Paper source | Quantity |
|---|---|---|
| Optics | Fig. 1c / 2d | Window-averaged (8–13 µm) emissivity, planar vs grating |
| Thermal | Fig. 3 | Equilibrium temperature of the 200 µm Si cell, bare vs grating |

## Result (computed here)

```
A. Cooler optics (Fig. 1c) — S4 window-averaged emissivity 8–13 µm
   cooler               paper      S4
   planar silica        (dip)     77%
   grating silica         90%     93%

B. Cell temperature (Fig. 3) — cooling_curve, 800 W/m², hc = 6, Ta = 300 K
   cell                    paper dT   calc dT
   bare 200 µm Si            77.5 C     93.9 C
   + grating cooler          37.5 C     37.8 C
```

**The grating raises the window emissivity to 0.93 (paper ~0.9) and the
grating-silica cell reaches 37.8 °C above ambient — matching the paper's 37.5 °C
to within 0.3 °C.** The grating (via the new `grating` shape) is a genuine RCWA
computation, well converged (emissivity flat to <0.003 over 10–120 Fourier
modes, since a 1-D grating only needs modes along the grating vector).

## How to run

From this directory, with the package installed (`../../install.sh`):

```bash
python run_validation.py            # rebuild the S4 optics, then validate
python run_validation.py --no-build # reuse the committed data/optics/*.txt
```

`pytest tests/test_validation_zhao_grating.py` checks the committed spectra.

## Documented caveats

* **Bare-cell temperature is model-sensitive.** The paper's Fig. 3 models a
  200 µm silicon slab. Silicon is nearly transparent in the mid-IR, so the bare
  slab's emissivity (`SiliconNew`, window average 5.6 %) — and hence its
  temperature — is set almost entirely by the silicon optical model, not by the
  cooler. It runs hotter here (93.9 °C vs 77.5 °C above ambient), consistent with
  a less mid-IR-absorbing (undoped) silicon than the paper's cell. The **grating**
  result is robust precisely because the strong silica emissivity (93 %)
  dominates and is independent of the silicon model — which is why it matches to
  <1 °C. The test asserts the grating temperature tightly and the bare only as a
  large relative cooling.
* **Fixed solar absorptivity.** A bare 200 µm Si slab without the cell's
  antireflection and texturing absorbs only ~0.5 of AM1.5 (vs the paper's cell
  ~0.95, Fig. 2d), which would understate the absorbed solar. `build_optics_s4.py`
  therefore fixes the solar band (λ ≤ 1.1 µm) to α = 0.95 for the cell stacks,
  isolating the grating's mid-IR emissivity effect — the paper's actual result —
  from that front-surface artefact. The cooler-alone spectra (Fig. 1c) are left
  untouched.
* **Back mirror.** Silver (`Hagemann_Ag`) replaces any real cell back contact;
  it only matters for the below-bandgap tail (T ≈ 0 in the mid-IR).
* **Atmosphere.** The paper uses MODTRAN; the bundled Cerro-Pachón transmittance
  is used here.
