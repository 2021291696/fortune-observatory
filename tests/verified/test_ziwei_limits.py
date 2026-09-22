"""Table-driven checks for the yearly Ziwei limit engine (frozen iztro 2.6.1 profile)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from fortune_core.models import BirthInput, DailyTransitRequest
from fortune_core.ziwei.limits import CHANG_QU_BY_STEM, calculate_yearly_limit
from fortune_core.ziwei.palaces import BRANCHES_FROM_YIN, calculate_palaces

CHINA_STANDARD_TIME = timezone(timedelta(hours=8))


def _birth(year: int, month: int, day: int, hour: int, sex: str = "male") -> BirthInput:
    moment = datetime(year, month, day, hour, 0, 0, tzinfo=CHINA_STANDARD_TIME)
    return BirthInput(
        civil_datetime=moment,
        apparent_solar_datetime=moment,
        timezone_id="Asia/Shanghai",
        longitude=116.4,
        latitude=39.9,
        sex_for_rule=sex,
    )


def test_flowing_chang_qu_table_follows_year_stem() -> None:
    assert BRANCHES_FROM_YIN[CHANG_QU_BY_STEM["甲"][0]] == "巳"
    assert BRANCHES_FROM_YIN[CHANG_QU_BY_STEM["甲"][1]] == "酉"
    assert BRANCHES_FROM_YIN[CHANG_QU_BY_STEM["癸"][0]] == "卯"
    assert BRANCHES_FROM_YIN[CHANG_QU_BY_STEM["癸"][1]] == "亥"


def test_yearly_limit_luanyu_xixi_and_mutagen_placement() -> None:
    birth = _birth(2000, 1, 1, 8)
    snapshot = calculate_palaces(birth)
    # 2026 = 丙午年（立春后取 6 月），虚岁 27。
    actual = calculate_yearly_limit(snapshot, birth, date(2026, 6, 15))
    assert actual.year_pillar == "丙午"
    assert actual.nominal_age == 27
    # 丙干四化：天同禄、天机权、文昌科、廉贞忌。
    assert [entry.star for entry in actual.yearly_mutagens] == ["天同", "天机", "文昌", "廉贞"]
    for entry in actual.yearly_mutagens:
        assert entry.palace_branch and entry.palace_name
    # 流禄在丙干禄存位（巳）。
    placements = {star.star: star.branch for star in actual.flowing_stars}
    assert placements["流禄"] == "巳"
    assert placements["流羊"] == "午"
    assert placements["流陀"] == "辰"
    # 午年红鸾在卯逆数：午→酉，天喜在卯。
    assert placements["流鸾"] == "酉"
    assert placements["流喜"] == "卯"
    # 大限已入运（27 岁），飞宫干四化齐全。
    assert not actual.decadal.is_childhood
    assert len(actual.decadal.mutagens) == 4


def test_childhood_limit_before_bureau_age() -> None:
    birth = _birth(2024, 5, 5, 10)
    snapshot = calculate_palaces(birth)
    actual = calculate_yearly_limit(snapshot, birth, date(2025, 3, 3))
    assert actual.nominal_age == 2
    assert actual.decadal.is_childhood


def test_yearly_limit_rejects_target_date_before_birth() -> None:
    # 审计回归：早于生日的行运日期曾把虚岁算成 <= 0，童年限运查表取负
    # 索引——轻则错宫 200，重则 IndexError 逃出 except ValueError 成 500。
    birth = _birth(2024, 5, 5, 10)
    snapshot = calculate_palaces(birth)
    with pytest.raises(ValueError):
        calculate_yearly_limit(snapshot, birth, date(2024, 3, 3))
    with pytest.raises(ValueError):
        # 出生 7 年前：旧路径下 nominal_age = -6，IndexError 窗口。
        calculate_yearly_limit(snapshot, birth, date(2017, 6, 15))


def test_daily_transit_request_rejects_date_before_birth() -> None:
    # 请求边界 422 守卫：与引擎层兜底等价，提前在 pydantic 层拒绝。
    birth = _birth(2024, 5, 5, 10)
    with pytest.raises(ValueError):
        DailyTransitRequest(birth=birth, transit_date=date(2024, 3, 3))
