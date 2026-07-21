# radcoolpv — code review

> **SUPERSEDED — historical record, retained for provenance.**
>
> This review describes a state of the package that no longer exists: it was
> written when the optics engine had just been swapped from S4 to the pure-Python
> `grcwa`. That swap has since been **reversed** — S4 is again the only RCWA
> backend and `grcwa_backend.py` has been removed.
>
> Two conclusions below are now known to be **wrong**:
>
> * *"S4 Python accessibility"* concluded the S4 pyext "was never built" and that
>   building it was impractical. In fact the module builds fine from the
>   maintained fork `github.com/phoebe-p/S4`; only *upstream* `victorliu/S4` fails,
>   because its binding still calls the Python 2 C API and no longer matches its
>   own `libS4` signatures. See the README for the working recipe.
> * The claim that the toolchain has "no compiled dependency" no longer holds.
>
> Findings 2 (`test2`), 5 (`emit_atm` column) and the dead-reference loaders have
> since been fixed or removed. Findings 1, 3, 5 (bandgap scalar), 6 and 7 were
> still open at the time of writing.

Scope: the `radcoolpv` package as of this change set (pure-Python optics via
`grcwa`). Report only; no code was changed for the sake of the review. The one
functional change in this session — replacing the S4 backend with `grcwa` — is
described under "Changes made".

## Architecture & execution flow

`cli.run` → `config.load` (parse + `validate`) → `pipeline.run`:

1. **Optics** (`_run_optics`): live RCWA (`grcwa_backend.sweep`), free-form data
   (`freeform.load`), or resume (`directional.from_folder` for raw `OUTPUTS4`
   folders, or `from_reduced_file` for a 5-/7-column spectrum). Raw per-angle
   data is reduced to spectral properties by `directional.reduce`.
2. **Thermal** (`energy_balance.run`): assembles the energy balance and solves
   the equilibrium temperature; the full-PV path adds the diode I–V
   (`thermal.pv`). Coupled in memory to the optics result.
3. **Outputs / plots**: `io.legacy_writers` + `io.clean_writers`, `plotting.figures`.

The design is clean: the RCWA engine is isolated behind a `RawOptics` contract
and a solver-agnostic geometry description (`geometry.build_structure`), which is
what made the S4→grcwa swap a localized change.

## Optics

* **Engine (`grcwa_backend`).** Pure-Python RCWA. Reproduces the analytic TMM
  result for flat stacks to ≤3·10⁻³ (R, T, and per-layer silicon absorptance,
  at normal and 60° incidence, TE and TM); the patterned/grid path reduces
  exactly to the uniform limit; patterned runs conserve energy (R+T+A=1).
  Silicon absorptance is the net z-Poynting-flux difference across the Si layer
  (the exact analogue of the old S4 `GetPowerFlux` bookkeeping).
  *Limitations:* (a) pure-Python RCWA is much slower than the old C++ S4 — a
  full 2000-λ × 18-angle patterned sweep is minutes-to-hours (tune
  `simulation.rcwa_modes` = grcwa `nG`, `grid_nx/ny`, or reduce λ/angles);
  (b) patterns are rasterised to an `Nx×Ny` grid (staircase) rather than S4's
  analytic shapes; (c) for a very thick *absorbing* layer the flux-difference
  `a_si` is clipped to `[0, A_total]` for numerical safety (irrelevant in the
  IR where Si is transparent).
* **Structures.** flat / sphere / semisphere / triangle / cylinder, discretised
  by `geometry.py`, on an ordered flat `structure` with exactly one `terminal`
  substrate; lattice square or hexagonal. Internal dataclasses keep the legacy
  names `S4Structure` / `S4Layer` (documented in `geometry.py`).
* **Reduction (`directional.reduce`).** Note finding 5 below re: the `emit_atm`
  column.

## PV / thermal

* Energy-balance terms (`energy_balance`): `P_rad = π∫εB(T)dλ`,
  `P_atm = π∫ε·ε_atm·B(T_amb)dλ`, `P_conv = h(T−T_amb)`, `P_sun`, and (full PV)
  `P_mpp`, `P_nonthermal`. Equilibrium is the first zero-crossing of the cooling
  curve; the full-PV path fixes `Vmpp` by a fixed-point iteration.
* Electrical model (`thermal.pv`): temperature-dependent bandgap, `Jsc` from
  `IQE·A_si·Φ_sun` up to `λg`, saturation current from the blackbody photon
  flux, Auger recombination, an `Rs`/`Rsh` diode solved per (T,V) with `fsolve`
  (continuation warm-start), then MPP / Voc / FF / efficiency / β_P.

## Findings

