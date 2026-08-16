from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import random
import shutil
import subprocess

from fortune_core.models import BirthInput
from fortune_core.ziwei import calculate_annual_palaces, calculate_palaces


RUNTIME_DIR = Path(__file__).parent / "iztro_runtime"
TIME_INDEX_HOURS = (0, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23)
CHINA_STANDARD_TIME = timezone(timedelta(hours=8))


def _cases() -> list[dict[str, str | int]]:
    # Seeded PRNG on purpose (not secrets): differential fixtures must stay
    # reproducible byte-for-byte across runs; no security decision depends on it.
    generator = random.Random(20260721)
    # China observed daylight saving time before 1992. This fixture deliberately
    # keeps the +08:00 test offset inside the post-DST support window.
    start = date(1992, 1, 1)
    day_count = (date(2100, 1, 1) - start).days
    dates = [start + timedelta(days=generator.randrange(day_count)) for _ in range(80)]
    return [
        {"date": item.isoformat(), "time_index": index, "sex": sex}
        for item in dates
        for index in range(13)
        for sex in ("male", "female")
    ]


def _python_snapshot(item: dict[str, str | int]):
    moment = datetime.combine(
        date.fromisoformat(str(item["date"])),
        datetime.min.time(),
        tzinfo=CHINA_STANDARD_TIME,
    ).replace(hour=TIME_INDEX_HOURS[int(item["time_index"])])
    birth = BirthInput(
        civil_datetime=moment,
        apparent_solar_datetime=moment,
        timezone_id="Asia/Shanghai",
        longitude=116.4,
        latitude=39.9,
        sex_for_rule=str(item["sex"]),
    )
    return calculate_palaces(birth)


def test_iztro_2_5_8_palace_branch_parity_for_2080_charts() -> None:
    assert shutil.which("node") is not None, "Node.js is required for frozen iztro parity"
    cases = _cases()
    completed = subprocess.run(
        ["node", "batch-palaces.cjs"],
        cwd=RUNTIME_DIR,
        input=json.dumps(cases),
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
    )
    oracle = json.loads(completed.stdout)

    assert len(cases) == len(oracle) == 2_080
    for item, expected in zip(cases, oracle, strict=True):
        actual = _python_snapshot(item)
        assert actual.year_stem == expected["year_stem"], item
        assert actual.life_branch == expected["life_branch"], item
        assert actual.body_branch == expected["body_branch"], item
        assert sorted(palace.branch for palace in actual.palaces) == expected["palace_branches"]
        assert {
            palace.branch: list(palace.decadal_range)
            for palace in actual.palaces
        } == expected["decadal_ranges"], item
        assert {
            palace.branch: list(palace.minor_limit_ages)
            for palace in actual.palaces
        } == expected["minor_limit_ages"], item
        actual_major_stars = {
            palace.branch: sorted(palace.major_stars)
            for palace in actual.palaces
        }
        assert actual_major_stars == expected["major_stars"], item
        assert {
            palace.branch: [list(item) for item in palace.major_star_brightness]
            for palace in actual.palaces
        } == expected["major_star_brightness"], item
        actual_minor_stars = {
            palace.branch: sorted(palace.minor_stars)
            for palace in actual.palaces
        }
        assert actual_minor_stars == expected["minor_stars"], item
        assert [item.__dict__ for item in actual.birth_mutagens] == expected["birth_mutagens"], item
        annual = calculate_annual_palaces(date.fromisoformat(str(item["date"])))
        assert annual.year_pillar == expected["annual_year_pillar"], item
        assert [palace.name for palace in annual.palaces] == expected["annual_palaces"], item
