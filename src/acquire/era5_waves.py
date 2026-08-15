"""
ERA5 유의파고(swh) 수집 — docs/05_limitations.md L1 해소용.

파고는 소형 목선 전복의 최직접 요인이며, 기존 위험도 지수에서
빠져 있던 성분이다. 이 스크립트 실행 후 marine_exposure.py 를
다시 돌리면 지수가 3성분(유속·수심경사·파고)으로 확장된다.

설계:
  - 계절별 대표월(1/4/7/10) × 다년(2015~2020) 6시간 간격
  - 산출: swh 평균 / p90 / p99 / 최대  (p90·p99가 위험도 핵심)
  - 절대값이 아닌 해역 간 상대 순위만 해석에 사용 (docs/05 L2)
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import xarray as xr
import cdsapi

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data" / "external"

AREA = [37.0, 123.5, 32.5, 128.5]          # N, W, S, E — 황해 남부+서남해안
YEARS = ["2017", "2018", "2019", "2020"]
MONTHS = ["01", "04", "07", "10"]           # 계절 대표
TIMES = ["00:00", "06:00", "12:00", "18:00"]
DAYS = [f"{d:02d}" for d in range(1, 32)]

# 주의: ERA5 single-levels 에 '10m_wind_speed' 는 없다 (MARS ambiguous 오류).
#       u/v 성분을 받아 speed 를 직접 계산한다.
VARS = [
    "significant_height_of_combined_wind_waves_and_swell",
    "mean_wave_period",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
]


def download() -> Path:
    raw = EXT / "era5_waves_raw.nc"
    if raw.exists():
        print(f"[era5] cached {raw.name} ({raw.stat().st_size:,} bytes)")
        return raw
    print("[era5] requesting ERA5 single-levels ...")
    c = cdsapi.Client()
    c.retrieve("reanalysis-era5-single-levels", {
        "product_type": ["reanalysis"],
        "variable": VARS,
        "year": YEARS, "month": MONTHS, "day": DAYS, "time": TIMES,
        "area": AREA,
        "data_format": "netcdf",
        "download_format": "unarchived",
    }, str(raw))
    print(f"[era5] downloaded {raw.stat().st_size:,} bytes")
    return raw


def _open_any(raw: Path) -> xr.Dataset:
    """CDS는 파고(wave)와 대기(oper)를 별도 스트림으로 나눠 ZIP 반환할 수 있다."""
    import zipfile, tempfile
    if not zipfile.is_zipfile(raw):
        return xr.open_dataset(raw)
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(raw) as z:
        names = [n for n in z.namelist() if n.endswith(".nc")]
        z.extractall(tmp)
    print(f"[era5] zip 내부 {len(names)} 스트림 병합: {names}")
    parts = [xr.open_dataset(tmp / n) for n in names]
    # 시간축 정렬 후 변수 병합
    return xr.merge(parts, compat="override", join="outer")


def summarise(raw: Path) -> Path:
    out = EXT / "era5_wave_stats.nc"
    if out.exists():
        print(f"[era5] cached {out.name}")
        return out
    ds = _open_any(raw)
    tdim = "valid_time" if "valid_time" in ds.dims else "time"
    print(f"[era5] dims={dict(ds.sizes)}  vars={list(ds.data_vars)}")

    swh = ds["swh"]
    res = {
        "swh_mean": swh.mean(tdim),
        "swh_p90": swh.quantile(0.90, dim=tdim).drop_vars("quantile"),
        "swh_p99": swh.quantile(0.99, dim=tdim).drop_vars("quantile"),
        "swh_max": swh.max(tdim),
    }
    if "mwp" in ds:
        res["mwp_mean"] = ds["mwp"].mean(tdim)
    if "u10" in ds and "v10" in ds:
        spd = np.sqrt(ds["u10"] ** 2 + ds["v10"] ** 2)
        res["wind_mean"] = spd.mean(tdim)
        res["wind_p90"] = spd.quantile(0.90, dim=tdim).drop_vars("quantile")

    o = xr.Dataset(res)
    ren = {}
    if "latitude" in o.coords: ren["latitude"] = "lat"
    if "longitude" in o.coords: ren["longitude"] = "lon"
    o = o.rename(ren)
    o.to_netcdf(out)
    print(f"[era5] saved {out.name}  {dict(o.sizes)}")
    return out


def main() -> None:
    EXT.mkdir(parents=True, exist_ok=True)
    raw = download()
    out = summarise(raw)
    ds = xr.open_dataset(out)
    print(f"\n[era5] {list(ds.data_vars)}")
    v = ds["swh_p90"].values
    print(f"[era5] swh_p90  유효셀 {np.isfinite(v).sum()}/{v.size}"
          f"  범위 {np.nanmin(v):.2f}~{np.nanmax(v):.2f} m")


if __name__ == "__main__":
    sys.exit(main())
