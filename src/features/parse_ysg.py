"""
『영산강유역 지석묘』Ⅴ 1~5권 유적 레코드 파서.

보고서 표준 8필드 구조:
  {번호} {유적명}
  1. 유적위치 / 2. 조사기관 / 3. 조사년도 / 4. 수량(기/현)
  5. 조사유형 / 6. 입지 / 7. 유적개요 / 8. 참고문헌

조판 함정 2가지 (실측 확인):
  (1) '6. 입' 뒤에 값이 오고 그 다음에 '지'가 떨어져 나온다.
      "6. 입 \n 구릉정상부 \n 51.9 \n 지 \n 7. 유적개요"
  (2) 3.조사년도의 '1992/1999/2005' 가 4.수량으로 새어들어
      2009/2014 같은 연도쌍이 기수로 잡힌다.
"""
from __future__ import annotations
import re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TXT = ROOT / "data" / "interim" / "pdftext"
OUT = ROOT / "data" / "interim"

FIELD_RE = {
    "위치": r"1\.\s*유적\s*위치",
    "기관": r"2\.\s*조사\s*기관",
    "연도": r"3\.\s*조사\s*년도",
    "수량": r"4\.\s*수\s*량",
    "유형": r"5\.\s*조사\s*유형",
    "입지": r"6\.\s*입(?!\S)",
    "개요": r"7\.\s*유적\s*개요",
    "문헌": r"8\.\s*참고\s*문헌",
}
ORDER = ["위치", "기관", "연도", "수량", "유형", "입지", "개요", "문헌"]

SIDO_RE = re.compile(r"(전라남도|광주광역시|전라북도|전북특별자치도)")
ADDR_RE = re.compile(r"([가-힣]{2,6}[시군구])\s*([가-힣]{1,8}[읍면동])?\s*([가-힣]{1,8}리)?")
QTY_RE = re.compile(r"(?<![\d.])(\d{1,4})\s*/\s*(\d{1,4})(?![\d.])")
LF_RE = re.compile(r"산록|구릉|평지|곡간|선상지|사면|정상|말단|하단|대지|충적|능선|산기슭|하천|해안|도서")
HEAD_RE = re.compile(r"^\s*(\d{1,4})\s+([가-힣][가-힣\s·ㆍ]{2,40}지석묘[가-힣\s]{0,8})\s*$", re.M)

_SIDO_TOKENS = {"전라남도", "광주광역시", "전라북도", "전북특별자치도"}


def clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s or "").strip()
    return re.sub(r"^[\.\,\-\s]+|[\.\,\-\s]+$", "", s)


def strip_noise(block: str) -> str:
    out = []
    for ln in (block or "").splitlines():
        s = ln.strip()
        if not s or re.fullmatch(r"[\d\.\,\s]+", s):
            continue
        out.append(s)
    return "\n".join(out)


def pick_landform(block: str) -> str:
    """'6. 입' 직후 첫 지형어 라인. 뒤따르는 고아 '지'는 건너뛴다."""
    for ln in (block or "").splitlines():
        s = ln.strip()
        if not s or s == "지" or re.fullmatch(r"[\d\.\,\s]+", s):
            continue
        if "유적개요" in s:
            break
        if LF_RE.search(s):
            tok = re.split(r"\s{2,}|\s(?=유적개요)", s)[0]
            return re.sub(r"\s+", " ", tok)[:24]
    return ""


def pick_qty(block: str) -> tuple[int | None, int | None]:
    """연도쌍(1900~2030) 및 비현실적 값 배제."""
    for m in QTY_RE.finditer(block or ""):
        a, b = int(m.group(1)), int(m.group(2))
        if 1900 <= a <= 2030 and 1900 <= b <= 2030:
            continue                      # 조사년도 오염
        if a > 1500 or b > 1500:
            continue
        return a, b
    return None, None


def parse_volume(path: Path, vol: int) -> list[dict]:
    text = path.read_text(errors="ignore")
    anchors = [m.start() for m in re.finditer(FIELD_RE["위치"], text)]
    records = []
    for i, a in enumerate(anchors):
        end = anchors[i + 1] if i + 1 < len(anchors) else len(text)
        chunk = text[a:end]

        heads = HEAD_RE.findall(text[max(0, a - 400):a])
        site_no, site_name = (heads[-1] if heads else ("", ""))

        pos = {}
        for k in ORDER:
            m = re.search(FIELD_RE[k], chunk)
            if m:
                pos[k] = (m.start(), m.end())
        ks = [k for k in ORDER if k in pos]
        vals = {}
        for j, k in enumerate(ks):
            s = pos[k][1]
            e = pos[ks[j + 1]][0] if j + 1 < len(ks) else len(chunk)
            vals[k] = chunk[s:e]

        addr_raw = clean(strip_noise(vals.get("위치", "")))
        sm = SIDO_RE.search(addr_raw)
        sido = sm.group(1) if sm else None
        tail = addr_raw[sm.end():] if sm else addr_raw
        am = ADDR_RE.search(tail)
        sigungu, eupmyeon, ri = (am.groups() if am else (None, None, None))
        if sigungu in _SIDO_TOKENS:
            sigungu = None

        n_rec, n_ext = pick_qty(strip_noise(vals.get("수량", "")))

        records.append({
            "vol": vol,
            "site_no": site_no,
            "site_name": clean(site_name),
            "addr_raw": addr_raw[:200],
            "sido": sido, "sigungu": sigungu, "eupmyeon": eupmyeon, "ri": ri,
            "n_recorded": n_rec,
            "n_extant": n_ext,
            "survey_type": clean(strip_noise(vals.get("유형", "")))[:24],
            "landform": pick_landform(vals.get("입지", "")),
            "survey_year": clean(strip_noise(vals.get("연도", "")))[:40],
        })
    return records


def main() -> None:
    rows = []
    for v in range(1, 6):
        p = TXT / f"ysg_raw_v{v}.txt"
        if not p.exists():
            print(f"[ysg] missing {p}"); continue
        r = parse_volume(p, v)
        print(f"[ysg] vol{v}: {len(r)} records")
        rows += r

    df = pd.DataFrame(rows)
    df.to_parquet(OUT / "ysg_sites_raw.parquet", index=False)

    print(f"\n[ysg] total = {len(df)}")
    print(f"  시군 확보     : {df.sigungu.notna().sum()}")
    print(f"  리(里) 확보   : {df.ri.notna().sum()}")
    print(f"  수량 확보     : {df.n_recorded.notna().sum()}")
    print(f"  입지 확보     : {(df.landform != '').sum()}")
    print(f"  기록 기수 합계: {df.n_recorded.sum():,.0f}")
    print(f"  현존 기수 합계: {df.n_extant.sum():,.0f}")
    inv = df[(df.n_extant > df.n_recorded)]
    print(f"  현존>기록 이상: {len(inv)}건")
    print("\n[ysg] 시군별 상위 12:")
    print(df.groupby("sigungu")["n_recorded"].agg(["count", "sum"])
            .sort_values("sum", ascending=False).head(12).to_string())
    print("\n[ysg] 입지 상위 10:")
    print(df[df.landform != ""].landform.value_counts().head(10).to_string())


if __name__ == "__main__":
    sys.exit(main())
