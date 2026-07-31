# Validation evidence

The repository includes several comparison cases, but they do not have equal
evidentiary strength. A successful run establishes software execution. It does
not by itself establish numerical convergence or physical validity.

```{admonition} Read the status before quoting a result
:class: warning
Validation A.1 is a configuration smoke test, Validation B includes digitized
curves, Validation C is partial, and Validation E exposes a thermal-model
contradiction. Do not relabel any of them as a full validation.
```

## Status at a glance

| Case | Input or solver | What it checks | Defensible status |
|---|---|---|---|
| A | Published reduced spectra | PV and thermal Table 1 quantities | Conditional regression; no live S4 and reflected-power discrepancies reach about 10% |
| A.1 | Live S4 followed by a stored spectrum | Hexagonal-cell execution and the complete PV pipeline | **Not a validation**; assumed pitch and normal-incidence TE approximation |
| B, Fig. 4d | Digitized measured spectra | Cooling balance | Conditional regression |
| B, Fig. 5d | Digitized published curves | Plot reproduction | Not an independent validation |
| C | YAML-defined S4 grating | Normal unpolarized optics and cooling | Partial validation |
| E | YAML-defined S4 Au/Si/silica stacks | Normal unpolarized optics and thermal balance | Cooling-band optics agree; paper-parameter thermal result fails |

## Cases and principal results

### A and A.1: PV workflow

Validation A compares the PV and thermal pipeline with published reduced
spectra. Because those files contain no angular TE/TM information, the
atmospheric calculation uses an angle-independent approximation. It also does
not exercise S4.

```bash
PYTHONPATH=. python "validations/validation A/run_table1_validation.py"
```

A.1 adds a live hexagonal-cell S4 smoke test and then drives the PV model from
the exported spectrum:

```bash
radcoolpv run "validations/validation A.1/optics_hemisph_sodalime.yaml"
radcoolpv run "validations/validation A.1/pv_hemisph_sodalime.yaml"
```

The committed A.1 spectrum gives an equilibrium temperature of 317.09 K,
$I_{sc}=365.92$ A/m$^2$, equilibrium $V_{oc}=0.7264$ V, equilibrium maximum
power of 230.61 W/m$^2$, fill factor 0.868, and equilibrium efficiency 23.14%.
These are useful tutorial reference values, not a reproduction of the paper:
the pitch is assumed close-packed, the live solve uses only 10 S4 modes, and
the thermal step treats a normal-incidence TE spectrum as angle-independent.

The Colab notebook executes this stored-spectrum PV step because it is fast and
produces the main result tables and figures without a second expensive S4 run.

### B: cooling curves from digitized data

The Figure 4d cases calculate cooling curves from digitized optical spectra.
The Figure 5d case only compares digitized published curves because the raw
commercial-module stack optics are unavailable.

```bash
for f in fig4d_pdms fig4d_sds fig4d_ads fig5d_cooling_family; do
  radcoolpv run "validations/validation B/$f.yaml"
done
```

### C: silica micro-grating

Validation C exercises the one-dimensional silica grating. Its calculated
8--13 $\mu$m emittance is 0.938 versus approximately 0.90 in the paper. The
grating-equipped cell rises 37.8 °C above ambient versus 37.5 °C in the paper.
The bare-cell temperature is materially model-dependent, the solar-band
absorptivity is fixed, and normal-incidence optics are treated as
angle-independent.

```bash
cd "validations/validation C"
python run_validation.py
python run_validation.py --no-build  # reuse committed optical spectra
```

### E: optics agreement and thermal failure

Validation E obtains close agreement in the 7.5--16 $\mu$m cooling band. The
thermal comparison does not reproduce the paper when using its stated total
nonradiative coefficient $h=6.0$ W/m$^2$/K. For a zero-emissivity surface, the
stated energy balance gives 434.67 K, whereas the paper reports 366.5 K. A
fitted value $h=12.54$ W/m$^2$/K reproduces the reported temperatures, but that
is calibration, not independent validation.

```bash
radcoolpv run "validations/validation E/validation.yaml"
```

## What students should record

For every calculation, retain `run.json` and report three things:

1. the YAML inputs and recorded solver/data provenance;
2. the numerical checks applied, including energy closure and convergence of a
   named observable;
3. which reference is being compared and which approximations prevent a full
   validation claim.

The complete case definitions, literature details, comparison tables, and
limitations are maintained in the repository's
[validation README](https://github.com/gsilvaoelker/radcoolpv-py/blob/main/validations/README.md).
