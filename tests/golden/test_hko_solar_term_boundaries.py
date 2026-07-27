import json
from datetime import datetime
from pathlib import Path

from fortune_core.bazi import calculate_bazi
from fortune_core.models import BirthInput


FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "golden"
    / "hko_solar_term_boundaries-v1.json"
)


def _pillars(value: str) -> tuple[str, str]:
    snapshot = calculate_bazi(
        BirthInput(
            civil_datetime=datetime.fromisoformat(value),
            timezone_id="Asia/Shanghai",
            longitude=120.0,
            latitude=30.0,
            sex_for_rule="male",
            use_apparent_solar_time=False,
        )
    )
    return snapshot.pillars.year, snapshot.pillars.month


def test_hko_lichun_boundaries_change_bazi_year_and_month_after_published_minute() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["source"]["publisher"] == "Hong Kong Observatory"
    for case in fixture["fixtures"]:
        assert _pillars(case["before_datetime"]) == (
            case["before_pillars"]["year"],
            case["before_pillars"]["month"],
        )
        assert _pillars(case["after_datetime"]) == (
            case["after_pillars"]["year"],
            case["after_pillars"]["month"],
        )
