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
