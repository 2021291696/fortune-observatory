from datetime import datetime

import pytest
from pydantic import ValidationError

from fortune_core.models import BirthInput
from fortune_core.time_location import CivilTimeError, normalize_civil_time


def test_rejects_spring_forward_gap() -> None:
    with pytest.raises(CivilTimeError, match="nonexistent"):
        normalize_civil_time(datetime(2024, 3, 10, 2, 30), "America/New_York")


def test_requires_fold_for_fall_back_overlap() -> None:
    local = datetime(2024, 11, 3, 1, 30)
    with pytest.raises(CivilTimeError, match="requires an explicit fold"):
        normalize_civil_time(local, "America/New_York")
    first = normalize_civil_time(local, "America/New_York", fold=0)
    second = normalize_civil_time(local, "America/New_York", fold=1)
    assert first.utcoffset() != second.utcoffset()
    assert first.astimezone().astimezone(first.tzinfo).replace(tzinfo=None) == local


def test_supports_non_whole_hour_offset() -> None:
    resolved = normalize_civil_time(datetime(2025, 1, 1, 12, 0), "Asia/Kathmandu")
    assert resolved.utcoffset().total_seconds() == 5.75 * 3600


def test_birth_input_rejects_offset_that_disagrees_with_iana_timezone() -> None:
    with pytest.raises(ValidationError, match="does not match timezone_id"):
        BirthInput(
            civil_datetime=datetime.fromisoformat("2025-01-01T12:00:00+09:00"),
            timezone_id="Asia/Shanghai",
            longitude=121.0,
            latitude=31.0,
            sex_for_rule="female",
            use_apparent_solar_time=False,
        )


def test_f007_birth_input_rejects_dst_overlap_without_fold() -> None:
    with pytest.raises(ValidationError, match="fold|ambiguous|overlap"):
        BirthInput(
            civil_datetime=datetime.fromisoformat("2024-11-03T01:30:00-04:00"),
            timezone_id="America/New_York",
            longitude=-74.0,
            latitude=40.7,
            sex_for_rule="male",
            use_apparent_solar_time=False,
        )
