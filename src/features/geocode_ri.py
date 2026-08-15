"""
리(里) 단위 지오코딩.

보고서에 좌표가 없으므로 행정지명 -> 좌표 변환이 필요하다.
전략: OSM Overpass 로 전남/전북/광주 권역의 지명 노드를 일괄 수집한 뒤
      (시군, 읍면, 리) 문자열 매칭. Nominatim 순차호출(690회)보다 빠르고 안정적.

정확도 한계: 리 중심점(centroid)이며 실제 유적 위치와 최대 수 km 오차.
             격자 5km 이상에서만 사용할 것. docs/03_results.md 참조.
"""
from __future__ import annotations
import json, re, sys, time
from pathlib import Path
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
RAW = ROOT / "data" / "raw"

ENDPOINTS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.osm.jp/api/interpreter",
]
HEADERS = {"User-Agent": "dolmen-maritime-risk/0.1 (academic)"}

# 전남·전북·광주 권역 bbox
BBOX = "33.8,125.0,36.3,128.0"

QUERY = f"""
[out:json][timeout:300];
(
  node["place"~"village|hamlet|suburb|neighbourhood|town|quarter"]["name"]({BBOX});
  way["place"~"village|hamlet|suburb|neighbourhood|town|quarter"]["name"]({BBOX});
  relation["boundary"="administrative"]["admin_level"~"^(7|8|9|10)$"]["name"]({BBOX});
);
out center tags;
"""


def fetch() -> dict:
    for ep in ENDPOINTS:
        try:
            print(f"[geo] {ep} ...", flush=True)
            r = requests.post(ep, data={"data": QUERY}, headers=HEADERS, timeout=600)
            if r.status_code == 200 and r.content[:1] in (b"{", b"\n", b" "):
                print(f"[geo] OK {len(r.content):,} bytes")
                return r.json()
            print(f"[geo]   HTTP {r.status_code}")
        except Exception as e:
            print(f"[geo]   {type(e).__name__}: {str(e)[:100]}")
        time.sleep(3)
    raise RuntimeError("Overpass mirrors exhausted")


def build_gazetteer(payload: dict) -> pd.DataFrame:
    rows = []
    for el in payload.get("elements", []):
        if el["type"] == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            c = el.get("center") or {}
            lat, lon = c.get("lat"), c.get("lon")
        if lat is None:
            continue
        t = el.get("tags", {})
        nm = (t.get("name") or "").strip()
        if not nm:
            continue
        rows.append({"name": nm, "lat": lat, "lon": lon,
                     "place": t.get("place", ""),
                     "admin_level": t.get("admin_level", ""),
                     "full": t.get("name:ko") or nm})
    g = pd.DataFrame(rows).drop_duplicates(subset=["name", "lat", "lon"])
    return g


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    cache = RAW / "osm_gazetteer_kr.json"
    if cache.exists():
        payload = json.loads(cache.read_text())
        print(f"[geo] cache hit ({cache.stat().st_size:,} bytes)")
    else:
        payload = fetch()
        cache.write_text(json.dumps(payload))

    gaz = build_gazetteer(payload)
    print(f"[geo] gazetteer entries: {len(gaz):,}")
    gaz.to_parquet(INTERIM / "gazetteer_kr.parquet", index=False)

    sites = pd.read_parquet(INTERIM / "ysg_sites_raw.parquet")

    # 매칭 우선순위: 읍면+리 동시 일치 > 리 단독 일치 > 읍면 일치
    by_name: dict[str, list] = {}
    for r in gaz.itertuples():
        by_name.setdefault(r.name, []).append((r.lat, r.lon, r.admin_level, r.place))

    def match(row):
        ri, em, sg = row.ri, row.eupmyeon, row.sigungu
        # 1) 리 이름 직접
        if isinstance(ri, str) and ri in by_name:
            cands = by_name[ri]
            return cands[0][0], cands[0][1], "ri"
        # 2) 리에서 '리' 제거한 마을명
        if isinstance(ri, str):
            stem = ri[:-1]
            if stem in by_name:
                c = by_name[stem][0]
                return c[0], c[1], "ri_stem"
        # 3) 읍면 중심
        if isinstance(em, str) and em in by_name:
            c = by_name[em][0]
            return c[0], c[1], "eupmyeon"
        # 4) 시군 중심
        if isinstance(sg, str) and sg in by_name:
            c = by_name[sg][0]
            return c[0], c[1], "sigungu"
        return None, None, "none"

    out = sites.apply(lambda r: pd.Series(match(r), index=["lat", "lon", "geo_level"]), axis=1)
    sites = pd.concat([sites, out], axis=1)
    sites.to_parquet(INTERIM / "ysg_sites_geo.parquet", index=False)

    print("\n[geo] 매칭 수준 분포:")
    print(sites.geo_level.value_counts().to_string())
    ok = sites.dropna(subset=["lat"])
    print(f"\n[geo] 좌표 확보 {len(ok)}/{len(sites)} ({len(ok)/len(sites)*100:.1f}%)")
    prec = ok[ok.geo_level.isin(["ri", "ri_stem"])]
    print(f"[geo] 리 단위 정밀 매칭 {len(prec)} ({len(prec)/len(sites)*100:.1f}%)")
    print(f"[geo] 정밀매칭 기수 합계 {prec.n_recorded.sum():,.0f}")


if __name__ == "__main__":
    sys.exit(main())
