# Radiative cooling of photovoltaic devices

This is the teaching interface for `radcoolpv`: a static explanation of the
model plus a Google Colab notebook for running the Python code. Students do not
need to install Python, S4, or the project dependencies on their own computers.

```{admonition} What runs where
:class: important
The pages are static. Numerical calculations run only in Google Colab. Each new
Colab runtime installs `radcoolpv` and compiles S4 before importing it.
```

## Start here

1. Read [Model and conventions](theory.md).
2. Read [Working with YAML](yaml-workflow.md).
3. Open the notebook and select **Open in Colab** in the page header, or use the
   direct link below.
4. Run the setup cells, edit `student.yaml`, and run the calculation.

[Open the notebook directly in Google Colab](https://colab.research.google.com/github/gsilvaoelker/radcoolpv-py/blob/main/docs/site/notebooks/radcoolpv_colab.ipynb)

## Scope

`radcoolpv` couples RCWA optics, radiative exchange, convection, and a
photovoltaic electrical model. S4 is the live optical solver. Free-form and
reduced-spectrum inputs read externally generated or previously stored spectra;
they are not independent optical solvers.

The Colab example is a smoke test. It demonstrates the workflow but is not
numerically converged. A reported scientific result additionally requires
energy-conservation, basis-size, wavelength-grid, and angular-grid checks.

For complete equations, implementation conventions, validation tables, and
limitations, see the [project manual](https://github.com/gsilvaoelker/radcoolpv-py/blob/main/docs/manual/radcoolpv_manual.pdf).
