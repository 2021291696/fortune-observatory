"""Twenty-eight mansions on the J2000 mean-ecliptic anchor (今测宿度).

口径（qizheng-traditional-alpha-v1）：
- 恒星黄道锚点 = J2000 平黄道帧；距星坐标取 J2000 星表值（忽略自行，1849-2150 误差 <0.05°）。
- 宿界 = 相邻距星 J2000 黄经（黄经升序），宿度即今测宿度；天体入宿用同帧 apparent 黄经
  （含光行差，与距星光行差差异 ≤20″，远小于宿界容差）。
- 宫支按宿界分宫：辰角亢、巳翼轸、午柳星张、未井鬼、申觜参、酉胃昴毕、
  戌奎娄、亥室壁、子女虚危、丑斗牛、寅尾箕、卯房心氐。
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# J2000 平黄赤交角（IAU 1980 常用值）。
OBLIQUITY_DEG = 23.4392911

# 28 宿距星：黄经升序（轸起于角前环绕），J2000 赤道坐标。
# (宿名, 宫支, Bayer 星名, RA 小时, RA 分, RA 秒, 赤纬度, 赤纬角分, 赤纬角秒)
# 赤纬符号存在"度"上；南纬 0° 区（如危 −0°19′）用浮点 -0.0 保留负号（int -0 会丢）。
# 距星身份依维基《二十八宿》距星表（承明清调整：奎宿二 ζ And、觜宿二 φ¹ Ori、
# 昴宿一 17 Tau）；参距星该表作参宿三 δ Ori，但 δ Ori 黄经（82.4°）在觜距星之西，
# 宿度将为负，几何不可行，故取崇祯以来"距星称宿一"通例用参宿一 ζ Ori。
# 全表已对 HYG v4.1（Hipparcos）交叉校验（scripts/cross_check_mansions_hyg.py，≤120″）。
MANSION_STARS: tuple[tuple[str, str, str, float, int, float, float, int, float], ...] = (
    ("角", "辰", "α Vir", 13, 25, 11.6, -11, 9, 41.0),
    ("亢", "辰", "κ Vir", 14, 12, 53.7, -10, 16, 25.3),
    ("氐", "卯", "α² Lib", 14, 50, 52.7, -16, 2, 30.0),
    ("房", "卯", "π Sco", 15, 58, 51.1, -26, 6, 51.0),
    ("心", "卯", "σ Sco", 16, 21, 11.3, -25, 35, 34.0),
    ("尾", "寅", "μ¹ Sco", 16, 51, 52.3, -38, 2, 51.0),
    ("箕", "寅", "γ Sgr", 18, 5, 48.1, -30, 25, 27.0),
    ("斗", "丑", "φ Sgr", 18, 45, 39.4, -26, 59, 27.0),
    ("牛", "丑", "β Cap", 20, 21, 0.7, -14, 46, 53.0),
    ("女", "子", "ε Aqr", 20, 47, 40.5, -9, 29, 44.8),
    ("虚", "子", "β Aqr", 21, 31, 33.5, -5, 34, 16.0),
    ("危", "子", "α Aqr", 22, 5, 47.0, -0.0, 19, 11.0),
    ("室", "亥", "α Peg", 23, 4, 45.7, 15, 12, 19.0),
    ("壁", "亥", "γ Peg", 0, 13, 14.2, 15, 11, 1.0),
    ("奎", "戌", "ζ And", 0, 47, 20.3, 24, 16, 1.8),
    ("娄", "戌", "β Ari", 1, 54, 38.4, 20, 48, 29.0),
    ("胃", "酉", "35 Ari", 2, 43, 27.1, 27, 42, 25.7),
    ("昴", "酉", "17 Tau", 3, 44, 52.5, 24, 6, 48.0),
    ("毕", "酉", "ε Tau", 4, 28, 37.0, 19, 10, 58.0),
    ("觜", "申", "φ¹ Ori", 5, 34, 49.2, 9, 29, 22.5),
    ("参", "申", "ζ Ori", 5, 40, 45.5, -1, 56, 34.0),
    ("井", "未", "μ Gem", 6, 22, 57.6, 22, 30, 49.0),
    ("鬼", "未", "θ Cnc", 8, 31, 35.7, 18, 5, 42.0),
    ("柳", "午", "δ Hya", 8, 37, 39.0, 5, 42, 37.0),
    ("星", "午", "α Hya", 9, 27, 35.2, -8, 39, 31.0),
    ("张", "午", "υ¹ Hya", 9, 51, 28.7, -14, 50, 47.8),
    ("翼", "巳", "α Crt", 10, 59, 46.4, -18, 17, 55.6),
    ("轸", "巳", "γ Crv", 12, 15, 48.4, -17, 32, 31.0),
)


@dataclass(frozen=True)
class MansionEntry:
    name: str
    branch: str
    star: str
    longitude_deg: float


def equatorial_to_ecliptic_longitude(ra_hours: float, dec_deg: float) -> float:
    """J2000 赤道坐标 → J2000 黄经（度）。"""
    ra = math.radians(ra_hours * 15.0)
    dec = math.radians(dec_deg)
    epsilon = math.radians(OBLIQUITY_DEG)
    longitude = math.atan2(
        math.sin(ra) * math.cos(epsilon) + math.tan(dec) * math.sin(epsilon),
        math.cos(ra),
    )
    return math.degrees(longitude) % 360.0


def mansion_table() -> tuple[MansionEntry, ...]:
    """按黄经升序构建宿表（角起）。"""
    entries = []
    for name, branch, star, h, m, s, dd, dm, ds in MANSION_STARS:
        ra = h + m / 60.0 + s / 3600.0
        dec = math.copysign(abs(dd) + dm / 60.0 + ds / 3600.0, dd)
        entries.append(MansionEntry(name, branch, star, equatorial_to_ecliptic_longitude(ra, dec)))
    entries.sort(key=lambda entry: entry.longitude_deg)
    return tuple(entries)


_TABLE = mansion_table()
_LONGITUDES = [entry.longitude_deg for entry in _TABLE]


def mansion_of(sidereal_longitude: float) -> tuple[MansionEntry, float]:
    """入宿：返回 (宿, 度数)。宿界为本宿距星至下一宿距星。"""
    for index, longitude in enumerate(_LONGITUDES):
        following = _LONGITUDES[(index + 1) % len(_LONGITUDES)]
        span = (following - longitude) % 360.0
        offset = (sidereal_longitude - longitude) % 360.0
        if offset < span:
            return _TABLE[index], offset
    raise ValueError("sidereal longitude must be finite")


def branch_of(sidereal_longitude: float) -> str:
    return mansion_of(sidereal_longitude)[0].branch
