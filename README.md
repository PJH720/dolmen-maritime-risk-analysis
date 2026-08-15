# 고인돌–고대 항해 위험도 상관관계 분석

영산강유역 고인돌 밀집이 고대 해양 이동의 위험도와 연관되는지
공간통계로 검정한 프로젝트.

## 결론

> **가설 기각.** 공간자기상관을 보정하면 해양 위험도 변수의 효과가
> 전부 소멸하고 부호까지 뒤집힌다. 영산강유역 지석묘 분포는
> 인접 해역의 물리적 위험도가 아니라 **공간적 군집 그 자체**로 설명된다.

ERA5 유의파고를 포함한 위험도 4성분 전부에 대해 성립한다.

| 변수 | 비공간 OLS | 공간시차 GM_Lag |
|---|---|---|
| 연안거리 | −0.307 (p<0.0001) | +0.056 (p=0.321) |
| 인접해역 유속 p90 | +0.146 (p=0.0001) | −0.071 (p=0.062) |
| 인접해역 수심경사 | −0.200 (p<0.0001) | +0.007 (p=0.851) |
| 인접해역 수심 | −0.293 (p<0.0001) | +0.059 (p=0.272) |
| 인접해역 유의파고 p90 | −0.139 (p=0.0020) | +0.021 (p=0.604) |
| **공간시차 ρ** | — | **+1.184 (p<0.0001)** |

추가로, **파고 계수는 비공간 모형에서조차 음수**다. 파고가 높은 해역에
인접할수록 지석묘가 적다는 뜻으로, 원가설이 예측한 방향과 반대다.

![계수 비교](reports/figures/fig2_coefficients.png)

## 데이터

| 소스 | 규모 | 확보 |
|---|---|---|
| 『영산강유역 지석묘』Ⅴ 1~5권 | 3,175면 → 유적 1,638건 / 7,027기 | 파싱 완료 |
| 국가유산청 OpenAPI | 지정 지석묘 169건 | 키 불필요 |
| OSM Overpass 거석 | 14,105건 | 키 불필요 |
| NOAA ETOPO 2022 수심 | 30초 격자 | 키 불필요 |
| HYCOM GLBy0.08 해류 | 표층 49시점 | 키 불필요 |
| ERA5 유의파고 | 2017–2020 · 1,968시점 | 확보 (CDS 키) |

## 실행

```bash
conda env create -f environment.yml && conda activate dolmen

make data      # 1차 수집 (OSM / 국가유산청 / Natural Earth)
make ocean     # ETOPO 수심 + HYCOM 해류 + ERA5 파고
make parse     # PDF 5권 파싱 + 리 단위 지오코딩
make grid      # 5km 격자 + 해양노출 지수
make model     # 음이항 회귀 + 공간회귀
make figures   # 그림 4종
```

원본 PDF(약 1.3GB)는 `.gitignore` 대상이다. `data/external/` 에 직접 배치할 것.

## 문서

| 문서 | 내용 |
|---|---|
| [00_hypothesis](docs/00_hypothesis.md) | 원가설의 구조적 문제 4가지, 재정식화 |
| [01_data_inventory](docs/01_data_inventory.md) | 자료 실측, **OSM 515배 편향** |
| [02_methodology](docs/02_methodology.md) | 게이트 방식 설계 |
| [03_project_plan](docs/03_project_plan.md) | A–Z 계획, 사전 중단조건 |
| [04_results](docs/04_results.md) | 결과 전문 |
| [05_limitations](docs/05_limitations.md) | 한계 (등급별) |

## 방법론적 발견 3가지

1. **OSM 조사강도 515배 편향** — 유럽 탐지율 39.6% vs 한국 0.077%.
   한반도가 세계 고인돌의 약 40%를 보유함에도 OSM에는 27건뿐이다.
   원자료로 전지구 회귀를 돌리면 결론이 정반대로 나온다.

2. **지정건수 ≠ 개체수** — 국가유산청 지정 단위는 "군(群)"이라
   화순 지석묘군 1건이 실제 596기다. 개체수는 지표조사 보고서에만 있다.

3. **공간자기상관 미보정의 위험** — 비공간 모형에서 p<0.0001로 나온
   해양 효과 3개가 공간보정 후 전부 소멸·반전했다. 이 프로젝트의 핵심 교훈이다.

## 출처

- 『영산강유역 지석묘』Ⅴ (전남 지표조사 보고서)
- 국가유산청 국가유산포털 OpenAPI (공공누리)
- OpenStreetMap contributors (ODbL 1.0)
- NOAA NCEI ETOPO 2022 / HYCOM Consortium GLBy0.08
- Natural Earth (Public Domain)
- Schulz Paulsson, B. (2019) *PNAS* 116(9):3460–3465
- UNESCO WHC #977 Gochang, Hwasun and Ganghwa Dolmen Sites
