"""
파고–지석묘 관계의 비선형 구조 검정.

배경
----
선형 모형만 돌리면 파고 계수가 통제변수 구성에 따라 부호가 뒤집힌다.
  단변량 +0.268 → +연안거리 +0.241 → +수심 −0.018 → 전체 −0.238
이는 파고–수심 상관(r=−0.507)에 의한 억제(suppression)이며,
동시에 **관계 자체가 단조(monotonic)가 아니라는** 신호다.

4분위 기술통계에서 역U자가 드러난다:
  Q1(0.29m)  353기( 5.4%)
  Q2(0.57m) 2998기(45.8%)
  Q3(0.96m) 2738기(41.9%)
  Q4(1.06m)  450기( 6.9%)
전체 기수의 87.7%가 중간 2개 분위에 집중된다.

이 스크립트는 2차항으로 그 구조를 정식 검정한다.
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
from spreg import GM_Lag

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
REP = ROOT / "reports"

BASE = ("y ~ dist_coast_km_z + elev_m_z + marine_curr_p90_z"
        " + marine_grad_z + marine_depth_z")
NB = sm.families.NegativeBinomial(alpha=1.0)


def main() -> None:
    d = pd.read_csv(PROC / "analysis_table.csv")
    d["swh2"] = d.marine_swh_p90_z ** 2
    d["curr2"] = d.marine_curr_p90_z ** 2
    mu, sd = d.marine_swh_p90.mean(), d.marine_swh_p90.std(ddof=0)

    # ---- 1) 파고 계수의 명세 의존성 ----
    print("=" * 70)
    print("1. 파고 계수는 통제변수 구성에 따라 부호가 뒤집힌다")
    print("=" * 70)
    specs = {
        "단변량": "y ~ marine_swh_p90_z",
        "+연안거리": "y ~ marine_swh_p90_z + dist_coast_km_z",
        "+수심": "y ~ marine_swh_p90_z + dist_coast_km_z + marine_depth_z",
        "+전체": BASE + " + marine_swh_p90_z",
    }
    spec_out = {}
    for n, f in specs.items():
        m = smf.glm(f, data=d, family=NB).fit()
        b, p = m.params["marine_swh_p90_z"], m.pvalues["marine_swh_p90_z"]
        spec_out[n] = {"b": float(b), "p": float(p)}
        print(f"  {n:10s} b={b:+.4f}  p={p:.4f}")
    print(f"\n  파고–수심 상관 r = {d.marine_swh_p90.corr(d.marine_depth):+.3f}"
          "  → 억제(suppression) 구조")

    # ---- 2) 4분위 기술통계 ----
    print("\n" + "=" * 70)
    print("2. 파고 4분위별 지석묘 분포 — 역U자")
    print("=" * 70)
    d["q"] = pd.qcut(d.marine_swh_p90, 4, duplicates="drop")
    g = d.groupby("q", observed=True).agg(
        cells=("y", "size"), total=("y", "sum"),
        mean_per_cell=("y", "mean"), mean_swh=("marine_swh_p90", "mean")).round(2)
    g["share_%"] = (g.total / g.total.sum() * 100).round(1)
    print(g.to_string())
    mid = g["share_%"].iloc[1:3].sum()
    print(f"\n  중간 2개 분위 점유율 = {mid:.1f}%")

    # ---- 3) 2차항 검정 ----
    print("\n" + "=" * 70)
    print("3. 2차항 검정")
    print("=" * 70)
    lin = smf.glm(BASE + " + marine_swh_p90_z", data=d, family=NB).fit()
    qua = smf.glm(BASE + " + marine_swh_p90_z + swh2", data=d, family=NB).fit()
    lr = 2 * (qua.llf - lin.llf); p = stats.chi2.sf(lr, 1)
    print(f"  선형  AIC={lin.aic:.1f}   2차항 AIC={qua.aic:.1f}")
    print(f"  LR={lr:.2f}  df=1  p={p:.3e}")
    b1, b2 = qua.params["marine_swh_p90_z"], qua.params["swh2"]
    print(f"  b(swh)={b1:+.4f} (p={qua.pvalues['marine_swh_p90_z']:.4f})")
    print(f"  b(swh²)={b2:+.4f} (p={qua.pvalues['swh2']:.2e})")
    peak = (-b1 / (2 * b2)) * sd + mu if b2 < 0 else None
    if peak is not None:
        print(f"  → 정점 파고 = {peak:.3f} m (이 값 부근에서 밀도 최대)")

    qc = smf.glm(BASE + " + marine_swh_p90_z + swh2 + curr2", data=d, family=NB).fit()
    lr2 = 2 * (qc.llf - qua.llf)
    print(f"\n  유속 2차항 추가: LR={lr2:.2f} p={stats.chi2.sf(lr2,1):.4f}"
          f" b={qc.params['curr2']:+.4f}")

    # ---- 4) 공간보정 후에도 남는가 ----
    print("\n" + "=" * 70)
    print("4. 공간시차 모형에 2차항 투입")
    print("=" * 70)
    X = d[["dist_coast_km_z", "elev_m_z", "marine_curr_p90_z", "marine_grad_z",
           "marine_depth_z", "marine_swh_p90_z", "swh2"]].values
    yv = np.log1p(d["y"].values).reshape(-1, 1)
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(d.ctr_x, d.ctr_y), crs=5179)
    w = KNN.from_dataframe(pts, k=8); w.transform = "r"
    lag = GM_Lag(yv, X, w=w)
    nm = ["dist_coast", "elev", "curr_p90", "sea_grad", "depth", "swh", "swh2", "rho"]
    lag_out = {}
    for i, c in enumerate(nm):
        b = float(lag.betas[i + 1][0]); pp = float(lag.z_stat[i + 1][1])
        lag_out[c] = {"b": b, "p": pp}
        print(f"  {c:11s} b={b:+.4f}  p={pp:.4f}  {'유의' if pp < 0.05 else ''}")
    print(f"  Pseudo R² = {lag.pr2:.4f}")

    out = {
        "spec_dependence": spec_out,
        "swh_depth_corr": float(d.marine_swh_p90.corr(d.marine_depth)),
        "quartiles": {str(k): {c: float(v) for c, v in row.items()}
                      for k, row in g.iterrows()},
        "mid_quartile_share_pct": float(mid),
        "quadratic": {"LR": float(lr), "p": float(p),
                      "b_swh": float(b1), "b_swh2": float(b2),
                      "peak_swh_m": float(peak) if peak else None,
                      "aic_linear": float(lin.aic), "aic_quad": float(qua.aic)},
        "spatial_with_quadratic": lag_out,
        "spatial_pr2": float(lag.pr2),
    }
    (REP / "nonlinear_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2))
    print("\n[nl] saved reports/nonlinear_results.json")


if __name__ == "__main__":
    sys.exit(main())
