# tests/verified/test_life_phase_buckets.py
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))
import app as api_module


def palace(start: int, end: int, name: str = "命") -> SimpleNamespace:
    return SimpleNamespace(name=name, branch="子", major_stars=["紫微"], decadal_range=(start, end))


TWELVE = [palace(i * 10, i * 10 + 9, f"宫{i}") for i in range(12)]
# 0-9, 10-19, ... 110-119


def test_age_21_keeps_two_upcoming_and_drops_the_rest() -> None:
    buckets = api_module._decadal_buckets(TWELVE, 21)
    assert [p.decadal_range for p in buckets["past"]] == [(0, 9), (10, 19)]
    assert buckets["current"].decadal_range == (20, 29)
    assert [p.decadal_range for p in buckets["upcoming"]] == [(30, 39), (40, 49)]
    assert [p.decadal_range for p in buckets["dropped"]] == [
        (50, 59), (60, 69), (70, 79), (80, 89), (90, 99), (100, 109), (110, 119),
    ]


def test_age_55_still_caps_upcoming_at_two() -> None:
    buckets = api_module._decadal_buckets(TWELVE, 55)
    assert len(buckets["past"]) == 5
    assert buckets["current"].decadal_range == (50, 59)
    assert len(buckets["upcoming"]) == 2
    assert len(buckets["dropped"]) == 4


def test_childhood_first_limit_has_no_past() -> None:
    buckets = api_module._decadal_buckets(TWELVE, 5)
    assert buckets["past"] == []
    assert buckets["current"].decadal_range == (0, 9)
    assert len(buckets["upcoming"]) == 2


def test_age_past_last_limit_uses_last_as_current() -> None:
    buckets = api_module._decadal_buckets(TWELVE, 130)
    assert buckets["current"].decadal_range == (110, 119)
    assert buckets["upcoming"] == []
    assert buckets["dropped"] == []
    assert len(buckets["past"]) == 11


def test_decadal_fact_rows_skip_dropped_limits() -> None:
    buckets = api_module._decadal_buckets(TWELVE, 21)
    rows = api_module._decadal_fact_rows(buckets)
    blob = "。".join(rows)
    assert "已过" in blob and "当前" in blob and "未到" in blob
    assert "80-89岁" not in blob
    assert "110-119岁" not in blob
    assert "30-39岁" in blob and "40-49岁" in blob
