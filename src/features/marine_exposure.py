"""
해양 노출 지수 (marine exposure index).

설계 수정 사유:
  해류·수심경사는 해상에만 존재한다. 내륙 40km 격자에서 유속을 뽑으면 NaN 이다.
  실제로 의미 있는 것은 "그 지점에 인접한 바다가 얼마나 위험한가" 이다.

  -> 각 육상 격자에 대해 최근접 해양 지점을 찾고, 그 지점의
     유속 p90 / 수심경사 / 수심을 부여한다.

이것은 '연안 접근성'과 '해양 위험도'를 분리하기 위한 조작화다.
  dist_coast_km : 바다까지 얼마나 가까운가 (접근성)
  marine_*      : 그 바다가 얼마나 험한가   (위험도)
두 변수를 동시에 넣어야 P2(경쟁가설) 문제를 검정할 수 있다.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "data" / "external"
PROC = ROOT / "data" / "processed"
CRS_M = 5179


def marine_points() -> pd.DataFrame:
    """HYCOM 격자에서 유효 해양 지점 추출 + ETOPO 수심/경사 결합."""
    cur = xr.open_dataset(EXT / "hycom_surface_currents.nc")
    df = cur[["speed_p90", "speed_mean"]].to_dataframe().reset_index().dropna()

    bat = xr.open_dataset(EXT / "etopo_yellowsea.nc")
    el = bat["elevation"]
    gy, gx = np.gradient(el.values.astype(float))
    grad = xr.DataArray(np.hypot(gx, gy), coords={"lat": bat.lat, "lon": bat.lon},
                        dims=("lat", "lon"))

    la = xr.DataArray(df.lat.values, dims="p")
    lo = xr.DataArray(df.lon.values, dims="p")
    df["depth_m"] = -el.interp(lat=la, lon=lo, method="nearest").values
    df["sea_grad"] = grad.interp(lat=la, lon=lo, method="nearest").values
    df = df[df.depth_m > 0]                       # 실제 바다만
    return df.reset_index(drop=True)


def era5_points() -> pd.DataFrame:
    """ERA5 유의파고 유효 해양셀 추출 (육상은 NaN)."""
    f = EXT / "era5_wave_stats.nc"
    if not f.exists():
        print("[marine] ERA5 없음 — 파고 성분 제외")
        return pd.DataFrame()
    ds = xr.open_dataset(f)
    cols = [c for c in ["swh_p90", "swh_p99", "swh_mean", "wind_p90", "mwp_mean"]
            if c in ds.data_vars]
    df = ds[cols].to_dataframe().reset_index().dropna(subset=["swh_p90"])
    return df.reset_index(drop=True)


def main() -> None:
    grid = gpd.read_parquet(PROC / "grid_5km.parquet")
    sea = marine_points()
    print(f"[marine] 유효 해양 지점 = {len(sea):,}")
    print(f"[marine] 수심 범위 {sea.depth_m.min():.0f}~{sea.depth_m.max():.0f} m")

    # 해양점을 투영좌표로
    sea_g = gpd.GeoDataFrame(sea, geometry=gpd.points_from_xy(sea.lon, sea.lat),
                             crs=4326).to_crs(CRS_M)
    sxy = np.c_[sea_g.geometry.x, sea_g.geometry.y]
    tree = cKDTree(sxy)

    gxy = np.c_[grid["ctr_x"].values, grid["ctr_y"].values]
    dist, idx = tree.query(gxy, k=1)

    grid["marine_dist_km"] = dist / 1000.0
    grid["marine_curr_p90"] = sea_g["speed_p90"].values[idx]
    grid["marine_curr_mean"] = sea_g["speed_mean"].values[idx]
    grid["marine_depth"] = sea_g["depth_m"].values[idx]
    grid["marine_grad"] = sea_g["sea_grad"].values[idx]

    # ---- ERA5 파고: 최근접 유효 해양셀 ----
    wav = era5_points()
    if len(wav):
        lonc = "lon" if "lon" in wav.columns else "longitude"
        latc = "lat" if "lat" in wav.columns else "latitude"
        wg = gpd.GeoDataFrame(wav, geometry=gpd.points_from_xy(wav[lonc], wav[latc]),
                              crs=4326).to_crs(CRS_M)
        wtree = cKDTree(np.c_[wg.geometry.x, wg.geometry.y])
        wd, wi = wtree.query(gxy, k=1)
        grid["wave_dist_km"] = wd / 1000.0
        for c in ["swh_p90", "swh_p99", "swh_mean", "wind_p90"]:
            if c in wg.columns:
                grid["marine_" + c] = wg[c].values[wi]
        print(f"[marine] ERA5 유효 해양셀 = {len(wav)}, "
              f"최근접거리 중앙값 {np.median(wd)/1000:.1f} km")
        print(f"[marine] swh_p90 범위 {grid['marine_swh_p90'].min():.2f}"
              f"~{grid['marine_swh_p90'].max():.2f} m")

    # 위험도 지수: 표준화 후 PCA 제1주성분 (임의 가중 회피)
    cols = ["marine_curr_p90", "marine_grad"]
    if "marine_swh_p90" in grid.columns:
        cols.append("marine_swh_p90")
    X = grid[cols].astype(float)
    Xz = (X - X.mean()) / X.std(ddof=0)
    U, S, Vt = np.linalg.svd(Xz.values - Xz.values.mean(0), full_matrices=False)
    pc1 = Xz.values @ Vt[0]
    if np.corrcoef(pc1, grid["marine_curr_p90"])[0, 1] < 0:
        pc1 = -pc1                                 # 유속 증가 = 위험 증가 방향 고정
    grid["risk_score"] = pc1
    ev = (S ** 2) / (S ** 2).sum()

    print(f"[marine] PCA 성분 = {cols}")
    print(f"[marine] 적재량 PC1 = {dict(zip(cols, Vt[0].round(3)))}")
    print(f"[marine] 설명분산 PC1 = {ev[0]*100:.1f}%")
    print(f"[marine] risk_score  mean={grid.risk_score.mean():.3f} sd={grid.risk_score.std():.3f}")
    print(f"[marine] NaN 잔존: {grid[cols + ['risk_score']].isna().sum().to_dict()}")

    grid.to_parquet(PROC / "grid_5km_marine.parquet")
    print(f"\n[marine] saved grid_5km_marine.parquet  ({len(grid):,} cells)")

    occ = grid[grid.n_sites > 0]
    print("\n[marine] 지석묘 보유 격자의 상관(피어슨):")
    corr_cols = ["dist_coast_km", "marine_curr_p90", "marine_grad", "risk_score", "elev_m"]
    if "marine_swh_p90" in grid.columns:
        corr_cols.insert(3, "marine_swh_p90")
    for c in corr_cols:
        r = np.corrcoef(occ["n_dolmen"], occ[c])[0, 1]
        print(f"   n_dolmen ~ {c:18s} r = {r:+.3f}")


if __name__ == "__main__":
    sys.exit(main())
