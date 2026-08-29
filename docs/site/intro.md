# Radiative cooling of photovoltaic devices

This is the teaching interface for `radcoolpv`: a static explanation of the
model plus one Google Colab notebook for running the code. Nothing needs to be
installed on your own computer.

```{admonition} What runs where
:class: important
These pages are static. Calculations run in Google Colab. A fresh runtime
installs `radcoolpv` in about forty seconds; S4 is compiled only by the one
optional section that computes optics from a geometry.
```

## Start here

1. Read [Model and conventions](theory.md).
2. Read [Working with YAML](yaml-workflow.md).
3. Open the notebook and choose **Runtime → Run all**.
4. Edit the YAML in the notebook, upload your own optical data, and re-run.
5. Read [Validation evidence](validations.md) before quoting any number.

[Open the notebook in Google Colab](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/radcoolpv_colab.ipynb)

## The validation, notebook by notebook

One published paper, reproduced in three steps. Each notebook states the
physics it rests on, shows the YAML in full so it can be edited, accepts your
own uploaded data, and ends with the numbers it produced.

| Notebook | S4? | What it establishes |
|---|---|---|
| [A — calculated emittance](notebooks/validation_a_optics.ipynb) | needed | Emittance from the geometry. Mean over 7.5–16 µm: 0.032 / 0.842 / 0.984 against 0.036 / 0.843 / 0.977 digitized. **The optics agree.** |
| [B — cooling power](notebooks/validation_b_cooling.ipynb) | no | The energy balance alone, on the paper's *measured* spectrum. At the paper's own *h* = 6 W/m²/K it gives 415.4 / 360.6 / 355.6 K against a reported 360 / 339 / 336. **The thermal model does not reproduce the paper.** |
| [C — the full cell](notebooks/validation_c_pv.ipynb) | needed | Optics, heat and electricity coupled. 350.5 / 329.3 / 327.0 K and 14.17 / 18.09 / 18.64 %, reproducing the paper's 24 K drop as 23.5 K. |

Read them in order: A shows the optics are right, which is what makes B's
disagreement attributable to the thermal model rather than to the solver, and C
shows what the whole chain predicts once both are in place.

## Scope

`radcoolpv` couples RCWA optics, radiative exchange, convection, and a
single-diode photovoltaic model. S4 is the live optical solver. The free-form
and stored-spectrum inputs read externally generated or previously computed
spectra; they are readers, not independent optical solvers.

A full Run-all needs no solver. It produces the equilibrium temperature, every
term of the energy balance, and the complete set of PV parameters, from optical
data committed to the repository or uploaded by you. Computing the optics from
a geometry instead is an optional section, and the reduced grid it runs by
default is a smoke test rather than a converged result.

A number worth reporting additionally requires energy-conservation, basis-size,
wavelength-grid, and angular-grid checks, plus an independent reference. The
worked example shows what happens when one of those is missing: see
[Validation evidence](validations.md).
