"""
국가유산청(KHS) OpenAPI — 한국 지정 지석묘 수집.
인증키 불필요. 목록 응답에 위경도가 직접 포함됨.
"""
from __future__ import annotations
import sys, time
import xml.etree.ElementTree as ET
from pathlib import Path
import requests
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
LIST_URL = "https://www.khs.go.kr/cha/SearchKindOpenapiList.do"
HEADERS = {"User-Agent": "dolmen-maritime-risk/0.1 (academic research)"}
KEYWORDS = ["지석묘", "고인돌"]

FIELDS = ["ccbaMnm1", "ccbaMnm2", "ccmaName", "ccbaCtcdNm", "ccsiName",
          "ccbaKdcd", "ccbaCtcd", "ccbaAsno", "longitude", "latitude"]


def fetch_keyword(kw: str, page_unit: int = 100) -> list[dict]:
    out, page = [], 1
    while True:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=60,
                         params={"ccbaMnm1": kw, "pageIndex": page, "pageUnit": page_unit})
        r.raise_for_status()
        root = ET.fromstring(r.content)
        total = int(root.findtext("totalCnt") or 0)
        items = root.findall(".//item")
        if not items:
            break
        for it in items:
            rec = {f: (it.findtext(f) or "").strip() for f in FIELDS}
            rec["keyword"] = kw
            out.append(rec)
        print(f"[khs] '{kw}' page {page}: +{len(items)} (total {total})")
        if page * page_unit >= total:
            break
        page += 1
        time.sleep(0.4)
    return out


def main() -> None:
    INTERIM.mkdir(parents=True, exist_ok=True)
    rows = []
    for kw in KEYWORDS:
        rows += fetch_keyword(kw)

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["ccbaKdcd", "ccbaCtcd", "ccbaAsno"])
    for c in ("latitude", "longitude"):
        df[c] = pd.to_numeric(df[c], errors="coerce")

    valid = df.dropna(subset=["latitude", "longitude"])
    valid = valid[(valid.latitude != 0) & (valid.longitude != 0)]

    valid.to_parquet(INTERIM / "khs_dolmens.parquet", index=False)
    valid.to_csv(INTERIM / "khs_dolmens.csv", index=False)

    print(f"\n[khs] unique={len(df)}  with coords={len(valid)}")
    print("\n[khs] 시도별 분포:")
    print(valid["ccbaCtcdNm"].value_counts().to_string())


if __name__ == "__main__":
    sys.exit(main())
