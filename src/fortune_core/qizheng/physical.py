"""Physical seven-body positions for the deliberately limited Qizheng beta."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fortune_core.models import QizhengBodySnapshot, QizhengSnapshot
from fortune_core.time_location import (
    EPHEMERIS_END_YEAR,
    EPHEMERIS_ID,
    EPHEMERIS_START_YEAR,
    skyfield_resources,
)

# datetime.UTC needs Python 3.11+; the SCF runtime is 3.10.
UTC = timezone.utc

PROFILE_ID = "qizheng-physical-beta-v1"
_BODY_KEYS = (
    ("sun", "sun"),
    ("moon", "moon"),
    ("mercury", "mercury"),
    ("venus", "venus"),
    ("mars", "mars barycenter"),
    ("jupiter", "jupiter barycenter"),
    ("saturn", "saturn barycenter"),
)


def _longitude_at(instant: datetime, ephemeris, timescale, body_key: str) -> float:
    time = timescale.from_datetime(instant.astimezone(UTC))
    _, longitude, _ = (
        ephemeris["earth"]
        .at(time)
        .observe(ephemeris[body_key])
        .apparent()
        .ecliptic_latlon(epoch="date")
    )
    return longitude.degrees % 360


def _signed_angle_difference(after: float, before: float) -> float:
    return (after - before + 180) % 360 - 180


def calculate_physical_baseline(civil_datetime: datetime) -> QizhengSnapshot:
    """Return apparent geocentric ecliptic positions at civil UTC instant.

    This deliberately does not use apparent solar time: a physical ephemeris
    position describes an instant, while apparent solar time is only a local
    civil-clock transformation for the BaZi and Ziwei rule profiles.
    """
    if civil_datetime.tzinfo is None:
        raise ValueError("civil_datetime must include an explicit UTC offset")
    if not EPHEMERIS_START_YEAR <= civil_datetime.year <= EPHEMERIS_END_YEAR:
        raise ValueError(
            f"{EPHEMERIS_ID} supports civil years "
            f"{EPHEMERIS_START_YEAR}-{EPHEMERIS_END_YEAR}"
        )

    instant = civil_datetime.astimezone(UTC)
    timescale, ephemeris = skyfield_resources()
    bodies = []
    for body, body_key in _BODY_KEYS:
        time = timescale.from_datetime(instant)
        latitude, longitude, _ = (
            ephemeris["earth"]
            .at(time)
            .observe(ephemeris[body_key])
            .apparent()
            .ecliptic_latlon(epoch="date")
        )
        before = _longitude_at(instant - timedelta(hours=1), ephemeris, timescale, body_key)
        after = _longitude_at(instant + timedelta(hours=1), ephemeris, timescale, body_key)
        longitude_rate = _signed_angle_difference(after, before) * 12
        bodies.append(
            QizhengBodySnapshot(
                body=body,
                longitude_deg=longitude.degrees % 360,
                latitude_deg=latitude.degrees,
                longitude_rate_deg_per_day=longitude_rate,
                motion="retrograde" if longitude_rate < 0 else "direct",
            )
        )

    return QizhengSnapshot(
        profile_id=PROFILE_ID,
        ephemeris_id=EPHEMERIS_ID,
        ephemeris_datetime=instant,
        bodies=tuple(bodies),
        scope_limits=(
            "physical_positions_only",
            "traditional_houses_not_computed",
            "traditional_limits_not_computed",
            "dynamic_fortune_disabled",
        ),
        verification_status="ambiguous",
    )
