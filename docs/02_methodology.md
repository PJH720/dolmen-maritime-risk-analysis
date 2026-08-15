# 02. 방법론

## 분석 순서 — 게이트 방식

각 단계는 **게이트**다. 통과 못 하면 다음으로 가지 않고 가설을 수정한다.
전지구 분석부터 시작하면 안 된다. 실패 비용이 너무 크다.

```
GATE 0  전남 개체수 자료 확보          ← 없으면 프로젝트 중단
   ↓
GATE 1  점패턴 분석: 군집이 존재하는가?
   ↓  (Ripley K, Moran's I)
GATE 2  연안거리만으로 밀도가 설명되는가?
   ↓  (설명된다면 → 위험도 가설은 잉여. 정직하게 보고)
GATE 3  연안거리 통제 후 위험도 계수가 유의한가?  ← 핵심
   ↓
GATE 4  OpenDrift 표류 상륙확률과 대응하는가?
   ↓
GATE 5  타 권역(유럽)에서 재현되는가?  (탐색적)
```

## GATE 1 — 점패턴

```python
from pointpats import ripley
from esda.moran import Moran
from libpysal.weights import KNN

w = KNN.from_dataframe(grid, k=8); w.transform = "r"
mi = Moran(grid["dolmen_count"], w)
# mi.I > 0 & mi.p_sim < 0.05 → 공간 군집 확인
```

CSR(완전공간랜덤) 기각이 안 되면 이후 분석은 무의미하다.

## GATE 2·3 — 회귀 설계

**모형은 OLS가 아니다.** 종속변수가 계수(count)이고 과산포가 심하다.

```
음이항 회귀 + 공간 오차항

log E[y_i] = b0 + b1·risk_i + b2·dist_coast_i
             + b3·pop_density_i + b4·slope_i + b5·soil_i
             + log(survey_effort_i)          ← offset
```

- `offset` 항이 조사강도 515배 편향을 흡수한다. **생략 불가.**
- 공간 자기상관 잔존 시 `spreg.GM_Lag` 또는 `GM_Error` 로 이행.
- **b1 의 부호와 유의성이 이 프로젝트의 결론 전부다.**

## 위험도 지수 구성 (고인돌과 독립적으로 사전 정의)

| 성분 | 자료 | 방향 |
|---|---|---|
| 표층 해류 속도 | HYCOM GLBy0.08 | + (빠를수록 위험) |
| 유의파고 P90 | ERA5 `swh` | + |
| 조석 진폭 | FES2014 / 조위관측 | + |
| 수심 급변도 | GEBCO 경사 | + |
| 안개 일수 | ERA5 시정 | + |

정규화 후 PCA 제1주성분을 `risk_score` 로 사용.
가중치를 임의로 정하면 연구자 자유도(researcher DoF)가 커진다.
**PCA 또는 사전등록된 고정 가중치 중 택일.**

## GATE 4 — OpenDrift 표류 시뮬레이션

```python
from opendrift.models.oceandrift import OceanDrift

o = OceanDrift()
o.add_readers_from_list([
    "https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0"
])
# 산둥반도·저장성 연안 다수 지점에서 입자 방출
o.seed_elements(lon=..., lat=..., number=5000, time=...)
o.run(duration=timedelta(days=30))
```

산출물:
1. 해안 구역별 **상륙확률** → 배후지 고인돌 밀도와 대응
2. 30일 내 미상륙률 = **표류 사망 프록시**
3. 계절별(춘·하·추·동) 분리 — 몬순 반전 효과

주의: HYCOM은 1994년 이후다. 절대 확률이 아닌
**해안 구역 간 상대 순위**만 해석에 사용한다.

## 사전등록 (권장)

GATE 3 실행 **전에** 아래를 고정하고 OSF 등에 기록:
- risk_score 가중치
- 통제변수 목록
- 유의수준
- 격자 크기

사후에 격자 크기를 바꿔가며 p<0.05 를 찾으면
MAUP(가변공간단위문제)를 이용한 p-hacking 이 된다.
격자 크기 민감도 분석은 **모두 보고**한다.

## 결과가 음(陰)일 때

`b1` 이 유의하지 않을 가능성이 실제로 높다.
그 경우에도 논문이 된다:

> "전남 고인돌 밀집은 해양 위험도가 아니라
>  하천 유역 농경 적지 분포로 더 잘 설명된다."

가설 기각도 결과다. 유의한 결과가 나올 때까지 모형을 바꾸는 것이
이 프로젝트에서 가장 경계해야 할 실패 양식이다.
