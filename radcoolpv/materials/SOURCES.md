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
It is used by Validation E over 2–16 µm, within its 0.300–24.93 µm range.

## Validation E silicon and silica

The paper cites Palik/Kitamura for Si and SiO2. The refractiveindex.info
database checked on 2026-07-27 contains the required Olmon Au record, but no
records labelled Palik silicon, Palik silica, or Kitamura silica. Substituting a
different current database record would change the paper model.

Validation E therefore retains the tables inherited from `matlab-radCoolPV`:

- `PalikKitamura_SiO2.csv`, converted without refitting from
  `materials/PalikKitamura_SiO2.m`. Its MATLAB header attributes values below
  4 µm to Kitamura and the remaining values to Palik p. 749. SHA-256:
  `1df3806f80806a90a686b8b7f25edfa99f30fcac44934c9d458d17d467fc6efd`.
- `SiliconNew.csv`, converted from `materials/silicon.m`. That MATLAB file
  calls the table “Silicon testing calculated data” but gives no bibliographic
  source. Validation E's `Akerboom_Si_lossless` model uses only its refractive
  index and sets `k = 0`, matching the paper's explicit nonabsorbing-Si
  assumption. The refractive-index provenance remains unresolved. SHA-256:
  `2fcc896375e9da0cd8c9c8ff3b0d4a4743b37f9c726f627d643c42b8e80ee4fb`.

This is a documented source limitation, not a claim that all Validation E
materials came from refractiveindex.info. Every tabulated loader rejects
extrapolation.