| # | Sev | Finding |
|---|-----|---------|
| 1 | **High** | **Stale editable install shadows the working copy.** The homebrew `radcoolpv` console script and any script run *by path* import `radcoolpv` from a stale copy at `~/Desktop/Research Projects/radCoolPV/radcoolpv-py` (an older `config.py`, no `cooling_curve`). Effect: `radcoolpv run` on any `cooling_curve` config (Validation B) fails with `TypeError`; `standard`-mode configs silently run old code. This is an install-state issue, not a repo bug. **Workaround (used throughout the docs):** prefix commands with `PYTHONPATH="$PWD"`. **Durable fix:** re-run `pip install -e .` from this copy, or use a `.venv` (`./install.sh`). |
| 2 | Med | **`run.mode: test2` is accepted but unimplemented.** `validate()` allows it, but `energy_balance.run` only special-cases `test` and `cooling_curve`, and `figures.make_all` gives it no handling, so `test2` silently behaves like `standard`. Either remove it from `validate` or implement it; documented as unsupported in the manual. |
| 3 | Low | **`emit` column double duty in `cooling_curve`.** `solar_power = ∫emit·AM1.5 × (solar_irradiance/total_am15)` reuses the IR-emissivity column as the solar absorptivity, so a resumed reduced file must set the sub-bandgap `emit` deliberately. Correct behaviour, but a foot-gun — documented in the manual. |
| 4 | Low | **Hemispherical `emit_atm` output column is not solid-angle weighted.** `directional.reduce` sums `1−τ^(1/cosθ)` over angles×dθ without the cosθ·sinθ weight (matches the original MATLAB); only the weighted `emitt_spec_times_emit_atm` feeds `P_atm`. The `emit_atm` CSV column is a display quantity that maxes near π/2, not 1 — do not read it as an emissivity. |
| 5 | Low | **Bandgap-wavelength scalar reduction.** `pv._bandgap_wavelength_um` reproduces a MATLAB matrix right-division that collapses the temperature sweep to a *single* scalar `λg` (`dot(T²,T+β)/dot(T+β,T+β)`), so the integration cut-off is one weighted value, not per-temperature. Intentional MATLAB parity; an approximation to be aware of. |
| 6 | Low | **`open_circuit_voltage` clamps to `volt[-1]`** when `−J` never crosses zero within the sweep, so too-low a `thermal.voltage.max` yields a silently wrong Voc. Depends on input range. |
| 7 | Low | **Error-handling gaps.** Missing data files surface as raw numpy/IO errors; no check that a reduced file's `emit ∈ [0,1]`; `fsolve` return codes are not inspected. None are incorrect, just unfriendly. |

(The previously-stale `configs/full.yaml` mode comment was corrected as part of
the S4→grcwa config edits.)

## Units & numerical consistency

Constants (`constants.py`) are SI with explicit µm↔m factors; `_compat.trapz`
covers NumPy 1.x/2.x. Tabulated permittivity is cached and interpolated as
`(n+ik)²`. Spectral integrals in the PV path run to `λg`. No unit inconsistency
found; the thermal path is checked against Stefan–Boltzmann and the Perrakis
2020 reference in the test suite, and the new backend against analytic TMM.

## Dependencies & reproducibility

Runtime deps are pure Python: numpy, scipy, matplotlib, pyyaml, openpyxl, and now
**grcwa** (numpy + autograd). `tmm` is a test-only reference. There is no longer
any compiled/native dependency. Reproducibility's main hazard is finding 1
(which interpreter/copy is used).

## S4 Python accessibility (verification result)

* `import S4` **fails** in every interpreter on this machine (`python`,
  `python3`, homebrew `python@3.11`) → `ModuleNotFoundError: No module named 'S4'`.
* What is installed is the **standalone Lua binary** only —
  `~/Documents/S4-master/build/S4` (executable, Mar 2023) plus `RCWA.so`; the
  **Python extension `S4.so` was never built** (none on disk; the source tree's
  `modules/setup.py` builds only the FunctionSampler helpers, not S4). So S4 was
  usable as a CLI Lua solver but never as a Python module, which is what the code
  required.
* **Resolution:** rather than build the (finicky, C++/Boost/FFTW) S4 pyext, the
  optics engine was replaced with the pure-Python `grcwa`, which is already
  installed and importable. radcoolpv is now a fully pure-Python replacement of
  the MATLAB+S4 toolchain.

## Changes made this session

* Added `radcoolpv/optics/grcwa_backend.py`; removed `radcoolpv/optics/s4_backend.py`.
* Wired grcwa in: `config.py` (`geometry.source` → `grcwa|freeform`, dropped
  `BackendConfig`, source-enum check), `pipeline.py`, `simulation.grid_nx/ny`.
* Updated `configs/*.yaml`, `requirements.txt`, `pyproject.toml`, `install.sh`,
  `README.md`, package/geometry docstrings; added `tests/test_grcwa_backend.py`.
* No other source behaviour changed; `pytest -q` = 36 passed, 1 skipped.
