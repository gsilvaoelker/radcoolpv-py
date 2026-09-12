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

## refractiveindex.info records

Unmodified records from the refractiveindex.info database (public domain,
CC0), fetched on 2026-09-12 from
https://github.com/polyanskiy/refractiveindex.info-database at commit
`c5c2f188e848453def5970e347399d653df2ffc2`. Each is one `tabulated nk`
dataset; the model name is the file stem, and the loader refuses any
wavelength outside the stated range. `RII_Olmon_2012_ev_Au` above belongs
to the same family.

| model | material | range (um) | reference | path under `database/data/` | SHA-256 |
|---|---|---|---|---|---|
| `RII_Franta_2017_Si` | float-zone crystalline Si, 25 C | 0.031–310 | Franta et al., Appl. Surf. Sci. 421, 405 (2017) | `main/Si/nk/Franta-25C.yml` | `c3e042b7…4cb16a` |
| `RII_Green_2008_Si` | intrinsic Si, 300 K; k is band-to-band only | 0.25–1.45 | Green, Sol. Energy Mater. Sol. Cells 92, 1305 (2008) | `main/Si/nk/Green-2008.yml` | `4b785ec4…52ce4` |
| `RII_Franta_2016_SiO2` | fused silica plate (Lithosil Q) | 0.025–125 | Franta et al., Proc. SPIE 9890, 989014 (2016) | `main/SiO2/nk/Franta.yml` | `89e3065c…458e` |
| `RII_Franta_2015_Al2O3` | e-beam Al2O3 film, 121.5 nm | 0.114–125 | Franta et al., Proc. SPIE 9628, 96281U (2015) | `main/Al2O3/nk/Franta.yml` | `e2b3bfc8…a4df0` |
| `RII_Siefke_2016_TiO2` | ALD TiO2 film, 350 nm | 0.120–125 | Siefke et al., Adv. Opt. Mater. 4, 1780 (2016) | `main/TiO2/nk/Siefke.yml` | `9b039479…2885c` |
| `RII_Franta_2015_HfO2` | e-beam HfO2 film, 112.7 nm | 0.115–125 | Franta et al., Appl. Opt. 54, 9108 (2015) | `main/HfO2/nk/Franta.yml` | `c2566863…fee92a` |
| `RII_Franta_2017_MgF2` | e-beam MgF2 film, 134.2 nm | 0.028–125 | Franta et al., Appl. Surf. Sci. 421, 424 (2017) | `main/MgF2/nk/Franta.yml` | `c51389d0…2e58e` |
| `RII_Yang_2015_Ag` | template-stripped Ag | 0.27–24.92 | Yang et al., Phys. Rev. B 91, 235137 (2015) | `main/Ag/nk/Yang.yml` | `6e486b57…01cf9` |
| `RII_Rakic_1998_Al` | Al, Brendel–Bormann fit | 0.062–248 | Rakić et al., Appl. Opt. 37, 5271 (1998) | `main/Al/nk/Rakic-BB.yml` | `2e3d1e79…f20d02c` |
| `RII_Zhang_2020_PDMS` | PDMS, Sylgard 10:1 | 0.4–19.94 | Zhang et al., Appl. Opt. 59, 2337 (2020); JQSRT 252, 107063 (2020) | `organic/(C2H6OSi)n - polydimethylsiloxane/nk/Zhang-10-1.yml` | `668c7bfe…7d3a2d` |
| `RII_Zhang_2020_PMMA` | PMMA (Tomson) | 0.4–19.94 | same | `organic/(C5H8O2)n - poly(methyl methacrylate)/nk/Zhang-Tomson.yml` | `334f5701…ad0ccf0` |
| `RII_Zhang_2020_PET` | PET | 0.4–19.94 | same | `organic/(C10H8O4)n - polyethylene terephthalate/nk/Zhang.yml` | `685cec36…070497` |
| `RII_Zhang_2020_PC` | polycarbonate | 0.4–19.94 | same | `organic/(C16H14O3)n - polycarbonate/nk/Zhang.yml` | `d5487142…779564` |

Full digests: `sha256sum radcoolpv/materials/data/RII_*.yml`.

Range is the first thing to check. The default grid (0.3–30 um) and the
Akerboom case (0.3–24.9 um) fit `RII_Franta_2017_Si`, the four Franta
dielectrics, `RII_Siefke_2016_TiO2` and `RII_Rakic_1998_Al`; the two
evaporated-metal records stop at 24.9 um and the Zhang polymers at 19.94 um,
so a case using them sets `optics.wavelength.max` accordingly.
`RII_Green_2008_Si` is the solar-band reference for a cell and cannot drive a
thermal run on its own. Not included, and why: the database's `Si/Franta.yml`
is a-Si:H film, not crystalline; Si3N4 has no record spanning both the solar
band and the atmospheric window (`DrudeSi3N4` covers all wavelengths); Cu
stops at 12.4 um; polyethylene at 12 um.
