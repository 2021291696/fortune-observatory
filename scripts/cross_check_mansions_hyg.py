"""Cross-check MANSION_STARS against the HYG v4.1 catalog (Hipparcos-based).

Run: uv run python scripts/cross_check_mansions_hyg.py <hyg_csv_path>
HYG stores ra as decimal hours; the mansion helper takes hours too.
Prints per-mansion my-table vs HYG J2000 ecliptic longitude and flags drift.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fortune_core.qizheng.mansions import MANSION_STARS, equatorial_to_ecliptic_longitude

# mansion -> acceptable HYG `bf` 后缀（bf 为 Flamsteed+Bayer+星座连写，如 '50Zet Ori'、
# '9Alp2Lib' 无空格、'Mu 1Sco' 带空格、'37Phi1Ori'、'10Gam2Sgr'）
BF_LOOKUP = {
    "角": ("Alp Vir",),
    "亢": ("Kap Vir",),
    "氐": ("Alp2Lib", "Alp2 Lib", "Alp Lib"),
    "房": ("Pi Sco",),
    "心": ("Sig Sco",),
    "尾": ("Mu 1Sco", "Mu1Sco", "Mu1 Sco"),
    "箕": ("Gam2Sgr", "Gam2 Sgr", "Gam Sgr"),
    "斗": ("Phi Sgr",),
    "牛": ("Bet Cap",),
    "女": ("Eps Aqr",),
    "虚": ("Bet Aqr",),
    "危": ("Alp Aqr",),
    "室": ("Alp Peg",),
    "壁": ("Gam Peg",),
    "奎": ("Zet And",),
    "娄": ("Bet Ari",),
    "胃": ("35 Ari",),
    "昴": ("17 Tau",),
    "毕": ("Eps Tau",),
    "觜": ("Phi1Ori", "Phi1 Ori"),
    "参": ("Zet Ori",),
    "井": ("Mu Gem",),
    "鬼": ("The Cnc",),
    "柳": ("Del Hya",),
    "星": ("Alp Hya",),
    "张": ("Ups1Hya", "Ups1 Hya"),
    "翼": ("Alp Crt",),
    "轸": ("Gam Crv",),
}


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: uv run python scripts/cross_check_mansions_hyg.py <hygdata_v4.csv>")
        return 2
    hyg_path = Path(sys.argv[1]).resolve()
    if hyg_path.suffix.lower() != ".csv" or not hyg_path.is_file():
        print(f"refusing non-csv or missing path: {hyg_path}")
        return 2
    suffixes = {name for names in BF_LOOKUP.values() for name in names}
    matches: dict[str, list[tuple[float, float, str]]] = {}
    with open(hyg_path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            bf = " ".join((row.get("bf") or "").split())
            for suffix in suffixes:
                if bf.endswith(suffix):
                    # 优先带 Bayer 名的行（避免同 bf 的裸重复行/伴星行）
                    rank = "0" if row.get("bayer") else "1"
                    matches.setdefault(suffix, []).append(
                        (rank, float(row["ra"]), float(row["dec"]))
                    )
    rows = {
        suffix: min(rows_)[1:] for suffix, rows_ in matches.items()
    }

    failures = 0
    print(f"{'宿':<3}{'my star':<10}{'my λ':>9}{'HYG λ':>9}{'diff″':>8}  matched bf")
    for name, branch, star, rh, rm, rs, rd, dmi, ds in MANSION_STARS:
        my_ra_hours = rh + rm / 60 + rs / 3600
        my_dec = math.copysign(abs(rd) + dmi / 60 + ds / 3600, rd)
        my_lon = equatorial_to_ecliptic_longitude(my_ra_hours, my_dec)
        candidates = BF_LOOKUP[name]
        matched = next((suffix for suffix in candidates if suffix in rows), None)
        if matched is None:
            print(f"{name:<3}{star:<10}{my_lon:9.3f}{'MISS':>9}{'':>8}  NOT FOUND")
            failures += 1
            continue
        hyg_ra_hours, hyg_dec = rows[matched]
        hyg_lon = equatorial_to_ecliptic_longitude(hyg_ra_hours, hyg_dec)
        diff_arcsec = abs(hyg_lon - my_lon) * 3600
        flag = "" if diff_arcsec <= 120 else "  <-- DRIFT"
        if diff_arcsec > 120:
            failures += 1
        print(f"{name:<3}{star:<10}{my_lon:9.3f}{hyg_lon:9.3f}{diff_arcsec:8.1f}  {matched}{flag}")

    print(f"\n{'FAIL' if failures else 'PASS'}: {failures} drift/missing of {len(MANSION_STARS)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
