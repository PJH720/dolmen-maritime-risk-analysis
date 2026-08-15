"""
황해–서남해안 해양 환경 데이터 수집 (인증키 불필요 경로만 사용).

  수심   : NOAA ETOPO 2022 (OPeNDAP)   — GEBCO WCS 다운 시 대체재
  해류   : HYCOM GLBy0.08 expt_93.0    — CMEMS 키 불필요 대체재
  파고   : ERA5 필요 (키 미설정)        — 현재 생략, docs/01 참조

시대 정합성: 두 자료 모두 현대 관측이다. 절대값이 아니라
             해역 간 '상대 순위'만 해석에 사용한다.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data" / "external"

# 분석 대상 해역: 황해 남부 + 한반도 서남해안
LAT = slice(32.5, 37.0)
LON = slice(123.5, 128.5)

ETOPO = ("https://www.ngdc.noaa.gov/thredds/dodsC/global/ETOPO2022/30s/"
         "30s_bed_elev_netcdf/ETOPO_2022_v1_30s_N90W180_bed.nc")
HYCOM = "https://tds.hycom.org/thredds/dodsC/GLBy0.08/expt_93.0/uv3z"


def get_bathymetry() -> Path:
    out = EXT / "etopo_yellowsea.nc"
    if out.exists():
        print(f"[bathy] cached {out.name}"); return out
    print("[bathy] opening ETOPO 2022 (30s) ...")
    ds = xr.open_dataset(ETOPO)
    latn = "lat" if "lat" in ds.coords else "latitude"
    lonn = "lon" if "lon" in ds.coords else "longitude"
    sub = ds.sel({latn: LAT, lonn: LON})
    var = [v for v in ds.data_vars if ds[v].ndim >= 2][0]
    sub = sub[[var]].rename({var: "elevation", latn: "lat", lonn: "lon"})
    sub.load()
    sub.to_netcdf(out)
    print(f"[bathy] saved {out.name}  shape={dict(sub.sizes)}")
    return out


def get_currents(n_days: int = 48) -> Path:
    out = EXT / "hycom_surface_currents.nc"
    if out.exists():
        print(f"[curr] cached {out.name}"); return out
    print("[curr] opening HYCOM GLBy0.08 ...")
    ds = xr.open_dataset(HYCOM, decode_times=False)
    ds = ds.sel(lat=LAT, lon=slice(123.5, 128.5))
    surf = ds.isel(depth=0)
    nt = surf.sizes["time"]
    step = max(1, nt // n_days)
    surf = surf.isel(time=slice(0, None, step))
    print(f"[curr] time steps {surf.sizes['time']} of {nt}")
    uv = surf[["water_u", "water_v"]].load()

    spd = np.sqrt(uv.water_u ** 2 + uv.water_v ** 2)
    res = xr.Dataset({
        "speed_mean": spd.mean("time"),
        "speed_p90": spd.quantile(0.90, dim="time").drop_vars("quantile"),
        "speed_max": spd.max("time"),
        "u_mean": uv.water_u.mean("time"),
        "v_mean": uv.water_v.mean("time"),
    })
    res.to_netcdf(out)
    print(f"[curr] saved {out.name}  shape={dict(res.sizes)}")
    return out


def main() -> None:
    EXT.mkdir(parents=True, exist_ok=True)
    b = get_bathymetry()
    c = get_currents()
    for p in (b, c):
        ds = xr.open_dataset(p)
        print(f"\n{p.name}: {list(ds.data_vars)}  {dict(ds.sizes)}")
        ds.close()


if __name__ == "__main__":
    sys.exit(main())
