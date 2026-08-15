"""
OSM Overpass API 전세계 거석 유적 수집.

megalith_type 태그 기반. 검증 결과 14,086건 (dolmen 4,582).
!! 조사강도 편향 심각 — src/features/survey_bias.py 로 반드시 보정할 것.
"""
from __future__ import annotations
import json, time, sys
from pathlib import Path
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"

ENDPOINTS = [
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.osm.jp/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
HEADERS = {"User-Agent": "dolmen-maritime-risk/0.1 (academic research)"}

QUERY = """
[out:json][timeout:300];
(
  nwr["megalith_type"];
  nwr["historic"="archaeological_site"]["site_type"="megalith"];
);
out center tags;
"""


def fetch(query: str = QUERY) -> dict:
    last = None
    for ep in ENDPOINTS:
        try:
            print(f"[osm] trying {ep} ...", flush=True)
            r = requests.post(ep, data={"data": query}, headers=HEADERS, timeout=600)
            if r.status_code == 200 and r.content[:1] in (b"{", b"\n", b" "):
                print(f"[osm] OK {len(r.content):,} bytes")
                return r.json()
            print(f"[osm]   -> HTTP {r.status_code}")
            last = f"HTTP {r.status_code}"
        except Exception as e:
            print(f"[osm]   -> {type(e).__name__}: {e}")
            last = str(e)
        time.sleep(3)
    raise RuntimeError(f"all Overpass mirrors failed: {last}")


def to_frame(payload: dict) -> pd.DataFrame:
    rows = []
    for el in payload.get("elements", []):
        if el["type"] == "node":
            lat, lon = el.get("lat"), el.get("lon")
        else:
            c = el.get("center") or {}
            lat, lon = c.get("lat"), c.get("lon")
        if lat is None or lon is None:
            continue
        t = el.get("tags", {})
        rows.append({
            "osm_id": f"{el['type']}/{el['id']}",
            "lat": lat, "lon": lon,
            "megalith_type": (t.get("megalith_type") or "").lower(),
            "site_type": t.get("site_type", ""),
            "historic": t.get("historic", ""),
            "name": t.get("name", ""),
            "wikidata": t.get("wikidata", ""),
        })
    return pd.DataFrame(rows)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    INTERIM.mkdir(parents=True, exist_ok=True)

    payload = fetch()
    (RAW / "osm_megaliths_raw.json").write_text(json.dumps(payload))

    df = to_frame(payload)
    df.to_parquet(INTERIM / "osm_megaliths.parquet", index=False)
    df.to_csv(INTERIM / "osm_megaliths.csv", index=False)

    print(f"\n[osm] saved {len(df):,} features")
    print(df["megalith_type"].value_counts().head(12).to_string())
    dol = df[df.megalith_type == "dolmen"]
    print(f"\n[osm] dolmen only: {len(dol):,}")
    kr = dol[(dol.lat.between(33, 39)) & (dol.lon.between(124, 132))]
    print(f"[osm] dolmen in Korea bbox: {len(kr)}  <-- 실제 3~4만기 대비 극단적 과소")


if __name__ == "__main__":
    sys.exit(main())
