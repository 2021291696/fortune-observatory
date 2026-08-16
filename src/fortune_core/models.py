from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BirthInput(StrictRequestModel):
    civil_datetime: datetime
    timezone_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9._+-]+(?:/[A-Za-z0-9._+-]+)*$",
    )
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    sex_for_rule: Literal["male", "female"]
    apparent_solar_datetime: datetime | None = None
    use_apparent_solar_time: bool = True

    @field_validator("civil_datetime", "apparent_solar_datetime")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if not 1849 <= value.year <= 2150:
                raise ValueError("datetime year must be between 1849 and 2150")
            if value.tzinfo is None:
                raise ValueError("datetime must include an explicit UTC offset")
        return value

    @model_validator(mode="after")
    def require_time_basis(self) -> "BirthInput":
        try:
            zone = ZoneInfo(self.timezone_id)
        except ZoneInfoNotFoundError as error:
            raise ValueError(f"unknown IANA timezone: {self.timezone_id}") from error

        resolved_civil = self.civil_datetime.astimezone(zone)
        if (
            resolved_civil.replace(tzinfo=None) != self.civil_datetime.replace(tzinfo=None)
            or resolved_civil.utcoffset() != self.civil_datetime.utcoffset()
        ):
            raise ValueError(
                "civil_datetime UTC offset does not match timezone_id at that local time"
            )
        return self


class Pillars(BaseModel):
    year: str
    month: str
    day: str
    hour: str


class HiddenStem(BaseModel):
    stem: str
    ten_god: str


class PillarDetail(BaseModel):
    """Per-pillar Zi Ping detail: ten god, hidden stems, nayin."""

    pillar: str
    ten_god: str
    hidden_stems: tuple[HiddenStem, ...]
    nayin: str


class GreatLuckStart(BaseModel):
    years: int
    months: int
    days: int
    direction: Literal["forward", "reverse"]
    first_pillar: str


class GreatLuckPeriod(BaseModel):
    pillar: str
    start_datetime: datetime
    end_datetime: datetime
    start_age: int
    end_age: int


class BaziSnapshot(BaseModel):
    system: Literal["bazi"] = "bazi"
    profile_id: str
    input_time_basis: Literal["civil", "apparent_solar"]
    apparent_solar_source: Literal["provided", "jpl_de440s", "civil"]
    calculation_datetime: datetime
    pillars: Pillars
    pillar_details: tuple[PillarDetail, ...] = ()
    lunar_date: str
    great_luck_start: GreatLuckStart
    great_luck_periods: tuple[GreatLuckPeriod, ...]
    warnings: list[str] = []
    verification_status: Literal["verified", "ambiguous", "unsupported"]


class ZiweiPalace(BaseModel):
    name: str
    stem: str
    branch: str
    is_body_palace: bool
    decadal_range: tuple[int, int]
    minor_limit_ages: tuple[int, ...]
    major_stars: tuple[str, ...]
    major_star_brightness: tuple[tuple[str, str], ...]
    minor_stars: tuple[str, ...]


class ZiweiBirthMutagen(BaseModel):
    star: str
    mutagen: Literal["禄", "权", "科", "忌"]


class ZiweiFlyingMutagen(BaseModel):
    from_branch: str
    stem: str
    mutagen: Literal["禄", "权", "科", "忌"]
    star: str
    to_branch: str
    is_self: bool


class ZiweiSnapshot(BaseModel):
    lunar_month: int
    hour_branch: str
    life_branch: str
    body_branch: str
    five_elements_bureau: int
    year_stem: str
    birth_mutagens: tuple[ZiweiBirthMutagen, ...]
    palaces: tuple[ZiweiPalace, ...]
    flying_mutagens: tuple[ZiweiFlyingMutagen, ...] = ()
    verification_status: Literal["verified", "ambiguous", "unsupported"]


class ZiweiMutagenPlacement(BaseModel):
    star: str
    mutagen: Literal["禄", "权", "科", "忌"]
    palace_branch: str
    palace_name: str


class ZiweiDecadalLimit(BaseModel):
    branch: str
    stem: str
    start_age: int
    end_age: int
    is_childhood: bool
    mutagens: tuple[ZiweiMutagenPlacement, ...]


class ZiweiFlowingStar(BaseModel):
    star: str
    branch: str


class ZiweiYearlySnapshot(BaseModel):
    year_pillar: str
    nominal_age: int
    life_branch: str
    yearly_mutagens: tuple[ZiweiMutagenPlacement, ...]
    decadal: ZiweiDecadalLimit
    flowing_stars: tuple[ZiweiFlowingStar, ...]


class ZiweiAnnualPalace(BaseModel):
    name: str
    branch: str


class ZiweiAnnualTransitSnapshot(BaseModel):
    target_date: date
    year_pillar: str
    life_branch: str
    palaces: tuple[ZiweiAnnualPalace, ...]
    verification_status: Literal["verified", "ambiguous", "unsupported"]


class QizhengBodySnapshot(BaseModel):
    body: Literal["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"]
    longitude_deg: float
    latitude_deg: float
    longitude_rate_deg_per_day: float
    motion: Literal["direct", "retrograde"]


