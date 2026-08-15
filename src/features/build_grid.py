"""
Phase B: 5km 격자 생성 및 공변량 결합.

투영: EPSG:5179 (Korea 2000 / Unified CS) — 거리 계산 정확도 확보.
격자 5km: 리(里) 중심점 지오코딩 오차(수 km)를 고려한 하한.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import xarray as xr
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[2]
INTERIM = ROOT / "data" / "interim"
EXT = ROOT / "data" / "external"
PROC = ROOT / "data" / "processed"

CRS_M = 5179
CELL = 5_000  # meters


def load_sites() -> gpd.GeoDataFrame:
    df = pd.read_parquet(INTERIM / "ysg_sites_geo.parquet")
    df = df.dropna(subset=["lat", "lon"])
    df = df[df.geo_level.isin(["ri", "ri_stem"])]        # 리 단위 정밀 매칭만
    df["n_recorded"] = df["n_recorded"].fillna(1)         # 미파싱은 최소 1기로
    g = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326)
    return g.to_crs(CRS_M)


def make_grid(sites: gpd.GeoDataFrame, pad: int = 20_000) -> gpd.GeoDataFrame:
    xmin, ymin, xmax, ymax = sites.total_bounds
    xmin, ymin = np.floor((xmin - pad) / CELL) * CELL, np.floor((ymin - pad) / CELL) * CELL
    xmax, ymax = np.ceil((xmax + pad) / CELL) * CELL, np.ceil((ymax + pad) / CELL) * CELL
    xs = np.arange(xmin, xmax, CELL)
    ys = np.arange(ymin, ymax, CELL)
    cells = [box(x, y, x + CELL, y + CELL) for x in xs for y in ys]
    g = gpd.GeoDataFrame({"cell_id": range(len(cells))}, geometry=cells, crs=CRS_M)
    g["ctr_x"] = g.geometry.centroid.x
    g["ctr_y"] = g.geometry.centroid.y
    return g


def add_coast_distance(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    coast = gpd.read_file(EXT / "ne_10m_coastline" / "ne_10m_coastline.shp")
    coast = coast.cx[123:130, 32:38].to_crs(CRS_M)
    union = coast.union_all()
    cent = gpd.GeoSeries(gpd.points_from_xy(grid["ctr_x"], grid["ctr_y"]), crs=CRS_M)
    grid["dist_coast_km"] = cent.distance(union) / 1000.0
    return grid


def sample_raster(grid: gpd.GeoDataFrame, ds: xr.Dataset, var: str, name: str) -> gpd.GeoDataFrame:
    pts = gpd.GeoSeries(gpd.points_from_xy(grid["ctr_x"], grid["ctr_y"]), crs=CRS_M).to_crs(4326)
    la = xr.DataArray(pts.y.values, dims="p")
    lo = xr.DataArray(pts.x.values, dims="p")
    v = ds[var].interp(lat=la, lon=lo, method="nearest").values
    grid[name] = np.asarray(v, dtype=float)
    return grid


def add_marine_covariates(grid: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    bat = xr.open_dataset(EXT / "etopo_yellowsea.nc")
    grid = sample_raster(grid, bat, "elevation", "elev_m")

    # 수심 경사: 해저 지형 급변도 (연안 항해 위험 프록시)
    el = bat["elevation"]
    gy, gx = np.gradient(el.values.astype(float))
    grad = np.hypot(gx, gy)
    bat2 = xr.Dataset({"bathy_grad": (("lat", "lon"), grad)},
                      coords={"lat": bat.lat, "lon": bat.lon})
    grid = sample_raster(grid, bat2, "bathy_grad", "bathy_grad")

    cur = xr.open_dataset(EXT / "hycom_surface_currents.nc")
    for v, n in [("speed_p90", "curr_p90"), ("speed_mean", "curr_mean")]:
        grid = sample_raster(grid, cur, v, n)
    return grid


def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)
    sites = load_sites()
    print(f"[grid] sites(리 정밀) = {len(sites)}, 기수합 = {sites.n_recorded.sum():,.0f}")

    grid = make_grid(sites)
    print(f"[grid] cells = {len(grid):,} ({CELL/1000:.0f}km)")

    j = gpd.sjoin(sites, grid[["cell_id", "geometry"]], how="left", predicate="within")
    agg = j.groupby("cell_id").agg(
        n_dolmen=("n_recorded", "sum"),
        n_sites=("site_name", "size"),
        n_extant=("n_extant", "sum"),
    ).reset_index()

    # 입지 분류 -> 격자 대표값(최빈)
    lf = (j[j.landform != ""].groupby("cell_id")["landform"]
          .agg(lambda s: s.value_counts().idxmax()).rename("landform_mode").reset_index())

    grid = grid.merge(agg, on="cell_id", how="left").merge(lf, on="cell_id", how="left")
    grid[["n_dolmen", "n_sites", "n_extant"]] = grid[["n_dolmen", "n_sites", "n_extant"]].fillna(0)

    grid = add_coast_distance(grid)
    grid = add_marine_covariates(grid)

    # 육지 격자만 유지 (유적은 육상)
    land = grid[grid.elev_m > -5].copy()
    print(f"[grid] land cells = {len(land):,}")

    # 분석 대상: 조사가 실제로 수행된 권역으로 한정 (조사강도 통제)
    occupied = land[land.n_sites > 0]
    print(f"[grid] cells with sites = {len(occupied):,}")
    print(f"[grid] dolmen total in grid = {land.n_dolmen.sum():,.0f}")

    land.to_parquet(PROC / "grid_5km.parquet")
    land.drop(columns="geometry").to_csv(PROC / "grid_5km.csv", index=False)

    print("\n[grid] 요약 통계:")
    print(land[["n_dolmen", "dist_coast_km", "elev_m", "bathy_grad",
                "curr_p90"]].describe().round(3).to_string())
    print("\n[grid] 지석묘 보유 격자 상위 8:")
    print(land.nlargest(8, "n_dolmen")[
        ["cell_id", "n_dolmen", "n_sites", "dist_coast_km", "elev_m", "landform_mode"]
    ].to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
