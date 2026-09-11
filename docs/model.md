# The model

What `radcoolpv` computes, and what it assumes. Every symbol here maps to a
key in the YAML or a column in `run.json`.

## Optics

From the S4 flux amplitudes at the top and bottom of the stack,

$$
R=-\frac{P^-_{\mathrm{top}}}{P_{\mathrm{inc}}},\qquad
T=\frac{P^+_{\mathrm{bottom}}}{P_{\mathrm{inc}}},\qquad
A=1-R-T,
$$

and the silicon absorptance $A_{\mathrm{Si}}$ follows from the net flux
difference across the two silicon interfaces. Unpolarized illumination is the
mean of the two polarizations, $X_{\mathrm{unpol}}=(X_{\mathrm{TE}}+X_{\mathrm{TM}})/2$,
and the hemispherical average, written $\langle X\rangle$, uses projected
solid-angle weighting,

$$
\langle X\rangle(\lambda)=\frac{1}{\pi}\int_0^{2\pi}\!\!\int_0^{\pi/2}
X(\lambda,\theta,\phi)\cos\theta\sin\theta\,\mathrm{d}\theta\,\mathrm{d}\phi .
$$

A superscript $\perp$ denotes the same quantity at normal incidence, so
$A_{\mathrm{Si}}^{\perp}=A_{\mathrm{Si}}(\lambda,\theta=0)$. Emittance is
identified with absorptance by Kirchhoff's law,
$\epsilon(\lambda,\theta,\phi)=A(\lambda,\theta,\phi)$.

## Atmosphere and energy balance

The directional atmospheric emittance is built from the tabulated zenith
transmittance $\tau_{\mathrm{atm}}$,

$$
\epsilon_{\mathrm{atm}}(\lambda,\theta)=1-\tau_{\mathrm{atm}}(\lambda)^{1/\cos\theta},
$$

and the radiative terms are Planck-weighted integrals over wavelength and the
hemisphere,

$$
P_{\mathrm{rad}}(T)=\int\!\mathrm{d}\Omega\cos\theta\!\int\!\mathrm{d}\lambda\,
B_\lambda(T)\,\epsilon(\lambda,\theta),
\qquad
P_{\mathrm{atm}}=\int\!\mathrm{d}\Omega\cos\theta\!\int\!\mathrm{d}\lambda\,
B_\lambda(T_{\mathrm{amb}})\,\epsilon(\lambda,\theta)\,
\epsilon_{\mathrm{atm}}(\lambda,\theta),
$$

where $B_\lambda$ is the Planck spectral radiance. Since
$\int\mathrm{d}\Omega\cos\theta=\pi$ over the hemisphere, the code evaluates
both from pre-averaged spectra,

$$
P_{\mathrm{rad}}(T)=\pi\!\int\!\langle\epsilon\rangle B_\lambda(T)\,\mathrm{d}\lambda,
\qquad
P_{\mathrm{atm}}=\pi\!\int\!\langle\epsilon\,\epsilon_{\mathrm{atm}}\rangle\,
B_\lambda(T_{\mathrm{amb}})\,\mathrm{d}\lambda .
$$

The atmospheric term averages the **product**. Because
$\epsilon_{\mathrm{atm}}$ varies steeply with $\theta$,
$\langle\epsilon\,\epsilon_{\mathrm{atm}}\rangle\neq\langle\epsilon\rangle\langle\epsilon_{\mathrm{atm}}\rangle$,
and only the former is correct.

Absorbed sunlight and non-radiative exchange are

$$
P_{\mathrm{sun}}=\int\!\langle\epsilon\rangle\,I_{\mathrm{AM1.5}}(\lambda)\,\mathrm{d}\lambda,
\qquad
P_{\mathrm{conv}}(T)=h\,(T-T_{\mathrm{amb}}).
$$

The solar term uses the same angle-averaged absorptance as the thermal terms
rather than the absorptance at one solar direction.

The balance solved for the operating temperature is

$$
P_{\mathrm{cool}}(T)=P_{\mathrm{rad}}(T)-P_{\mathrm{atm}}+P_{\mathrm{conv}}(T)
-P_{\mathrm{sun}}+P_{\mathrm{MPP}}(T)+P_{\mathrm{nt}}(T),
$$

with the equilibrium temperature the root of $P_{\mathrm{cool}}(T_{\mathrm{eq}})=0$.
Check this sign convention before comparing with another paper or program.

## PV model

The band gap follows Varshni, and its wavelength sets the upper limit of every
photogeneration integral:

$$
E_g(T)=E_{g0}-\frac{\alpha T^2}{T+\beta},\qquad \lambda_g=\frac{hc}{E_g}.
$$

Short-circuit and saturation current densities come from the measured internal
quantum efficiency, the silicon absorptance, and the solar and blackbody photon
fluxes $\Phi$:

$$
J_{\mathrm{sc}}=q\!\int_0^{\lambda_g}\!\mathrm{IQE}\,\langle A_{\mathrm{Si}}\rangle\,
\Phi_{\mathrm{sun}}\,\mathrm{d}\lambda,
\qquad
J_0(T)=q\!\int_0^{\lambda_g}\!\mathrm{IQE}\,\langle A_{\mathrm{Si}}\rangle\,
\Phi_{\mathrm{bb}}(T)\,\mathrm{d}\lambda .
$$

