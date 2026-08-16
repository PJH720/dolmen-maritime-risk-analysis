"""결과 그림 생성 (4종)."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
EXT = ROOT / "data" / "external"
FIG = ROOT / "reports" / "figures"

for cand in ["AppleGothic", "Apple SD Gothic Neo", "NanumGothic", "Malgun Gothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 130

INK, ACC, WARN = "#1b2430", "#2f6f8f", "#b5452f"


def fig1_distribution():
    g = gpd.read_parquet(PROC / "grid_5km_marine.parquet")
    g["_cx"] = g.geometry.centroid.x; g["_cy"] = g.geometry.centroid.y
    g = g.to_crs(4326)
    import geopandas as _gpd
    _c = _gpd.GeoSeries(_gpd.points_from_xy(g["_cx"], g["_cy"]), crs=5179).to_crs(4326)
    g["lon_c"], g["lat_c"] = _c.x.values, _c.y.values
    occ = g[g.n_dolmen > 0]
    coast = gpd.read_file(EXT / "ne_10m_coastline" / "ne_10m_coastline.shp").cx[125:128.2, 34:36]

    fig, ax = plt.subplots(figsize=(7.4, 7.6))
    coast.plot(ax=ax, color="#8a97a6", lw=0.7, zorder=1)
    s = ax.scatter(occ["lon_c"], occ["lat_c"], s=occ.n_dolmen * 1.6 + 8, c=occ.n_dolmen,
                   cmap="YlOrRd", ec=INK, lw=0.35, alpha=0.88, zorder=3)
    plt.colorbar(s, ax=ax, shrink=0.62, label="격자당 지석묘 기수")
    ax.set_xlim(125.6, 127.9); ax.set_ylim(34.2, 35.9)
    ax.set_title(f"영산강유역 지석묘 분포 (5km 격자, 총 {int(g.n_dolmen.sum()):,}기)",
                 fontsize=12, color=INK, pad=10)
    ax.set_xlabel("경도"); ax.set_ylabel("위도")
    ax.grid(alpha=0.18, ls=":")
    fig.tight_layout(); fig.savefig(FIG / "fig1_distribution.png"); plt.close(fig)
    print("  fig1 ok")


def fig2_coefficients():
    sp = json.loads((ROOT / "reports" / "spatial_results.json").read_text())
    names = [n for n in ["dist_coast_km", "elev_m", "marine_curr_p90", "marine_grad",
                         "marine_depth", "marine_swh_p90"] if n in sp["ols"]]
    LB = {"dist_coast_km": "연안거리", "elev_m": "표고",
          "marine_curr_p90": "인접해역 유속p90", "marine_grad": "인접해역 수심경사",
          "marine_depth": "인접해역 수심", "marine_swh_p90": "인접해역 유의파고p90"}
    labels = [LB[n] for n in names]
    ob = [sp["ols"][n]["b"] for n in names]; op = [sp["ols"][n]["p"] for n in names]
    lb = [sp["gm_lag"][n]["b"] for n in names]; lp = [sp["gm_lag"][n]["p"] for n in names]

    y = np.arange(len(names)); h = 0.36
    fig, ax = plt.subplots(figsize=(8.6, 5.1))
    ax.barh(y + h/2, ob, h, color=[ACC if p < .05 else "#c9d3db" for p in op],
            ec=INK, lw=.5, label="비공간 OLS")
    ax.barh(y - h/2, lb, h, color=[WARN if p < .05 else "#e8d5cf" for p in lp],
            ec=INK, lw=.5, label="공간시차 GM_Lag")
    ax.axvline(0, color=INK, lw=1)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.set_xlabel("표준화 회귀계수")
    ax.set_title("공간자기상관 보정 시 해양 변수 효과 소멸 (ERA5 파고 포함)\n(진한 색 = p<0.05)",
                 fontsize=12, color=INK, pad=10)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.grid(axis="x", alpha=.2, ls=":")
    fig.tight_layout(); fig.savefig(FIG / "fig2_coefficients.png"); plt.close(fig)
    print("  fig2 ok")


def fig3_maup():
    r = json.loads((ROOT / "reports" / "results.json").read_text())
    m = pd.DataFrame(r["maup"])
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    series = [("b_curr", "인접해역 유속 p90", ACC), ("b_grad", "인접해역 수심경사", WARN)]
    if "b_swh" in m.columns and m["b_swh"].notna().all():
        series.append(("b_swh", "인접해역 유의파고 p90", "#4a7c59"))
    for col, lab, c in series:
        pc = m[col.replace("b_", "p_")]
        ax.plot(m.cell_km, m[col], "o-", color=c, lw=1.8, ms=7, label=lab)
        for x, yv, pv in zip(m.cell_km, m[col], pc):
            ax.annotate(f"p={pv:.3f}", (x, yv), textcoords="offset points",
                        xytext=(0, 9), ha="center", fontsize=8, color=c)
    ax.axhline(0, color=INK, lw=1, ls="--")
    ax.set_xticks(m.cell_km); ax.set_xlabel("격자 크기 (km)")
    ax.set_ylabel("표준화 회귀계수")
    ax.set_title("MAUP 민감도: 20km에서 유속 효과 소멸 (파고는 부호 안정)",
                 fontsize=12, color=INK, pad=10)
    ax.legend(frameon=False, fontsize=9); ax.grid(alpha=.2, ls=":")
    fig.tight_layout(); fig.savefig(FIG / "fig3_maup.png"); plt.close(fig)
    print("  fig3 ok")


def fig4_coast_gradient():
    d = pd.read_csv(PROC / "analysis_table.csv")
    bins = pd.cut(d.dist_coast_km, [0, 5, 10, 20, 30, 50, 200])
    g = d.groupby(bins, observed=True).agg(mean_n=("y", "mean"), cells=("y", "size")).reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2))
    axes[0].bar(range(len(g)), g.mean_n, color=ACC, ec=INK, lw=.5)
    axes[0].set_xticks(range(len(g)))
    axes[0].set_xticklabels([str(i) for i in g["dist_coast_km"]], rotation=30, fontsize=8)
    axes[0].set_ylabel("격자당 평균 기수"); axes[0].set_xlabel("연안거리 구간 (km)")
    axes[0].set_title("연안거리별 지석묘 밀도", fontsize=11, color=INK)
    axes[0].grid(axis="y", alpha=.2, ls=":")

    occ = d[d.y > 0]
    xc = "marine_swh_p90" if "marine_swh_p90" in occ.columns else "marine_curr_p90"
    xl = "인접해역 유의파고 p90 (m)" if xc.endswith("swh_p90") else "인접해역 유속 p90 (m/s)"
    axes[1].scatter(occ[xc], occ.y, s=16, alpha=.5, color=WARN, ec="none")
    axes[1].set_xlabel(xl); axes[1].set_ylabel("격자당 기수")
    axes[1].set_title("파고 위험도 대 지석묘 기수 (유적 보유 격자)", fontsize=11, color=INK)
    axes[1].grid(alpha=.2, ls=":")
    fig.tight_layout(); fig.savefig(FIG / "fig4_gradients.png"); plt.close(fig)
    print("  fig4 ok")


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    print("[fig] generating ...")
    fig1_distribution(); fig2_coefficients(); fig3_maup(); fig4_coast_gradient()
    fig5_wave_nonlinear()
    print(f"[fig] saved to {FIG}")




def fig5_wave_nonlinear():
    """파고–지석묘 역U자 구조 + 계수 부호의 명세 의존성."""
    import json as _j
    d = pd.read_csv(PROC / "analysis_table.csv")
    nl = _j.loads((ROOT / "reports" / "nonlinear_results.json").read_text())

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.4))

    # (좌) 파고 구간별 총 기수
    d["q"] = pd.qcut(d.marine_swh_p90, 4, duplicates="drop")
    g = d.groupby("q", observed=True).agg(total=("y", "sum"),
                                          swh=("marine_swh_p90", "mean")).reset_index()
    share = g.total / g.total.sum() * 100
    cols = ["#c9d3db", ACC, ACC, "#c9d3db"]
    axes[0].bar(range(len(g)), g.total, color=cols, ec=INK, lw=.6)
    for i, (t, s) in enumerate(zip(g.total, share)):
        axes[0].annotate(f"{int(t):,}기\n{s:.1f}%", (i, t), ha="center",
                         va="bottom", fontsize=8.5, color=INK)
    axes[0].set_xticks(range(len(g)))
    axes[0].set_xticklabels([f"Q{i+1}\n{v:.2f}m" for i, v in enumerate(g.swh)], fontsize=9)
    axes[0].set_ylabel("총 지석묘 기수"); axes[0].set_xlabel("인접해역 유의파고 p90 4분위")
    peak = nl["quadratic"]["peak_swh_m"]
    axes[0].set_title(f"중간 파고대 집중 (중간 2분위 {nl['mid_quartile_share_pct']:.1f}%)\n"
                      f"추정 정점 {peak:.2f} m", fontsize=11, color=INK)
    axes[0].set_ylim(0, g.total.max() * 1.28)
    axes[0].grid(axis="y", alpha=.2, ls=":")

    # (우) 명세별 파고 계수 부호 변화
    sp = nl["spec_dependence"]
    ks = list(sp.keys()); bs = [sp[k]["b"] for k in ks]; ps = [sp[k]["p"] for k in ks]
    c2 = [ACC if b > 0 else WARN for b in bs]
    c2 = [c if p < .05 else "#d8dee3" for c, p in zip(c2, ps)]
    axes[1].bar(range(len(ks)), bs, color=c2, ec=INK, lw=.6)
    axes[1].axhline(0, color=INK, lw=1)
    for i, (b, p) in enumerate(zip(bs, ps)):
        axes[1].annotate(f"p={p:.3f}", (i, b), ha="center",
                         va="bottom" if b > 0 else "top",
                         fontsize=8.5, color=INK,
                         xytext=(0, 4 if b > 0 else -12), textcoords="offset points")
    axes[1].set_xticks(range(len(ks))); axes[1].set_xticklabels(ks, fontsize=9)
    axes[1].set_ylabel("파고 회귀계수")
    axes[1].set_title(f"통제변수 구성에 따른 부호 반전\n(파고–수심 r="
                      f"{nl['swh_depth_corr']:+.2f}, 억제 구조)", fontsize=11, color=INK)
    axes[1].grid(axis="y", alpha=.2, ls=":")

    fig.tight_layout(); fig.savefig(FIG / "fig5_wave_nonlinear.png"); plt.close(fig)
    print("  fig5 ok")


if __name__ == "__main__":
    sys.exit(main())
