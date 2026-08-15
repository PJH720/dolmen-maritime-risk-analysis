"""
공간 자기상관 보정 + 진단.

M3 잔차 Moran's I = +0.099 (p=0.001) 로 공간구조가 남았다.
비공간 GLM 의 표준오차는 과소추정(anti-conservative)이므로
공간회귀로 재추정하고, 계수 유의성이 유지되는지 확인한다.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import statsmodels.api as sm
from libpysal.weights import KNN
from esda.moran import Moran
from spreg import GM_Lag, OLS
from statsmodels.stats.outliers_influence import variance_inflation_factor as vif

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
REP = ROOT / "reports"

XCOLS = ["dist_coast_km", "elev_m", "marine_curr_p90", "marine_grad", "marine_depth",
         "marine_swh_p90"]


def main() -> None:
    d = pd.read_csv(PROC / "analysis_table.csv")
    global XCOLS
    XCOLS = [c for c in XCOLS if c in d.columns]
    print(f"[sp] cells = {len(d)} | predictors = {XCOLS}")

    print("\n" + "=" * 66)
    print("공선성 진단")
    print("=" * 66)
    print(d[XCOLS].corr().round(3).to_string())
    Z = d[[c + "_z" for c in XCOLS]].values
    Xv = sm.add_constant(Z)
    print("\n  VIF:", {c: round(vif(Xv, i + 1), 2) for i, c in enumerate(XCOLS)})

    # log(count+1) 변환 후 공간시차 모형 (spreg 는 가우시안 기반)
    y = np.log1p(d["y"].values).reshape(-1, 1)
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(d["ctr_x"], d["ctr_y"]), crs=5179)
    w = KNN.from_dataframe(pts, k=8); w.transform = "r"

    print("\n" + "=" * 66)
    print("비공간 OLS  vs  공간시차 GM_Lag   (종속: log(기수+1))")
    print("=" * 66)
    ols = OLS(y, Z, w=w, spat_diag=True, name_y="log_dolmen", name_x=XCOLS)
    resid_mi = Moran(ols.u.flatten(), w)
    print(f"  OLS R2 = {ols.r2:.4f} | 잔차 Moran's I = {resid_mi.I:+.4f} (p={resid_mi.p_sim:.4f})")
    print("\n  [OLS]")
    for i, c in enumerate(XCOLS):
        b, t, p = ols.betas[i + 1][0], ols.t_stat[i + 1][0], ols.t_stat[i + 1][1]
        print(f"    {c:18s} b={b:+.4f}  t={t:+.2f}  p={p:.4f}")

    lag = GM_Lag(y, Z, w=w, name_y="log_dolmen", name_x=XCOLS)
    print("\n  [GM_Lag 공간시차]")
    names = XCOLS + ["W_log_dolmen(rho)"]
    for i, c in enumerate(names):
        b = lag.betas[i + 1][0]
        z, p = lag.z_stat[i + 1][0], lag.z_stat[i + 1][1]
        flag = "유의" if p < 0.05 else "비유의"
        print(f"    {c:18s} b={b:+.4f}  z={z:+.2f}  p={p:.4f}  {flag}")

    lag_mi = Moran(lag.u.flatten(), w)
    print(f"\n  GM_Lag 잔차 Moran's I = {lag_mi.I:+.4f} (p={lag_mi.p_sim:.4f})")
    print(f"  Pseudo R2 = {lag.pr2:.4f}")

    res = {
        "vif": {c: float(vif(Xv, i + 1)) for i, c in enumerate(XCOLS)},
        "corr": d[XCOLS].corr().round(4).to_dict(),
        "ols": {c: {"b": float(ols.betas[i+1][0]), "p": float(ols.t_stat[i+1][1])}
                for i, c in enumerate(XCOLS)},
        "ols_resid_moran": {"I": float(resid_mi.I), "p": float(resid_mi.p_sim)},
        "gm_lag": {c: {"b": float(lag.betas[i+1][0]), "p": float(lag.z_stat[i+1][1])}
                   for i, c in enumerate(names)},
        "gm_lag_resid_moran": {"I": float(lag_mi.I), "p": float(lag_mi.p_sim)},
        "gm_lag_pr2": float(lag.pr2),
    }
    (REP / "spatial_results.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print("\n[sp] saved reports/spatial_results.json")


if __name__ == "__main__":
    sys.exit(main())
