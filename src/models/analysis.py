"""
Phase C·D: 점패턴(GATE 1) + 음이항 회귀(GATE 2·3).

설계 노트
---------
1) 연구영역 한정: 조사가 실제 수행된 영산강유역 footprint 내부만 사용한다.
   미조사 지역을 0으로 넣으면 조사강도 편향이 그대로 들어온다.

2) offset 미사용: n_sites 는 결과변수와 동어반복(유적수↑=기수↑)이라
   offset 으로 쓰면 순환이 된다. 대신 연구영역 한정으로 조사강도를 통제한다.

3) 위험도 단일지수 대신 성분 분리 투입:
   PCA PC1 설명분산이 50.1%(적재 ±0.707)로, 두 성분이 사실상 무상관이다.
   단일 risk_score 는 해석 불가능하므로 curr_p90 과 sea_grad 를 따로 넣는다.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from libpysal.weights import KNN
from esda.moran import Moran

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
REP = ROOT / "reports"


def study_region(grid: gpd.GeoDataFrame, buffer_km: float = 10.0) -> gpd.GeoDataFrame:
    """조사 수행 footprint = 유적 보유 격자의 buffer 합집합."""
    occ = grid[grid.n_sites > 0]
    hull = occ.geometry.union_all().buffer(buffer_km * 1000)
    inside = grid[grid.geometry.intersects(hull)].copy()
    return inside


def simplify_landform(s: str) -> str:
    s = str(s or "")
    if "산록" in s: return "산록"
    if "구릉" in s: return "구릉"
    if "평지" in s: return "평지"
    return "기타"


def main() -> None:
    REP.mkdir(exist_ok=True)
    grid = gpd.read_parquet(PROC / "grid_5km_marine.parquet")
    d = study_region(grid)
    print(f"[reg] 전체 육상격자 {len(grid):,} -> 연구영역 {len(d):,}")
    print(f"[reg] 지석묘 총 {d.n_dolmen.sum():,.0f}기 / 유적 보유 격자 {(d.n_sites>0).sum()}")

    d["landform_g"] = d["landform_mode"].map(simplify_landform)
    d["y"] = d["n_dolmen"].astype(int)

    # 표준화 (계수 비교 가능하게)
    for c in ["dist_coast_km", "elev_m", "marine_curr_p90", "marine_grad", "marine_depth"]:
        d[c + "_z"] = (d[c] - d[c].mean()) / d[c].std(ddof=0)

    # ---------- 공선성 진단 ----------
    cc = ["dist_coast_km", "elev_m", "marine_curr_p90", "marine_grad", "marine_depth"]
    print("\n" + "="*66)
    print("공선성 진단: 예측변수 상관행렬")
    print("="*66)
    print(d[cc].corr().round(3).to_string())
    from statsmodels.stats.outliers_influence import variance_inflation_factor as _vif
    Xv = sm.add_constant(d[[c+"_z" for c in cc]].values)
    print("\n  VIF:", {c: round(_vif(Xv, i+1), 2) for i, c in enumerate(cc)})

    # ---------- GATE 1: 공간 자기상관 ----------
    pts = gpd.GeoDataFrame(d[["y"]], geometry=gpd.points_from_xy(d["ctr_x"], d["ctr_y"]),
                           crs=grid.crs)
    w = KNN.from_dataframe(pts, k=8); w.transform = "r"
    mi = Moran(d["y"].values, w)
    print("\n" + "="*66)
    print("GATE 1  공간 자기상관 (Moran's I)")
    print("="*66)
    print(f"  I = {mi.I:+.4f}   E[I] = {mi.EI:+.4f}   z = {mi.z_sim:+.3f}   p = {mi.p_sim:.4f}")
    gate1 = (mi.I > 0) and (mi.p_sim < 0.05)
    print(f"  판정: {'통과 — 군집 존재' if gate1 else '실패 — CSR 기각 못함'}")

    # ---------- GATE 2·3: 음이항 회귀 ----------
    # landform 은 지석묘 보유 격자에만 정의되므로 결과변수 조건화가 된다.
    # (기타 = 유적없음 더미로 작동) -> 주모형에서 제외한다.
    models = {
        "M1_연안거리만": "y ~ dist_coast_km_z",
        "M2_지형통제":   "y ~ dist_coast_km_z + elev_m_z",
        "M3_해양위험도": "y ~ dist_coast_km_z + elev_m_z"
                        " + marine_curr_p90_z + marine_grad_z + marine_depth_z",
    }
    fits, rows = {}, []
    print("\n" + "="*66)
    print("GATE 2·3  음이항 회귀 (NB2)")
    print("="*66)
    for name, f in models.items():
        m = smf.glm(f, data=d, family=sm.families.NegativeBinomial(alpha=1.0)).fit()
        fits[name] = m
        rows.append({"model": name, "llf": m.llf, "aic": m.aic, "df": m.df_model})
        print(f"\n── {name}   logL={m.llf:.2f}  AIC={m.aic:.1f}")
        for p in m.params.index:
            if p == "Intercept": continue
            print(f"     {p:26s} b={m.params[p]:+.4f}  se={m.bse[p]:.4f}  p={m.pvalues[p]:.4f}")

    # 우도비 검정 M2 vs M3
    lr = 2 * (fits["M3_해양위험도"].llf - fits["M2_지형통제"].llf)
    ddf = fits["M3_해양위험도"].df_model - fits["M2_지형통제"].df_model
    p_lr = stats.chi2.sf(lr, ddf)
    print("\n" + "="*66)
    print("GATE 3  판정: M2 vs M3 우도비 검정")
    print("="*66)
    print(f"  LR = {lr:.4f}   df = {ddf}   p = {p_lr:.4f}")
    gate3 = p_lr < 0.05
    print(f"  판정: {'통과 — 해양위험도가 추가 설명력 보유' if gate3 else '실패 — 해양위험도 추가 설명력 없음'}")

    m3 = fits["M3_해양위험도"]
    risk_terms = ["marine_curr_p90_z", "marine_grad_z", "marine_depth_z"]
    print("\n  개별 위험도 계수:")
    for t in risk_terms:
        print(f"    {t:20s} b={m3.params[t]:+.4f}  p={m3.pvalues[t]:.4f}"
              f"  {'유의' if m3.pvalues[t]<0.05 else '비유의'}")

    # 잔차 공간 자기상관
    resid = m3.resid_pearson
    mi_r = Moran(np.asarray(resid), w)
    print(f"\n  M3 잔차 Moran's I = {mi_r.I:+.4f} (p={mi_r.p_sim:.4f})"
          f" -> {'공간구조 잔존, 공간회귀 필요' if mi_r.p_sim<0.05 else '잔차 공간구조 없음'}")

    # ---------- MAUP 민감도 ----------
    print("\n" + "="*66)
    print("MAUP 민감도: 격자 크기별 위험도 계수 부호")
    print("="*66)
    maup = []
    for agg in [1, 2, 4]:
        dd = d.copy()
        dd["gx"] = (dd["ctr_x"] // (5000 * agg)).astype(int)
        dd["gy"] = (dd["ctr_y"] // (5000 * agg)).astype(int)
        a = dd.groupby(["gx", "gy"]).agg(
            y=("y", "sum"), dist_coast_km=("dist_coast_km", "mean"),
            elev_m=("elev_m", "mean"), marine_curr_p90=("marine_curr_p90", "mean"),
            marine_grad=("marine_grad", "mean"), marine_depth=("marine_depth", "mean"),
        ).reset_index()
        for c in ["dist_coast_km", "elev_m", "marine_curr_p90", "marine_grad", "marine_depth"]:
            a[c + "_z"] = (a[c] - a[c].mean()) / a[c].std(ddof=0)
        mm = smf.glm("y ~ dist_coast_km_z + elev_m_z + marine_curr_p90_z"
                     " + marine_grad_z + marine_depth_z",
                     data=a, family=sm.families.NegativeBinomial(alpha=1.0)).fit()
        print(f"  {5*agg:2d}km (n={len(a):4d})  curr b={mm.params['marine_curr_p90_z']:+.4f}"
              f" p={mm.pvalues['marine_curr_p90_z']:.4f}   "
              f"grad b={mm.params['marine_grad_z']:+.4f} p={mm.pvalues['marine_grad_z']:.4f}")
        maup.append({"cell_km": 5*agg, "n": len(a),
                     "b_curr": float(mm.params["marine_curr_p90_z"]),
                     "p_curr": float(mm.pvalues["marine_curr_p90_z"]),
                     "b_grad": float(mm.params["marine_grad_z"]),
                     "p_grad": float(mm.pvalues["marine_grad_z"])})

    # ---------- 보조분석: 유적 보유 격자만 (강도 모형) ----------
    occ = d[d.n_sites > 0].copy()
    print("\n" + "="*66)
    print(f"보조분석: 유적 보유 격자만 (n={len(occ)}) — 0 과잉 제거")
    print("="*66)
    mo = smf.glm("y ~ dist_coast_km_z + elev_m_z + marine_curr_p90_z"
                 " + marine_grad_z + marine_depth_z + C(landform_g)",
                 data=occ, family=sm.families.NegativeBinomial(alpha=1.0)).fit()
    for pn in mo.params.index:
        if pn == "Intercept": continue
        print(f"    {pn:26s} b={mo.params[pn]:+.4f}  p={mo.pvalues[pn]:.4f}")
    occ_res = {pn: {"b": float(mo.params[pn]), "p": float(mo.pvalues[pn])}
               for pn in mo.params.index if pn != "Intercept"}

    out = {
        "occupied_only": occ_res,
        "n_cells_study": int(len(d)),
        "n_dolmen": int(d.n_dolmen.sum()),
        "gate1_moran": {"I": float(mi.I), "p": float(mi.p_sim), "pass": bool(gate1)},
        "gate3_lr": {"LR": float(lr), "df": int(ddf), "p": float(p_lr), "pass": bool(gate3)},
        "m3_risk_coefs": {t: {"b": float(m3.params[t]), "p": float(m3.pvalues[t])}
                          for t in risk_terms},
        "m3_dist_coast": {"b": float(m3.params["dist_coast_km_z"]),
                          "p": float(m3.pvalues["dist_coast_km_z"])},
        "resid_moran": {"I": float(mi_r.I), "p": float(mi_r.p_sim)},
        "model_fit": rows,
        "maup": maup,
    }
    def _ser(o):
        import numpy as _np
        if isinstance(o, (_np.integer,)): return int(o)
        if isinstance(o, (_np.floating,)): return float(o)
        if isinstance(o, (_np.bool_,)): return bool(o)
        raise TypeError(str(type(o)))
    (REP / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2, default=_ser))
    d.drop(columns="geometry").to_csv(PROC / "analysis_table.csv", index=False)
    print(f"\n[reg] saved reports/results.json")


if __name__ == "__main__":
    sys.exit(main())
