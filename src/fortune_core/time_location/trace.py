from __future__ import annotations

from datetime import timedelta, timezone
from zoneinfo import ZoneInfo

import tzdata

from fortune_core.models import BaziSnapshot, BirthInput, TimeTraceSnapshot
from fortune_core.time_location.apparent_solar import EPHEMERIS_ID, EPHEMERIS_SHA256

# datetime.UTC needs Python 3.11+; the SCF runtime is 3.10.
UTC = timezone.utc


def build_time_trace(birth: BirthInput, bazi: BaziSnapshot) -> TimeTraceSnapshot:
    """Expose every time basis used by the chart calculation.

    Local mean solar time is a longitude correction to the declared civil UTC
    offset.  It is displayed separately from apparent solar time so the user
    can inspect the equation-of-time contribution instead of treating the
    derived clock as an opaque input.
    """
    offset = birth.civil_datetime.utcoffset()
    if offset is None:  # BirthInput validation already rejects this path.
        raise ValueError("civil_datetime must include an explicit UTC offset")
    offset_hours = offset.total_seconds() / 3600
    local_mean = birth.civil_datetime + timedelta(
        hours=birth.longitude / 15 - offset_hours
    )
    apparent = (
        bazi.calculation_datetime
        if bazi.input_time_basis == "apparent_solar"
        else None
    )
    return TimeTraceSnapshot(
        timezone_id=birth.timezone_id,
        tzdb_version=tzdata.__version__,
        resolved_fold=birth.civil_datetime.astimezone(ZoneInfo(birth.timezone_id)).fold,
        longitude=birth.longitude,
        latitude=birth.latitude,
        civil_datetime=birth.civil_datetime,
        utc_datetime=birth.civil_datetime.astimezone(UTC),
        local_mean_solar_datetime=local_mean,
        apparent_solar_datetime=apparent,
        apparent_solar_source=bazi.apparent_solar_source,
        ephemeris_id=EPHEMERIS_ID,
        ephemeris_sha256=EPHEMERIS_SHA256,
    )
