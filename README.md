# 고인돌–고대 항해 위험도 상관관계 분석

전남 서남해안 고인돌 밀집 현상이 고대 해양 이동의 위험도와
연관되는지를 공간통계로 검정한다.

## 현재 상태

| 항목 | 상태 |
|---|---|
| 데이터 수집 파이프라인 | 동작 (OSM / 국가유산청 / Natural Earth) |
| 조사강도 편향 진단 | 완료 — **515배 편향 확인** |
| 위험도 지수 | 미구축 (ERA5·CMEMS 키 필요) |
| 회귀 분석 | 미착수 (GATE 0 대기) |

## 빠른 시작

```bash
conda env create -f environment.yml
conda activate dolmen

python src/acquire/khs_korea.py       # 국가유산청 지석묘 (키 불필요)
python src/acquire/osm_megaliths.py   # OSM 전세계 거석
python src/acquire/basemap.py         # Natural Earth 해안선
python src/features/survey_bias.py    # 편향 진단 — 먼저 읽을 것
```

## 먼저 읽어야 할 것

1. [`docs/00_hypothesis.md`](docs/00_hypothesis.md) — 원가설의 구조적 문제 4가지
2. [`docs/01_data_inventory.md`](docs/01_data_inventory.md) — 확보 자료와 편향 실측
3. [`docs/02_methodology.md`](docs/02_methodology.md) — 게이트 방식 분석 설계

## 핵심 경고

OSM 거석 자료는 유럽 탐지율 39.6%, 한국 0.077% 로 **515배 편향**되어 있다.
한반도가 세계 고인돌의 약 40%를 보유함에도 OSM에는 27건뿐이다.
**전지구 밀도 비교에 원자료를 사용하면 결론이 정반대로 나온다.**

## 다음 병목 (GATE 0)

전남 고인돌 **개체수** 자료. 국가유산청 지정자료는 "군(群)" 단위라
화순 지석묘군 1건 = 실제 596기다. 지자체 정밀지표조사 보고서를
`data/external/` 에 확보해야 H1 검정이 가능하다.

## 라이선스·출처

- OSM: ODbL 1.0 — © OpenStreetMap contributors
- 국가유산청: 공공누리
- Natural Earth: Public Domain
- 문헌: Schulz Paulsson (2019) PNAS 116(9):3460–3465