Auger recombination adds a bias-dependent term with a tabulated, temperature-
interpolated coefficient $C_{\mathrm{A}}$ and intrinsic concentration $n_i$,

$$
J_{\mathrm{Aug}}(V,T)=2q\,C_{\mathrm{A}}(T)\,n_i^3(T)\,d_{\mathrm{Si}}
\exp\!\left(\frac{3qV}{2k_BT}\right),
$$

and the single-diode I-V with series and shunt resistance is solved implicitly
for $J$ at each voltage, writing $V_d=V-JR_s$:

$$
J=\frac{V_d}{R_{\mathrm{sh}}}
+J_0\!\left[\exp\!\left(\frac{qV_d}{k_BT}\right)-1\right]
+J_{\mathrm{Aug}}-J_{\mathrm{sc}} .
$$

The output power density is $P=-JV$; $P_{\mathrm{MPP}}$ and $V_{\mathrm{MPP}}$
are its sub-grid maximum, $V_{\mathrm{oc}}$ the interpolated zero crossing of
$-J$, and

$$
\mathrm{FF}=\frac{P_{\mathrm{MPP}}}{J_{\mathrm{sc}}V_{\mathrm{oc}}},
\qquad
\eta=\frac{P_{\mathrm{MPP}}}{P_{\mathrm{AM1.5}}},
\qquad
\beta_P=\frac{P_{\mathrm{MPP}}(T_{\mathrm{amb}})-P_{\mathrm{MPP}}(T_{\mathrm{eq}})}
{T_{\mathrm{amb}}-T_{\mathrm{eq}}}\cdot\frac{100}{P_{\mathrm{MPP}}(T_{\mathrm{amb}})} .
$$

Luminescent (non-thermal) emission from the cell depends on the operating
point, so $V_{\mathrm{MPP}}$ and $T_{\mathrm{eq}}$ are obtained together by
fixed-point iteration:

$$
P_{\mathrm{nt}}(T)=\pi\exp\!\left(\frac{qV_{\mathrm{MPP}}}{k_BT}\right)
\int_0^{\lambda_g}\!\mathrm{IQE}\,A_{\mathrm{Si}}^{\perp}\,
B_\lambda(T)\,\mathrm{d}\lambda .
$$

This is the only term that uses the normal-incidence absorptance rather than
the hemispherical average.

## Assumptions

Optical:

- Media are linear, passive, reciprocal, non-magnetic, and in local thermal
  equilibrium, which is what licenses $\epsilon=A$.
- S4 solves RCWA: the structure is laterally infinite and strictly periodic,
  layers are coherent, and the Fourier basis is truncated at `optics.s4_modes`. A
  result is only meaningful once it is converged in modes, wavelength grid, and
  angular quadrature.
- Material data are tabulated or analytic dispersions from the sources listed
  in `radcoolpv/materials/SOURCES.md`; extrapolation outside their range is not
  performed.

Thermal:

- Steady state, with one lumped temperature for the whole stack — no in-plane
  or through-thickness gradient.
- Radiative exchange is one-sided, per unit area, into a plane-parallel sky at
  ambient temperature, using a single stored clear-sky transmittance. Clouds,
  ground exchange, and site-specific atmospheres are not modeled.
- All non-radiative exchange is one temperature-independent coefficient $h$
  lumping convection and conduction.
- The full absorptance $\epsilon$ heats the module, while only $A_{\mathrm{Si}}$
  generates carriers: parasitic absorption is a thermal load and no more.
- $P_{\mathrm{MPP}}$ is subtracted from the balance, so the module is assumed to
  run at its maximum power point with the electrical energy exported rather
  than dissipated.
- A spectrum supplied as a single emittance column can drive the thermal
  model, but its atmospheric term is then the zenith atmosphere times the
  averaged emittance: an explicitly angle-independent approximation. An
  `optics.txt` written by radcoolpv carries the angle-averaged product and is
  exact.

PV:

- Single-diode model with constant $R_s$ and $R_{\mathrm{sh}}$, ideality one,
  and radiative saturation current from detailed balance below $\lambda_g$.
- $\lambda_g$ is reduced to a single scalar over the temperature sweep,
  reproducing the MATLAB original, so the integration cut-off does not move
  with $T$. It is a weighted mean over the whole swept range, so **setting
  `thermal.temperatures` moves the cut-off** and with it $J_{sc}$ and
  $\beta_P$. The default range is left at the MATLAB one, $T_{amb}$ to
  $T_{amb}+150$ K, for that reason; widen it deliberately, not incidentally.
- When the optics come from a single supplied emittance column, $A_{Si}$ is
  taken to equal $\epsilon$ below $\lambda_g$ and zero above, since parasitic
  absorption above the gap is neglected. `run.json` records that this was
  assumed rather than solved.
- IQE is read from a measured file and set to zero outside its range.
- Sunlight is the AM1.5 global spectrum, absorbed through the hemispherically
  averaged absorptance rather than at a single solar direction — consistent
  with AM1.5G including a diffuse component. There is no explicit sun
  position, spectral shift, or concentration.

Numerical:

- All spectral integrals are trapezoidal on the user's wavelength grid, so the
  grid must resolve the bands that matter, including the 8-13 um atmospheric
  window.
- Cost scales roughly as $n_\lambda n_\theta n_\phi n_{\mathrm{pol}}$ times
  the cube of `s4_modes`.