class QizhengTraditionalBody(BaseModel):
    body: Literal[
        "sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn",
        "rahu", "ketu", "apogee", "ziqi",
    ]
    longitude_deg: float
    longitude_rate_deg_per_day: float
    motion: Literal["direct", "retrograde"]
    mansion: str
    mansion_offset_deg: float


class QizhengTraditionalHouses(BaseModel):
    life_branch: str
    body_branch: str
    houses: tuple[tuple[str, str], ...]


class QizhengTraditionalSnapshot(BaseModel):
    profile_id: str
    anchor: Literal["j2000_mean_ecliptic"]
    bodies: tuple[QizhengTraditionalBody, ...]
    houses: QizhengTraditionalHouses | None = None
    notes: tuple[str, ...] = ()
    scope_limits: tuple[str, ...]
    verification_status: Literal["verified", "ambiguous", "unsupported"]


class QizhengSnapshot(BaseModel):
    profile_id: str
    ephemeris_id: str
    ephemeris_datetime: datetime
    bodies: tuple[QizhengBodySnapshot, ...]
    traditional: QizhengTraditionalSnapshot | None = None
    scope_limits: tuple[str, ...]
    verification_status: Literal["verified", "ambiguous", "unsupported"]


class TimeTraceSnapshot(BaseModel):
    timezone_id: str
    tzdb_version: str
    resolved_fold: Literal[0, 1]
    longitude: float
    latitude: float
    civil_datetime: datetime
    utc_datetime: datetime
    local_mean_solar_datetime: datetime
    apparent_solar_datetime: datetime | None
    apparent_solar_source: Literal["provided", "jpl_de440s", "civil"]
    ephemeris_id: str
    ephemeris_sha256: str


class TransitFact(BaseModel):
    fact_id: str
    relation: Literal["branch_clash", "branch_combination", "branch_same"]
    natal_pillar: str
    transit_pillar: str


class DailyTransitSnapshot(BaseModel):
    transit_date: date
    day_pillar: str
    facts: tuple[TransitFact, ...]
    verification_status: Literal["verified", "ambiguous", "unsupported"]


class TransitWindowSnapshot(BaseModel):
    start_date: date
    end_date: date
    daily: tuple[DailyTransitSnapshot, ...]
    verification_status: Literal["verified", "ambiguous", "unsupported"]


class TransitLayerSnapshot(BaseModel):
    period: Literal["great_luck", "year", "month", "day"]
    pillar: str
    facts: tuple[TransitFact, ...]


class SignalSnapshot(BaseModel):
    signal_id: str
    system: Literal["bazi", "ziwei", "qizheng"]
    direction: Literal["support", "tension", "neutral"]
    strength: Literal["core", "secondary", "edge"]
    rule_id: str
    fact_ids: tuple[str, ...]


class InsightSnapshot(BaseModel):
    insight_id: str
    title: str
    summary: str
    action: str
    fact_ids: tuple[str, ...]


class TransitSnapshot(BaseModel):
    transit_date: date
    layers: tuple[TransitLayerSnapshot, ...]
    ziwei_annual: ZiweiAnnualTransitSnapshot
    signals: tuple[SignalSnapshot, ...]
    insights: tuple[InsightSnapshot, ...]
    verification_status: Literal["verified", "ambiguous", "unsupported"]


class ChartResponse(BaseModel):
    bazi: BaziSnapshot
    ziwei: ZiweiSnapshot
    qizheng: QizhengSnapshot
    time_trace: TimeTraceSnapshot
    natal_insights: tuple[InsightSnapshot, ...]
    trace_id: str


class DailyTransitRequest(StrictRequestModel):
    birth: BirthInput
    transit_date: date

    @field_validator("transit_date")
    @classmethod
    def require_supported_date(cls, value: date) -> date:
        if not 1849 <= value.year <= 2150:
            raise ValueError("transit date year must be between 1849 and 2150")
        return value


class DailyTransitResponse(BaseModel):
    transit: DailyTransitSnapshot
    trace_id: str
    ziwei_yearly: ZiweiYearlySnapshot | None = None


class TransitWindowRequest(StrictRequestModel):
    birth: BirthInput
    start_date: date
    end_date: date

    @field_validator("start_date", "end_date")
    @classmethod
    def require_supported_date(cls, value: date) -> date:
        if not 1849 <= value.year <= 2150:
            raise ValueError("transit date year must be between 1849 and 2150")
        return value

    @model_validator(mode="after")
    def validate_window(self) -> "TransitWindowRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if (self.end_date - self.start_date).days > 31:
            raise ValueError("transit window cannot exceed 32 calendar days")
        return self


class TransitWindowResponse(BaseModel):
    transit: TransitWindowSnapshot
    trace_id: str


class TransitRequest(StrictRequestModel):
    birth: BirthInput
    transit_date: date

    @field_validator("transit_date")
    @classmethod
    def require_supported_date(cls, value: date) -> date:
        if not 1849 <= value.year <= 2150:
            raise ValueError("transit date year must be between 1849 and 2150")
        return value


class TransitResponse(BaseModel):
    transit: TransitSnapshot
    trace_id: str
