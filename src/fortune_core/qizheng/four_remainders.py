"""Four remainders (四余) on the frozen mean-element profile.

口径（qizheng-traditional-alpha-v1）：
- 罗睺 = 月球平升交点（Meeus/Chapront Ω），计都 = 罗睺 + 180°。
- 月孛 = 月球平远地点（L' − M' + 180°，Meeus 47.1/47.4 平根数）。
- 紫炁 = 月孛 + 180°（气孛对宫，现代约定占位，非古典行度）。
- T 取 UTC（不引入 ΔT）：均数行度 ≤1934°/儒略世纪，70 秒级时间差对黄经影响 <0.001°。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

UTC = timezone.utc
JULIAN_CENTURY_DAYS = 36525.0

# J2000.0 epoch: 2000-01-01 12:00 TT；本 profile 以 UTC 视同（误差见模块注释）。
_J2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC)


def _centuries(instant: datetime) -> float:
    return (instant - _J2000).total_seconds() / 86400.0 / JULIAN_CENTURY_DAYS


def mean_ascending_node(instant: datetime) -> float:
    """月球平升交点黄经（度，Meeus《Astronomical Algorithms》47.7）。"""
    t = _centuries(instant)
    return (
        125.0445479
        - 1934.1362891 * t
        + 0.0020754 * t * t
        + t ** 3 / 467441.0
        - t ** 4 / 60616000.0
    ) % 360.0


def _mean_moon_longitude(t: float) -> float:
    """月球平黄经 L'（Meeus 47.1）。"""
    return (
        218.3164477
        + 481267.88123421 * t
        - 0.0015786 * t * t
        + t ** 3 / 538841.0
        - t ** 4 / 65194000.0
    )


def _mean_moon_anomaly(t: float) -> float:
    """月球平近点角 M'（Meeus 47.4）。"""
    return (
        134.9633964
        + 477198.8675055 * t
        + 0.0087414 * t * t
        + t ** 3 / 69699.0
        - t ** 4 / 14712000.0
    )


def mean_lunar_apogee(instant: datetime) -> float:
    """月孛：月球平远地点黄经 = L' − M' + 180°（度）。"""
    t = _centuries(instant)
    return (_mean_moon_longitude(t) - _mean_moon_anomaly(t) + 180.0) % 360.0


def _rate_per_day(instant: datetime, longitude_at) -> float:
    before = longitude_at(instant - timedelta(hours=1))
    after = longitude_at(instant + timedelta(hours=1))
    signed = (after - before + 180.0) % 360.0 - 180.0
    return signed * 12.0


def four_remainders(instant: datetime) -> dict[str, tuple[float, float]]:
    """返回 {罗睺/计都/月孛/紫炁: (黄经°, 每日行度)}。计都/紫炁行度与本体同。"""
    rahu = mean_ascending_node(instant)
    yuebo = mean_lunar_apogee(instant)
    return {
        "罗睺": (rahu, _rate_per_day(instant, mean_ascending_node)),
        "计都": ((rahu + 180.0) % 360.0, _rate_per_day(instant, mean_ascending_node)),
        "月孛": (yuebo, _rate_per_day(instant, mean_lunar_apogee)),
        "紫炁": ((yuebo + 180.0) % 360.0, _rate_per_day(instant, mean_lunar_apogee)),
    }
