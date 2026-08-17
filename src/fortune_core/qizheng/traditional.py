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
    QizhengLimitRow,
    QizhengTraditionalBody,
    QizhengTraditionalHouses,
    QizhengTraditionalSnapshot,
)
from fortune_core.qizheng.dignities import (
    dignity_of,
    palace_lord,
    relation_to_lord,
)
from fortune_core.qizheng.four_remainders import _centuries, four_remainders
from fortune_core.qizheng.houses import arrange_houses
from fortune_core.qizheng.limits import childhood_exit_age, limit_table
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

PROFILE_ID = "qizheng-traditional-alpha-v2"

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


def _is_day_chart(
    instant: datetime, latitude: float, longitude: float, ephemeris, timescale
) -> bool:
    """太阳视高度 > 0（站心 apparent、不含折光）判昼盘。"""
    from skyfield.api import wgs84

    observer = ephemeris["earth"] + wgs84.latlon(latitude, longitude)
    time = timescale.from_datetime(instant.astimezone(UTC))
    altitude, _, _ = observer.at(time).observe(ephemeris["sun"]).apparent().altaz()
    return altitude.degrees > 0.0


def sun_moon_mansions(civil_datetime: datetime) -> tuple[str, str, str, str]:
    """(太阳宿, 太阳宫支, 月亮宿, 月亮宫支)——流日七政 facts 用（地心，与位置无关）。"""
    if civil_datetime.tzinfo is None:
        raise ValueError("civil_datetime must include an explicit UTC offset")
    instant = civil_datetime.astimezone(UTC)
    timescale, ephemeris = skyfield_resources()
    result = []
    for body_key in ("sun", "moon"):
        longitude = _j2000_longitude(instant, ephemeris, timescale, body_key)
        mansion, _offset = mansion_of(longitude)
        result.extend((mansion.name, mansion.branch))
    return result[0], result[1], result[2], result[3]


def calculate_traditional(
    civil_datetime: datetime,
    hour_branch: str,
    latitude: float | None = None,
    longitude: float | None = None,
) -> QizhengTraditionalSnapshot:
    """排七政四余传统层（入宿+命身宫+庙旺恩难+昼夜+洞微大限，alpha）。"""
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
        body_longitude = _j2000_longitude(instant, ephemeris, timescale, body_key)
        before = _j2000_longitude(instant - timedelta(hours=1), ephemeris, timescale, body_key)
        after = _j2000_longitude(instant + timedelta(hours=1), ephemeris, timescale, body_key)
        rate = _signed_rate(after, before) * 12.0
        mansion, offset = mansion_of(body_longitude)
        longitudes[key] = body_longitude
        bodies.append(
            QizhengTraditionalBody(
                body=key,
                longitude_deg=round(body_longitude, 3),
                longitude_rate_deg_per_day=round(rate, 4),
                motion="retrograde" if rate < 0 else "direct",
                mansion=mansion.name,
                mansion_branch=mansion.branch,
                mansion_offset_deg=round(offset, 2),
            )
        )

    precession = _precession_deg(_centuries(instant))
    for key, label in _REMAINDER_KEYS:
        longitude_raw, rate = four_remainders(instant)[label]
        longitude_j2000 = (longitude_raw - precession) % 360.0
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

    life_lord = palace_lord(layout.life_branch)
    body_lord = palace_lord(layout.body_branch)
    for body in bodies:
        body.dignity = dignity_of(body.body, body.mansion_branch, body.mansion)
        body.relation = relation_to_lord(body.body, life_lord)

    exit_age = childhood_exit_age(longitudes["sun"], branch_of(longitudes["sun"]))
    rows = tuple(
        QizhengLimitRow(palace=name, branch=branch, years=years,
                        start_age=round(start, 2), end_age=round(end, 2), segment=segment)
        for name, branch, years, start, end, segment in limit_table(layout.life_branch, exit_age)
    )
    is_day = (
        _is_day_chart(instant, latitude, longitude, ephemeris, timescale)
        if latitude is not None and longitude is not None
        else None
    )

    return QizhengTraditionalSnapshot(
        profile_id=PROFILE_ID,
        anchor="j2000_mean_ecliptic",
        bodies=tuple(bodies),
        houses=houses,
        life_lord=life_lord,
        body_lord=body_lord,
        is_day_chart=is_day,
        childhood_exit_age=round(exit_age, 2),
        limit_rows=rows,
        notes=(
            "紫炁为月孛对宫占位（现代约定，非古典行度）",
            "四余为平根数并归算 J2000 恒星黄道帧",
            "四余居垣为五行派生约定；恩难仇用之用/仇为通行读法（恩/难有典源）",
        ),
        scope_limits=(
            "traditional_alpha",
            "bamboo_rofa_limits_not_computed",
            "dynamic_fortune_limited",
        ),
        verification_status="ambiguous",
    )
