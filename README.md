# Dolmen Distribution and Ancient Maritime Hazard

*[한국어 README](README.ko.md)*

A spatial-statistical test of whether dolmen density in the Yeongsan River basin
(Jeollanam-do, South Korea) is associated with the physical hazard of adjacent seas.

## Background

The Korean peninsula holds roughly 35,000 dolmens — about 40% of the world total —
with the heaviest concentration in the southwest. One proposed explanation is that
megaliths mark departure or return points of prehistoric sea voyages, and therefore
cluster where maritime crossings were most dangerous.

This repository tests that proposition directly, using survey-report counts rather
than designation records, and reports the result whether or not it supports the
hypothesis.

## Result

> **Hypothesis rejected.** Once spatial autocorrelation is accounted for, every
> maritime hazard variable loses significance and four of them reverse sign.
> Dolmen density in the study area is explained by spatial clustering itself,
> not by the physical hazard of the neighbouring sea.

This holds across all four hazard components, including ERA5 significant wave height.

| Predictor | Non-spatial OLS | Spatial lag (GM_Lag) |
|---|---|---|
| Distance to coast | −0.307 (p<0.0001) | +0.056 (p=0.321) |
| Adjacent-sea current speed p90 | +0.146 (p=0.0001) | −0.071 (p=0.062) |
| Adjacent-sea bathymetric gradient | −0.200 (p<0.0001) | +0.007 (p=0.851) |
| Adjacent-sea depth | −0.293 (p<0.0001) | +0.059 (p=0.272) |
| Adjacent-sea significant wave height p90 | −0.139 (p=0.0020) | +0.021 (p=0.604) |
| **Spatial lag ρ** | — | **+1.184 (p<0.0001)** |

`OLS R² = 0.094` (residual Moran's I = +0.367, p=0.001) · `GM_Lag Pseudo R² = 0.409`

Note the wave-height coefficient: it is **negative even in the non-spatial model**.
Proximity to rougher seas is associated with *fewer* dolmens — the opposite of what
the hypothesis predicts.

![Coefficient comparison](reports/figures/fig2_coefficients.png)

## Data

| Source | Scale | Access |
|---|---|---|
| *Yeongsan River Basin Dolmens* Vol. Ⅴ, books 1–5 | 3,175 pages → 1,638 sites / 7,027 dolmens | Manual acquisition |
| Korea Heritage Service OpenAPI | 169 designated dolmens | No key required |
| OSM Overpass megaliths | 14,105 features | No key required |
| NOAA ETOPO 2022 bathymetry | 30-arcsecond grid | No key required |
| HYCOM GLBy0.08 surface currents | 49 timesteps | No key required |
| ERA5 significant wave height | 2017–2020, 1,968 timesteps | CDS key required |

The source PDFs (~1.3 GB) are gitignored. Place them in `data/external/` to reproduce
the parsing stage.

## Pipeline

```bash
conda env create -f environment.yml && conda activate dolmen

make data      # OSM / Korea Heritage Service / Natural Earth
make ocean     # ETOPO bathymetry + HYCOM currents + ERA5 waves
make parse     # Parse 5 report volumes, geocode to ri (里) level
make grid      # 5 km grid (EPSG:5179) + marine exposure index
make model     # Negative binomial + spatial regression
make figures   # Four result figures
```

`make ocean` needs a Copernicus CDS key at `~/.cdsapirc`. The other stages run
without credentials.

## Documentation

| Document | Contents |
|---|---|
| [00_hypothesis](docs/00_hypothesis.md) | Four structural problems with the original hypothesis; reformulation |
| [01_data_inventory](docs/01_data_inventory.md) | Measured data inventory; **OSM 515× survey bias** |
| [02_methodology](docs/02_methodology.md) | Gate-based analysis design |
| [03_project_plan](docs/03_project_plan.md) | A–Z plan with pre-declared stopping rules |
| [04_results](docs/04_results.md) | Full results |
| [05_limitations](docs/05_limitations.md) | Limitations, graded by severity |

Documentation is in Korean; code and comments are mixed Korean/English.

## Three methodological findings

**1. OSM megalith data carries a 515× survey-intensity bias.**
Detection rate is 39.6% in Europe versus 0.077% in Korea. The peninsula holds ~40%
of the world's dolmens but appears in OSM with 27 records. Running a global
regression on the raw data inverts the conclusion.

**2. Designation count ≠ monument count.**
Korea Heritage Service designations are group-level: one Hwasun dolmen-group record
covers 596 individual monuments. Per-monument counts exist only in field survey
reports, which is why the PDF parsing stage exists.

**3. Ignoring spatial autocorrelation manufactures significance.**
Four maritime effects significant at p<0.0001 in the non-spatial model vanished and
reversed after spatial correction. This is the central lesson of the project.

## Pre-registration and honest reporting

Stopping rules were declared in `docs/03_project_plan.md` *before* the analysis was
run. Rule 3 (sign reversal across grid scales) triggered, so all results are
downgraded from confirmatory to **exploratory**. No model was re-specified in search
of significance.

Conditions that would overturn the conclusion are listed in
[`docs/05_limitations.md`](docs/05_limitations.md). The main one is that ERA5's 0.25°
grid cannot resolve local wave conditions in the southwestern archipelago; a nested
coastal wave model (SWAN, WAVEWATCH III) would be the substantive rebuttal.

## Sources and licensing

- *영산강유역 지석묘* Ⅴ (Yeongsan River basin dolmen survey reports)
- Korea Heritage Service National Heritage Portal OpenAPI — KOGL
- OpenStreetMap contributors — ODbL 1.0
- NOAA NCEI ETOPO 2022 · HYCOM Consortium GLBy0.08
- Copernicus Climate Change Service (C3S) ERA5 — contains modified Copernicus
  Climate Change Service information; neither the European Commission nor ECMWF is
  responsible for any use of this information
- Natural Earth — Public Domain
- Schulz Paulsson, B. (2019) *PNAS* 116(9):3460–3465
- UNESCO WHC #977, Gochang, Hwasun and Ganghwa Dolmen Sites

Code in this repository is available under the MIT License. Derived datasets in
`data/processed/` are 5 km aggregates; underlying report content remains with its
original rights holders.
