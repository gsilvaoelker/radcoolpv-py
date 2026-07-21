# radcoolpv validations

This folder holds literature-reproduction checks for `radcoolpv`.

**Trusted (verified to run):** Validation A and Validation B.
**Not trusted:** everything else. Validations C and D are reference papers only
(no runnable configs yet). Validation E has been moved to
[`archive/validation E/`](archive/) and is **not** an active or trusted
validation — see the note at the end.

All commands below are run from the repository root
(`.../radcoolpv-py/`). They pin the working copy of the package on `PYTHONPATH`
because a stale editable install elsewhere on the machine otherwise shadows it
(see [`../docs/CODE_REVIEW.md`](../docs/CODE_REVIEW.md), finding 1). Both trusted
validations **resume from precomputed optical spectra** (`run.optics: false`), so
they never invoke the RCWA engine and are unaffected by the optics backend.

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
PYTHONPATH="$PWD" python "validations/validation A/run_table1_validation.py"
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
  PYTHONPATH="$PWD" radcoolpv run "validations/validation B/$f.yaml"
done
```

> Note: the un-pinned `radcoolpv run …` currently fails on Validation B with a
> `TypeError` because the machine's editable install points at a stale copy that
> predates `cooling_curve`. The `PYTHONPATH="$PWD"` prefix pins the working copy.

---

## Archived / untrusted

* **`archive/validation E/`** — a silica-microcylinder reproduction (Akerboom et
  al. 2022) built in an earlier session. Preserved in full but **not** a trusted
  or active validation; it is excluded from the list above by intent.
* **`validation C/`, `validation D/`** — reference papers only; no runnable
  configs.
