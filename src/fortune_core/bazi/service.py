from __future__ import annotations

from datetime import datetime

from lunar_python import Solar

from fortune_core.models import (
    BaziSnapshot,
    BirthInput,
    GreatLuckPeriod,
    GreatLuckStart,
    Pillars,
)
from fortune_core.time_location import apparent_solar_datetime

PROFILE_ID = "bazi-zi-ping-apparent-solar-v1"
YANG_STEMS = frozenset({"甲", "丙", "戊", "庚", "壬"})


def _source_datetime(birth: BirthInput) -> tuple[datetime, str, str]:
    if birth.use_apparent_solar_time:
        if birth.apparent_solar_datetime is not None:
            return birth.apparent_solar_datetime, "apparent_solar", "provided"
        return apparent_solar_datetime(birth.civil_datetime, birth.longitude), "apparent_solar", "jpl_de440s"
    return birth.civil_datetime, "civil", "civil"


def _direction(year_pillar: str, sex: str) -> str:
    is_yang_year = year_pillar[0] in YANG_STEMS
    return "forward" if (sex == "male") == is_yang_year else "reverse"


def _great_luck_periods(yun, timezone) -> tuple[GreatLuckPeriod, ...]:
    start_solar = yun.getStartSolar()
    start_template = datetime(
        start_solar.getYear(),
        start_solar.getMonth(),
        start_solar.getDay(),
        start_solar.getHour(),
        start_solar.getMinute(),
        start_solar.getSecond(),
        tzinfo=timezone,
    )
    periods: list[GreatLuckPeriod] = []
    for decade in yun.getDaYun(10)[1:]:
        start = start_template.replace(year=decade.getStartYear())
        next_start = start_template.replace(year=decade.getStartYear() + 10)
        periods.append(
            GreatLuckPeriod(
                pillar=decade.getGanZhi(),
                start_datetime=start,
                end_datetime=next_start,
            )
        )
    return tuple(periods)


def calculate_bazi(birth: BirthInput) -> BaziSnapshot:
    """Produce a Zi Ping four-pillar snapshot from an explicit time basis.

    lunar-python is deliberately a second implementation during v1. Its output is
    pinned by golden tests; first-party astronomical/calendar adapters will replace
    this implementation only after parity is demonstrated.
    """
    calculation_datetime, basis, apparent_source = _source_datetime(birth)
    solar = Solar.fromYmdHms(
        calculation_datetime.year,
        calculation_datetime.month,
        calculation_datetime.day,
        calculation_datetime.hour,
        calculation_datetime.minute,
        calculation_datetime.second,
    )
    lunar = solar.getLunar()
    eight_char = lunar.getEightChar()
    eight_char.setSect(1)
    pillars = Pillars(
        year=eight_char.getYear(),
        month=eight_char.getMonth(),
        day=eight_char.getDay(),
        hour=eight_char.getTime(),
    )
    direction = _direction(pillars.year, birth.sex_for_rule)
    # lunar-python derives the direction from biological/rule gender plus the
    # annual stem polarity.  Passing the desired direction here is incorrect
    # for male Yin-year charts.
    gender_code = 1 if birth.sex_for_rule == "male" else 0
    yun = eight_char.getYun(gender_code)
    # Index zero is the pre-luck interval; index one starts the first decade.
    first_decade = yun.getDaYun(2)[1]
    great_luck_periods = _great_luck_periods(yun, calculation_datetime.tzinfo)
    return BaziSnapshot(
        profile_id=PROFILE_ID,
        input_time_basis=basis,
        apparent_solar_source=apparent_source,
        calculation_datetime=calculation_datetime,
        pillars=pillars,
        lunar_date=lunar.toString(),
        great_luck_start=GreatLuckStart(
            years=yun.getStartYear(),
            months=yun.getStartMonth(),
            days=yun.getStartDay(),
            direction=direction,
            first_pillar=first_decade.getGanZhi(),
        ),
        great_luck_periods=great_luck_periods,
        warnings=(
            ["user-provided apparent solar time was not cross-verified"]
            if apparent_source == "provided"
            else []
        ),
        verification_status=(
            "verified" if basis == "apparent_solar" and apparent_source == "jpl_de440s" else "ambiguous"
        ),
    )
