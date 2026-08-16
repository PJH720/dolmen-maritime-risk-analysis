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

## Result (v1, provisional)

> These are **v1 interim findings.** A v2 iteration with additional data and a
> revised hypothesis is planned, so the statements below describe *what is observed
> under the current data and specification* — not a settled conclusion.

The original hypothesis predicted a **monotonic positive** relationship: rougher seas,
more dolmens. That specific form is **not supported** by the current data.

This does **not** mean dolmen distribution is unrelated to the marine environment.
If anything, the opposite.

### What was found: an inverted-U relationship with wave height

| Wave quartile | Mean SWH p90 | Dolmens | Share |
|---|---|---|---|
| Q1 (calmest) | 0.29 m | 353 | 5.4% |
| **Q2** | **0.57 m** | **2,998** | **45.8%** |
| **Q3** | **0.96 m** | **2,738** | **41.9%** |
| Q4 (roughest) | 1.06 m | 450 | 6.9% |

**87.7% of all dolmens fall in the two middle quartiles**, with both extremes nearly
empty. A quadratic term test gives `LR = 159.21, p ≈ 1.7e-36`, with an estimated
peak at **0.684 m**.

So a relationship exists, and a strong one. It is simply **non-monotonic**, which is
why linear specifications failed to capture it — and why a rank correlation reports
near-zero (Spearman ρ = +0.049, p = 0.10): the inverted U cancels out under a
monotonic measure.

![Wave non-linearity](reports/figures/fig5_wave_nonlinear.png)

### Three readings to avoid

**1. A negative coefficient is not "no effect."**
In the full linear specification the wave coefficient is −0.238 (p<0.0001). That is a
*directional* finding — proximity to rougher seas is associated with *fewer* dolmens.
It runs opposite to the hypothesis, but it is not an absence of information. It also
strengthens with aggregation scale (5 km −0.238 → 20 km −0.670), which argues against
it being noise.

**2. The wave coefficient's sign is specification-dependent.**
Univariate +0.268 → +coast distance +0.241 → +depth −0.018 → full model −0.238. Wave
height and depth correlate at r = −0.507, producing a suppression structure. Any
single coefficient reported in isolation is misleading.

**3. Non-significance after spatial correction is an identification failure, not
proof of independence.**
With ρ = 1.18, the spatial lag term absorbs the environmental signal; the two
components cannot be separated under the current design. Absence of evidence is not
evidence of absence.

### Linear-specification regression (for reference)

| Predictor | Non-spatial OLS | Spatial lag (GM_Lag) |
|---|---|---|
| Distance to coast | −0.307 (p<0.0001) | +0.056 (p=0.321) |
| Adjacent-sea current speed p90 | +0.146 (p=0.0001) | −0.071 (p=0.062) |
| Adjacent-sea bathymetric gradient | −0.200 (p<0.0001) | +0.007 (p=0.851) |
| Adjacent-sea depth | −0.293 (p<0.0001) | +0.059 (p=0.272) |
| Adjacent-sea significant wave height p90 | −0.139 (p=0.0020) | +0.021 (p=0.604) |
| **Spatial lag ρ** | — | **+1.184 (p<0.0001)** |

`OLS R² = 0.094` (residual Moran's I = +0.367, p=0.001) · `GM_Lag Pseudo R² = 0.409`

This table assumes a **monotonic linear** form. Given the inverted-U structure above,
these coefficients should be read as a non-linear relationship compressed into a
linear frame, not as the relationship itself.

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
| [06_v2_roadmap](docs/06_v2_roadmap.md) | v2 plan — the "navigable band" hypothesis |

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

**3. Assuming monotonicity can hide a strong relationship.**
Wave height relates to dolmen density in an inverted U, yet a rank correlation reports
ρ = +0.049 and linear models flip sign depending on controls. Inspect the descriptive
structure before imposing a functional form.

**4. Ignoring spatial autocorrelation manufactures significance — and correcting it
can hide real effects.**
Maritime effects significant at p<0.0001 vanished after spatial correction. But with
ρ = 1.18 exceeding the usual stationarity bound, this is better read as failure to
separate environmental from spatial variation than as evidence of no relationship.

## Pre-registration and honest reporting

Stopping rules were declared in `docs/03_project_plan.md` *before* the analysis was
run. Rule 3 (sign reversal across grid scales) triggered, so all v1 results are
downgraded from confirmatory to **exploratory**. No model was re-specified in search
of significance.

The inverted-U structure is a **post hoc discovery**, not a pre-registered
prediction. It is therefore treated as a hypothesis to be tested on independent data
in v2, not as an established finding. The v2 pre-registration plan is in
[`docs/06_v2_roadmap.md`](docs/06_v2_roadmap.md).

Conditions that would revise these provisional findings are listed in
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
