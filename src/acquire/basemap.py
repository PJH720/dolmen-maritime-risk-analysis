"""Natural Earth 해안선/육지 폴리곤 다운로드 (연안 버퍼 분석 기반)."""
from __future__ import annotations
import sys, zipfile, io
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data" / "external"
URLS = {
    "ne_10m_coastline": "https://naciscdn.org/naturalearth/10m/physical/ne_10m_coastline.zip",
    "ne_10m_land":      "https://naciscdn.org/naturalearth/10m/physical/ne_10m_land.zip",
}
HEADERS = {"User-Agent": "dolmen-maritime-risk/0.1"}


def main() -> None:
    EXT.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        dest = EXT / name
        if (dest / f"{name}.shp").exists():
            print(f"[ne] {name} already present, skip")
            continue
        print(f"[ne] downloading {name} ...")
        r = requests.get(url, headers=HEADERS, timeout=300)
        r.raise_for_status()
        zipfile.ZipFile(io.BytesIO(r.content)).extractall(dest)
        print(f"[ne] extracted -> {dest}")


if __name__ == "__main__":
    sys.exit(main())
