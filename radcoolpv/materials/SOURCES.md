# Material-data sources

## Gold

`RII_Olmon_2012_ev_Au.yml` is the unmodified refractiveindex.info record for
evaporated gold from:

R. L. Olmon et al., “Optical dielectric function of gold,” *Physical Review B*
**86**, 235147 (2012), https://doi.org/10.1103/PhysRevB.86.235147.

Source:
https://github.com/polyanskiy/refractiveindex.info-database/blob/main/database/data/main/Au/nk/Olmon-ev.yml.
The local file has SHA-256
`be778621e6491fc4e2db6eee400fb329d44ada2b987f7bfd2e219c83fe32a338`.
It is used by the Akerboom case over 2–16 µm, within its 0.300–24.93 µm range.

## Akerboom silicon and silica

The paper cites Palik/Kitamura for Si and SiO2. The refractiveindex.info
database checked on 2026-07-27 contains the required Olmon Au record, but no
records labelled Palik silicon, Palik silica, or Kitamura silica. Substituting a
different current database record would change the paper model.

The Akerboom case therefore retains the tables inherited from `matlab-radCoolPV`:

- `PalikKitamura_SiO2.csv`, converted without refitting from
  `materials/PalikKitamura_SiO2.m`. Its MATLAB header attributes values below
  4 µm to Kitamura and the remaining values to Palik p. 749. SHA-256:
  `1df3806f80806a90a686b8b7f25edfa99f30fcac44934c9d458d17d467fc6efd`.
- `SiliconNew.csv`, converted from `materials/silicon.m`. That MATLAB file
  calls the table “Silicon testing calculated data” but gives no bibliographic
  source. The `Akerboom_Si_lossless` model uses only its refractive
  index and sets `k = 0`, matching the paper's explicit nonabsorbing-Si
  assumption. The refractive-index provenance remains unresolved. SHA-256:
  `2fcc896375e9da0cd8c9c8ff3b0d4a4743b37f9c726f627d643c42b8e80ee4fb`.

This is a documented source limitation, not a claim that all Akerboom-case
materials came from refractiveindex.info. Every tabulated loader rejects
extrapolation.

## Palik silicon

`Palik_Si.csv` was converted without refitting from
`permittivityDataBase/Palik_Si.m` in the `matlab-radCoolPV` project, using
a one-off conversion script. That MATLAB file is headed
"Si dielectric constant from Palik" and is byte-identical across the three
copies of the database on record. It gives no page reference, so the specific
Palik volume and chapter remain unverified; the attribution is the MATLAB
header's, carried over unchanged. SHA-256:
`ef4d0801411d809c10ab2629c5fb28363a4b0e6c6515948ffc4ff19a1d1f458d`.

351 points spanning 0.1907–40 µm, which is wider than `SiliconNew.csv`
(0.28–30 µm) at both ends. Sampling is 146 points below 1.2 µm and 40 across
the 8–14 µm window.

Its refractive index agrees with `SiliconNew.csv` to roughly four decimals
across the whole overlap, which is circumstantial evidence that the two share an
origin and partially answers the unresolved provenance noted above. The
extinction coefficients do **not** agree in the infrared: `SiliconNew` is larger
by ~216x at 3 µm and ~6x at 30 µm. Both are minute in absolute terms, but the
silicon layer is 250–500 µm thick, so the choice moves parasitic sub-gap
absorption and therefore the emittance in the cooling band. Neither table
states a doping level, and free-carrier absorption in that band depends on it,
so neither should be treated as authoritative for a doped cell without a
source that specifies the wafer.
