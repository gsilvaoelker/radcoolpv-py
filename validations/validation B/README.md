# Validation B: Le et al. 2026

Standalone YAML validation for the main cooling-power figures in
"Enhancing Passive Radiative Cooling Performance on Solar Panels via Multiple
Scattering Effects in Aggregated Silica Particles/Polydimethylsiloxane Films."

Run from the repository root:

```bash
radcoolpv run 'validations/validation B/fig4d_pdms.yaml'
radcoolpv run 'validations/validation B/fig4d_sds.yaml'
radcoolpv run 'validations/validation B/fig4d_ads.yaml'
radcoolpv run 'validations/validation B/fig5d_cooling_family.yaml'
```

Figure 4d is calculated by `cooling_curve` mode from the bundled digitized
optical spectra, 800.0 W/m2 solar irradiance, and hc = 9.0 W/m2-K. The digitized
Figure 4d curves are plotted only as reference.

Figure 5d is a digitized curve comparison. The paper does not provide the raw
commercial-module stack optics needed for an independent calculation of this
panel-level heat-transfer-coefficient family.

All inputs required by these YAML files are under `data/`; generated outputs
are written under `results/` and are intentionally not part of the validation.
