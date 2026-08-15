from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from skyfield.api import Loader, load_file

# datetime.UTC and hashlib.file_digest need Python 3.11+; the SCF runtime is 3.10.
UTC = timezone.utc


EPHEMERIS_ID = "de440s"
EPHEMERIS_SHA256 = "c1c7feeab882263fc493a9d5a5b2ddd71b54826cdf65d8d17a76126b260a49f2"
EPHEMERIS_START_YEAR = 1849
EPHEMERIS_END_YEAR = 2150
EPHEMERIS_PATH = Path(__file__).resolve().parents[3] / "data" / "ephemeris" / "de440s.bsp"


def _verify_ephemeris(path: Path, expected_sha256: str = EPHEMERIS_SHA256) -> str:
    if not path.is_file():
        raise RuntimeError("Pinned ephemeris file is missing")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if not hmac.compare_digest(actual_sha256, expected_sha256):
        raise RuntimeError("Pinned ephemeris integrity check failed")
    return actual_sha256


@lru_cache(maxsize=1)
def skyfield_resources():
    _verify_ephemeris(EPHEMERIS_PATH)
    loader = Loader(EPHEMERIS_PATH.parent)
    return loader.timescale(), load_file(EPHEMERIS_PATH)


def apparent_solar_datetime(civil_datetime: datetime, longitude: float) -> datetime:
    """Convert an aware civil time to local apparent solar time with JPL DE440s.

    The apparent solar clock is derived directly from the apparent solar hour
    angle. Longitude is east-positive; latitude is intentionally not involved
    because it affects altitude, not the local apparent solar clock.
    """
    if civil_datetime.tzinfo is None:
        raise ValueError("civil_datetime must include an explicit UTC offset")
    if not EPHEMERIS_START_YEAR <= civil_datetime.year <= EPHEMERIS_END_YEAR:
        raise ValueError(
            f"{EPHEMERIS_ID} supports civil years {EPHEMERIS_START_YEAR}-{EPHEMERIS_END_YEAR}"
        )
    timescale, ephemeris = skyfield_resources()
    instant = timescale.from_datetime(civil_datetime.astimezone(UTC))
    right_ascension, _, _ = ephemeris["earth"].at(instant).observe(ephemeris["sun"]).apparent().radec(epoch="date")
    apparent_clock_hours = (12 + instant.gast + longitude / 15 - right_ascension.hours) % 24
    civil_clock_hours = (
        civil_datetime.hour
        + civil_datetime.minute / 60
        + civil_datetime.second / 3600
        + civil_datetime.microsecond / 3_600_000_000
    )
    correction_hours = ((apparent_clock_hours - civil_clock_hours + 12) % 24) - 12
    return civil_datetime + timedelta(hours=correction_hours)
