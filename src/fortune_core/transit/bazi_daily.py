from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from lunar_python import Solar

from fortune_core.models import TransitLayerSnapshot
from fortune_core.signals import build_transit_signals
from fortune_core.ziwei import calculate_annual_palaces


CLASHES = frozenset({frozenset(pair) for pair in (("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"), ("辰", "戌"), ("巳", "亥"))})
COMBINATIONS = frozenset({frozenset(pair) for pair in (("子", "丑"), ("寅", "亥"), ("卯", "戌"), ("辰", "酉"), ("巳", "申"), ("午", "未"))})


@dataclass(frozen=True)
class TransitFact:
    fact_id: str
    relation: str
    natal_pillar: str
    transit_pillar: str


@dataclass(frozen=True)
class DailyTransit:
    transit_date: date
    day_pillar: str
    facts: tuple[TransitFact, ...]
    verification_status: str


@dataclass(frozen=True)
class TransitWindow:
    start_date: date
    end_date: date
    daily: tuple[DailyTransit, ...]
    verification_status: str


@dataclass(frozen=True)
class TransitLayer:
    period: str
    pillar: str
    facts: tuple[TransitFact, ...]


@dataclass(frozen=True)
class Transit:
    transit_date: date
    layers: tuple[TransitLayer, ...]
    ziwei_annual: object
    verification_status: str
    signals: tuple
    insights: tuple


def _facts(period: str, pillar: str, natal_pillars: tuple[str, str, str, str]) -> tuple[TransitFact, ...]:
    facts: list[TransitFact] = []
    for index, natal in enumerate(natal_pillars):
        branches = frozenset((natal[1], pillar[1]))
        if branches in CLASHES:
            relation = "branch_clash"
        elif branches in COMBINATIONS:
            relation = "branch_combination"
        elif natal[1] == pillar[1]:
            relation = "branch_same"
        else:
            continue
        facts.append(TransitFact(f"{period}-{relation}-{index}", relation, natal, pillar))
    return tuple(facts)


def calculate_daily_transit(transit_date: date, natal_pillars: tuple[str, str, str, str]) -> DailyTransit:
    """Return deterministic daily stem-branch relations, never an interpretation.

    Each fact names both operands so later narrative code can cite it without
    inferring new chart values. The calendar implementation remains pinned to
    lunar-python until the first-party astronomical calendar reaches parity.
    """
    lunar = Solar.fromYmd(transit_date.year, transit_date.month, transit_date.day).getLunar()
    day_pillar = lunar.getDayInGanZhi()
    return DailyTransit(transit_date, day_pillar, _facts("daily", day_pillar, natal_pillars), "verified")


def calculate_transit_window(
    start_date: date,
    end_date: date,
    natal_pillars: tuple[str, str, str, str],
) -> TransitWindow:
    """Return an inclusive calendar window of deterministic daily facts."""
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    if (end_date - start_date).days > 31:
        raise ValueError("transit window cannot exceed 32 calendar days")
    daily = tuple(
        calculate_daily_transit(start_date + timedelta(days=offset), natal_pillars)
        for offset in range((end_date - start_date).days + 1)
    )
    return TransitWindow(start_date, end_date, daily, "verified")


def calculate_transit(
    transit_date: date,
    natal_pillars: tuple[str, str, str, str],
    great_luck_pillar: str | None = None,
) -> Transit:
    """Return Ganzhi facts for the target date at the explicit local-noon convention."""
    lunar = Solar.fromYmdHms(
        transit_date.year,
        transit_date.month,
        transit_date.day,
        12,
        0,
        0,
    ).getLunar()
    eight_char = lunar.getEightChar()
    eight_char.setSect(1)
    layer_values = [
        ("year", eight_char.getYear()),
        ("month", eight_char.getMonth()),
        ("day", eight_char.getDay()),
    ]
    if great_luck_pillar is not None:
        layer_values.insert(0, ("great_luck", great_luck_pillar))
    layers = tuple(
        TransitLayer(period, pillar, _facts(period, pillar, natal_pillars))
        for period, pillar in layer_values
    )
    signal_layers = tuple(
        TransitLayerSnapshot(
            period=layer.period,
            pillar=layer.pillar,
            facts=tuple(
                {
                    "fact_id": fact.fact_id,
                    "relation": fact.relation,
                    "natal_pillar": fact.natal_pillar,
                    "transit_pillar": fact.transit_pillar,
                }
                for fact in layer.facts
            ),
        )
        for layer in layers
    )
    signals, insights = build_transit_signals(signal_layers)
    return Transit(
        transit_date,
        layers,
        calculate_annual_palaces(transit_date),
        "verified",
        signals,
        insights,
    )
