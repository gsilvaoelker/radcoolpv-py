# Model and conventions

This page summarizes the active equations and the conventions needed to
interpret an output.

## Optical balance

For incident power flux $P_{\mathrm{inc}}$, the code defines

$$
R=-\frac{P^-_{\mathrm{top}}}{P_{\mathrm{inc}}},\qquad
T=\frac{P^+_{\mathrm{bottom}}}{P_{\mathrm{inc}}},\qquad
A=1-R-T.
$$

The silicon absorptance is obtained from the net flux difference across the
silicon interfaces. For unpolarized illumination,

$$
X_{\mathrm{unpol}}=\frac{X_{\mathrm{TE}}+X_{\mathrm{TM}}}{2}.
$$

The hemispherical average uses projected solid-angle weighting,

$$
X_h(\lambda)=\frac{1}{\pi}\int_0^{2\pi}\int_0^{\pi/2}
X(\lambda,\theta,\phi)\cos\theta\sin\theta\,d\theta\,d\phi.
$$

Directional Kirchhoff identification, $\epsilon=A$, is used only under the
usual assumptions of a passive reciprocal system in local thermal equilibrium.

## Atmosphere and thermal balance

For atmospheric zenith transmittance $\tau_{\mathrm{atm}}$, the directional
atmospheric emittance is

$$
\epsilon_{\mathrm{atm}}(\lambda,\theta)
=1-\tau_{\mathrm{atm}}(\lambda)^{1/\cos\theta}.
$$

The emitted and absorbed atmospheric powers are spectral integrals of the
Planck radiance. In the code's cooling-power convention,

$$
P_{\mathrm{cool}}(T)=P_{\mathrm{rad}}(T)-P_{\mathrm{atm}}
+P_{\mathrm{conv}}(T)-P_{\mathrm{sun}}+P_{\mathrm{MPP}}(T)+P_{\mathrm{nt}},
$$

with

$$
P_{\mathrm{conv}}=h(T-T_{\mathrm{amb}}).
$$

The equilibrium temperature is a root of
$P_{\mathrm{cool}}(T)=0$. Check the sign convention before comparing this
quantity with another paper or program.

## Minimum numerical checks

A runnable case is not automatically a valid result. At minimum:

- verify finite outputs, passivity, and $R+T+A\approx1$;
- increase `simulation.s4_modes` until the reported observable stabilizes;
- refine the wavelength grid;
- for hemispherical results, refine both theta and azimuthal quadratures;
- state the material-data source and every calibrated rather than paper-stated
  thermal parameter.

The computational cost scales approximately as
$n_\lambda n_\theta n_\phi n_{\mathrm{pol}}$. The default full YAML therefore
does not belong in an introductory free-Colab exercise without first reducing
the grid.
