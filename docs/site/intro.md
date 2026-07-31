# Radiative cooling of photovoltaic devices

This is the teaching interface for `radcoolpv`: a static explanation of the
model plus a Google Colab notebook for running the Python code. Students do not
need to install Python, S4, or the project dependencies on their own computers.

```{admonition} What runs where
:class: important
The pages are static. Numerical calculations run only in Google Colab. Each new
Colab runtime installs `radcoolpv`; S4 is compiled only by notebooks or optional
cells that request live optics.
```

## Start here

1. Read [Model and conventions](theory.md).
2. Read [Working with YAML](yaml-workflow.md).
3. Read [Validation evidence](validations.md) to understand what each supplied
   case does and does not establish.
4. Open the main notebook below, or use the validation-specific Colab link in
   each section of [Validation evidence](validations.md).
5. Run the setup cells, edit the optical and PV YAML files, and inspect the
   reported parameters and figures.

[Open the notebook directly in Google Colab](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/radcoolpv_colab.ipynb)

## Scope

`radcoolpv` couples RCWA optics, radiative exchange, convection, and a
photovoltaic electrical model. S4 is the live optical solver. Free-form and
reduced-spectrum inputs read externally generated or previously stored spectra;
they are not independent optical solvers.

The main Colab notebook first executes a small live-S4 optical smoke test. It then
uses a committed Validation A.1 spectrum to obtain operating temperature,
current-voltage behavior, maximum power, fill factor, efficiency, and the main
figures. Neither shortcut is a converged literature reproduction. A reported
scientific result additionally requires energy-conservation, basis-size,
wavelength-grid, angular-grid, and independent-reference checks.

The governing equations and conventions are maintained in
[Model and conventions](theory.md); evidence-qualified results and references
are maintained in [Validation evidence](validations.md).
