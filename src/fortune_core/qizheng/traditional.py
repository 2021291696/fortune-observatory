"""传统层组装：七政四余恒星黄道入宿 + 命身十二宫（alpha）。

口径（qizheng-traditional-alpha-v1）：
- 恒星黄道锚点 = J2000 平黄道帧。七政取 apparent 视位置（含光行差）经 ICRS
  赤道坐标转 J2000 黄经（与距星表同一转换函数）。
- 四余为平根数（瞬时黄经），减 IAU1976 黄经总岁差 p_A 归算到 J2000 帧
  （T·5029.0966″ + T²·1.11113″，±150 年内优于 0.01°）。
- 入宿度 = 天体 J2000 黄经 − 本宿距星黄经；宫支按宿界分宫。
- 命宫/身宫/十二宫见 houses.py。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fortune_core.models import (
    QizhengTraditionalBody,
    QizhengTraditionalHouses,
    QizhengTraditionalSnapshot,
)
from fortune_core.qizheng.four_remainders import _centuries, four_remainders
from fortune_core.qizheng.houses import arrange_houses
from fortune_core.qizheng.mansions import (
    branch_of,
    equatorial_to_ecliptic_longitude,
    mansion_of,
)
from fortune_core.time_location import (
    EPHEMERIS_END_YEAR,
    EPHEMERIS_START_YEAR,
    skyfield_resources,
)

UTC = timezone.utc

PROFILE_ID = "qizheng-traditional-alpha-v1"

_BODY_KEYS = (
    ("sun", "sun"),
    ("moon", "moon"),
    ("mercury", "mercury"),
    ("venus", "venus"),
    ("mars", "mars barycenter"),
    ("jupiter", "jupiter barycenter"),
    ("saturn", "saturn barycenter"),
)
_REMAINDER_KEYS = (("rahu", "罗睺"), ("ketu", "计都"), ("apogee", "月孛"), ("ziqi", "紫炁"))

# J2000 帧黄经 = 瞬时平黄经 − p_A（IAU1976 黄经总岁差）。
_PRECESSION_ARCSEC_PER_CENTURY = 5029.0966
_PRECESSION_ARCSEC_PER_CENTURY_SQ = 1.11113


def _precession_deg(centuries: float) -> float:
    return (
        _PRECESSION_ARCSEC_PER_CENTURY * centuries
        + _PRECESSION_ARCSEC_PER_CENTURY_SQ * centuries * centuries
    ) / 3600.0


def _j2000_longitude(instant: datetime, ephemeris, timescale, body_key: str) -> float:
    """apparent 视位置（ICRS）→ J2000 平黄道黄经，与距星表同帧。"""
    time = timescale.from_datetime(instant.astimezone(UTC))
    ra, dec, _ = (
        ephemeris["earth"].at(time).observe(ephemeris[body_key]).apparent().radec()
    )
    return equatorial_to_ecliptic_longitude(ra.hours, dec.degrees)


def _signed_rate(after: float, before: float) -> float:
    return (after - before + 180.0) % 360.0 - 180.0


def calculate_traditional(
    civil_datetime: datetime, hour_branch: str
) -> QizhengTraditionalSnapshot:
    """排七政四余入宿与命身十二宫（alpha 静态展示，不做吉凶解读）。"""
    if civil_datetime.tzinfo is None:
        raise ValueError("civil_datetime must include an explicit UTC offset")
    if not EPHEMERIS_START_YEAR <= civil_datetime.year <= EPHEMERIS_END_YEAR:
        raise ValueError(
            f"ephemeris supports civil years {EPHEMERIS_START_YEAR}-{EPHEMERIS_END_YEAR}"
        )

    instant = civil_datetime.astimezone(UTC)
    timescale, ephemeris = skyfield_resources()

    bodies: list[QizhengTraditionalBody] = []
    longitudes: dict[str, float] = {}
    for key, body_key in _BODY_KEYS:
        longitude = _j2000_longitude(instant, ephemeris, timescale, body_key)
        before = _j2000_longitude(instant - timedelta(hours=1), ephemeris, timescale, body_key)
        after = _j2000_longitude(instant + timedelta(hours=1), ephemeris, timescale, body_key)
        rate = _signed_rate(after, before) * 12.0
        mansion, offset = mansion_of(longitude)
        longitudes[key] = longitude
        bodies.append(
            QizhengTraditionalBody(
                body=key,
                longitude_deg=round(longitude, 3),
                longitude_rate_deg_per_day=round(rate, 4),
                motion="retrograde" if rate < 0 else "direct",
                mansion=mansion.name,
                mansion_branch=mansion.branch,
                mansion_offset_deg=round(offset, 2),
            )
        )

    precession = _precession_deg(_centuries(instant))
    for key, label in _REMAINDER_KEYS:
        longitude, rate = four_remainders(instant)[label]
        longitude_j2000 = (longitude - precession) % 360.0
        mansion, offset = mansion_of(longitude_j2000)
        longitudes[key] = longitude_j2000
        bodies.append(
            QizhengTraditionalBody(
                body=key,
                longitude_deg=round(longitude_j2000, 3),
                longitude_rate_deg_per_day=round(rate, 4),
                motion="retrograde" if rate < 0 else "direct",
                mansion=mansion.name,
                mansion_branch=mansion.branch,
                mansion_offset_deg=round(offset, 2),
            )
        )

    layout = arrange_houses(branch_of(longitudes["sun"]), hour_branch)
    houses = QizhengTraditionalHouses(
        life_branch=layout.life_branch,
        body_branch=layout.body_branch,
        houses=tuple((house.name, house.branch) for house in layout.houses),
    )

    return QizhengTraditionalSnapshot(
        profile_id=PROFILE_ID,
        anchor="j2000_mean_ecliptic",
        bodies=tuple(bodies),
        houses=houses,
        notes=(
            "紫炁为月孛对宫占位（现代约定，非古典行度）",
            "四余为平根数并归算 J2000 恒星黄道帧",
        ),
        scope_limits=(
            "traditional_alpha",
            "dignities_not_computed",
            "limits_not_computed",
            "dynamic_fortune_disabled",
        ),
        verification_status="ambiguous",
    )
