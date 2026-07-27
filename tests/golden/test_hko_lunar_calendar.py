import json
from datetime import date
from pathlib import Path

from lunar_python import Solar


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "golden"
    / "hko_lunar_calendar_boundaries-v1.json"
)


def test_lunar_python_matches_frozen_hko_month_boundaries() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["source"]["publisher"] == "Hong Kong Observatory"
    for case in fixture["fixtures"]:
        civil_date = date.fromisoformat(case["civil_date"])
        lunar = Solar.fromYmd(civil_date.year, civil_date.month, civil_date.day).getLunar()
        assert (lunar.getYear(), lunar.getMonth(), lunar.getDay()) == (
            case["lunar_year"],
            case["lunar_month"],
            case["lunar_day"],
        )
        assert lunar.getYearInGanZhi() == case["lunar_year_ganzhi"]
