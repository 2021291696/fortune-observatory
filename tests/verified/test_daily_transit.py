from datetime import date

from fortune_core.transit import calculate_daily_transit, calculate_transit


def test_daily_transit_returns_traceable_facts_only() -> None:
    transit = calculate_daily_transit(date(2026, 1, 1), ("乙酉", "戊子", "辛巳", "己亥"))
    assert transit.day_pillar == "乙亥"
    assert [(fact.relation, fact.natal_pillar) for fact in transit.facts] == [
        ("branch_clash", "辛巳"),
        ("branch_same", "己亥"),
    ]
    assert all(fact.fact_id.startswith("daily-") for fact in transit.facts)


def test_transit_snapshot_keeps_year_month_and_day_facts_separate() -> None:
    transit = calculate_transit(date(2026, 1, 1), ("乙酉", "戊子", "辛巳", "己亥"))
    assert [(layer.period, layer.pillar) for layer in transit.layers] == [
        ("year", "乙巳"), ("month", "戊子"), ("day", "乙亥"),
    ]
    assert [(fact.relation, fact.natal_pillar) for fact in transit.layers[0].facts] == [
        ("branch_same", "辛巳"), ("branch_clash", "己亥"),
    ]
