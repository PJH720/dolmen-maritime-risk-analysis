# 03. 프로젝트 완성 계획 (A–Z)

작성 2026-08-16. 각 Phase는 게이트다. 통과 실패 시 다음으로 가지 않고 가설을 낮춘다.

## 전제 조건 실측 (계획 수립 시점)

| 자원 | 상태 |
|---|---|
| 『영산강유역 지석묘』Ⅴ 1~5권 | 확보 (3,175면, 텍스트 추출 가능) |
| 문화유적분포지도-순천시 | 확보 (295면, **스캔본 — 폰트 0개**, OCR 필요) |
| 전국해양문화학자대회 자료집 | 확보 (텍스트 추출 가능) |
| ERA5 파고 | **미확보** — `.cdsapirc` 2개 모두 `YOUR_PERSONAL_ACCESS_TOKEN` 플레이스홀더 |
| ETOPO 2022 수심 | 확보 (OPeNDAP, 키 불필요) |
| HYCOM 표층해류 | 확보 (OPeNDAP, 키 불필요) |

**ERA5 부재의 영향**: 위험도 지수에서 파고 성분이 빠진다.
수심경사·해류속도 2성분만으로 구성하며, 이는 `docs/05_limitations.md`에
1급 한계로 명시한다. 키 설정 후 `src/acquire/era5_waves.py` 실행하면
지수가 3성분으로 자동 확장되도록 설계한다.

---

## Phase A — 자료 구조화 (완료)

- A1. PDF 5권 텍스트 추출 (`pdftotext`, 읽기순서 모드)
- A2. 8필드 정형 파서 (`src/features/parse_ysg.py`)
- A3. 리(里) 단위 지오코딩 (`src/features/geocode_ri.py`)

산출: 유적 1,638건 / 기록 7,027기 / 좌표 확보 1,392건(85.0%)

## Phase B — 격자화와 공변량 구축

- B1. 5km 격자 생성 (EPSG:5179 한국 중부원점 TM)
  - 리 중심점 오차가 수 km이므로 5km 미만 격자는 부적절
- B2. 격자별 지석묘 기수 집계 (`n_recorded` 합)
- B3. 공변량
  - `dist_coast` : Natural Earth 해안선까지 최단거리
  - `bathy_grad` : ETOPO 수심 경사 (연안 100km 내 평균)
  - `curr_speed` : HYCOM 표층유속 p90
  - `landform`   : 보고서 입지 분류 (산록/구릉/평지) — **보고서 고유 강점**
  - `survey_effort` : 격자 내 조사 레코드 수 (offset)

## Phase C — 점패턴 (GATE 1)

- C1. Moran's I (KNN k=8, row-standardized)
- C2. 결과: I>0 & p<0.05 → 군집 확인, 아니면 중단

## Phase D — 회귀 (GATE 2·3) ★ 핵심

- D1. 음이항 회귀, `log(survey_effort)` offset
- D2. 모형 3종 비교
  - M1 기저   : `~ dist_coast`
  - M2 지형   : `~ dist_coast + landform + elev`
  - M3 위험도 : `~ dist_coast + landform + elev + risk_score`
- D3. **판정**: M2→M3 에서 `beta_risk` 가 유의한가?
  - 유의하지 않으면 → 가설 기각. 정직하게 보고한다.
- D4. 공간 자기상관 잔존 시 `spreg.GM_Lag` 로 이행

## Phase E — 표류 시뮬레이션 (GATE 4)

- E1. OpenDrift + HYCOM reader
- E2. 산둥반도·저장성 연안 다지점 입자 방출
- E3. 해안 구역별 상륙확률 산출
- E4. 상륙확률 ↔ 배후지 기수 밀도 상관

## Phase F — 산출물

- F1. 그림 4종 (분포도 / 위험도면 / 회귀계수 / 표류궤적)
- F2. `docs/04_results.md` 결과 보고
- F3. `docs/05_limitations.md` 한계 명세
- F4. GitHub push

---

## 중단 조건 (사전 선언)

아래 중 하나라도 해당하면 그 지점에서 정지하고 결과를 그대로 보고한다.
유의한 결과가 나올 때까지 격자 크기·변수 조합을 바꾸지 않는다.

1. GATE 1 에서 CSR 기각 실패
2. M2 가 M3 와 통계적으로 구분되지 않음 (LR test p>0.05)
3. 격자 크기 5/10/20km 민감도에서 부호가 뒤집힘

3번이 발생하면 MAUP 취약으로 판정하고 **전 결과를 탐색적**으로 강등한다.
