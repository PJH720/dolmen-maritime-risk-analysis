"""
조사강도(survey intensity) 편향 진단.

이 프로젝트의 사활이 걸린 스크립트.
OSM 원자료를 그대로 회귀에 넣으면 "한국은 고인돌이 거의 없다"는
사실과 정반대의 결론이 나온다. 그 크기를 정량화한다.

문헌 기준값
  - 한반도 고인돌: 약 35,000기 (세계 총량의 약 40%) — UNESCO/WHC
  - 유럽 거석기념물: 약 35,000기 — Schulz Paulsson (2019) PNAS
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
PROC = ROOT / "data" / "processed"

# 문헌 추정 실제 분포량 (출처는 docs/01_data_inventory.md 참조)
LITERATURE_TRUTH = {
    "EUROPE": 35_000,
    "KOREA": 35_000,
}

BOXES = {
    "KOREA":     (33.0, 39.0, 124.0, 132.0),
    "JAPAN":     (30.0, 46.0, 129.0, 146.0),
    "EUROPE":    (35.0, 72.0, -12.0, 40.0),
    "LEVANT_ME": (12.0, 42.0,  25.0, 63.0),
    "S_ASIA":    ( 5.0, 35.0,  68.0, 92.0),
    "SE_ASIA":   (-11.0, 23.0, 92.0, 141.0),
    "AFRICA":    (-36.0, 37.0, -18.0, 52.0),
}


def tag_region(lat: float, lon: float) -> str:
    for name, (s, n, w, e) in BOXES.items():
        if s <= lat <= n and w <= lon <= e:
            return name
    return "OTHER"


def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)
    osm = pd.read_parquet(INTERIM / "osm_megaliths.parquet")
    osm["region"] = [tag_region(a, b) for a, b in zip(osm.lat, osm.lon)]

    all_mega = osm.groupby("region").size().rename("osm_all_megaliths")
    dolmen = (osm[osm.megalith_type == "dolmen"]
              .groupby("region").size().rename("osm_dolmen"))

    tab = pd.concat([all_mega, dolmen], axis=1).fillna(0).astype(int)
    tab = tab.sort_values("osm_all_megaliths", ascending=False)

    tab["literature_est"] = tab.index.map(LITERATURE_TRUTH)
    tab["detection_rate_%"] = (
        tab["osm_all_megaliths"] / tab["literature_est"] * 100
    ).round(3)

    print("=" * 74)
    print("OSM 조사강도 편향 진단")
    print("=" * 74)
    print(tab.to_string())

    eu = tab.loc["EUROPE", "detection_rate_%"]
    kr = tab.loc["KOREA", "detection_rate_%"]
    ratio = eu / kr
    print("\n" + "=" * 74)
    print(f"  유럽 탐지율 : {eu:8.3f} %")
    print(f"  한국 탐지율 : {kr:8.3f} %")
    print(f"  편향 배율   : {ratio:8.1f} 배")
    print("=" * 74)
    print(f"""
[결론]
  OSM 원자료로 전지구 회귀를 돌리면 유럽이 한국보다 약 {ratio:.0f}배 과대대표된다.
  실제로는 한반도가 세계 고인돌의 약 40%를 보유한 최대 밀집지다.
  → 전지구 단일 회귀는 성립 불가. 아래 둘 중 하나를 택해야 한다.

  (A) 권역 내 분석(within-region): 조사강도가 균질한 단일 권역에서만 비교.
      전남 = 국가유산청 정밀지표조사 자료 기반. 이 프로젝트의 1차 경로.

  (B) 조사강도 오프셋 모형: 음이항 회귀에 log(조사강도)를 offset 으로 투입.
      log(E[count]) = beta*risk + ... + log(survey_effort)
      조사강도 대리변수: 발굴보고서 건수 / 도로밀도 / 지자체 조사예산.
""")
    tab.to_csv(PROC / "survey_bias_diagnostic.csv")
    print(f"saved -> {PROC / 'survey_bias_diagnostic.csv'}")


if __name__ == "__main__":
    main()
