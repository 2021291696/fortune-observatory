"""八字排盘差分校验：项目引擎（fortune_core）vs 社区 bazi skill（skills/bazi）。

skill 的 pai_pan.py 为纯标准库第二实现（jinchenma94/bazi-skill），
本项目引擎经 JPL 真太阳时与手工复核；两者在 civil 时间口径下四柱必须一致。
夜子时用例若暴露口径分歧，以项目引擎口径（ADR-0002/0003）为准并在此注明。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys

from fortune_core.bazi.service import calculate_bazi
from fortune_core.models import BirthInput

SKILL_PAI_PAN = Path(__file__).parents[2] / "skills" / "bazi" / "scripts" / "pai_pan.py"
CHINA_STANDARD_TIME = timezone(timedelta(hours=8))

# (solar, HH:MM, sex, 备注)
CASES: tuple[tuple[str, str, str, str], ...] = (
    ("1990-05-15", "12:00", "男", "基准例"),
    ("1984-02-02", "10:00", "男", "立春前年柱界"),
    ("1984-02-05", "10:00", "男", "立春后年柱界"),
    ("2023-03-25", "08:00", "女", "农历闰二月期间"),
    ("1988-06-11", "23:30", "男", "夜子时（日柱换日口径）"),
    ("2000-01-01", "00:30", "女", "早子时跨年"),
    ("1975-08-08", "06:15", "女", "常规例"),
    ("1999-04-05", "05:05", "男", "清明交节附近"),
    ("2010-08-07", "18:40", "女", "立秋交节附近"),
    ("2005-12-24", "00:05", "男", "冬至前后 civil 凌晨"),
)


def _skill_pillars(solar: str, hour: str, sex: str) -> tuple[str, str, str, str]:
    completed = subprocess.run(
        [sys.executable, str(SKILL_PAI_PAN), "--solar", solar, "--hour", hour, "--sex", sex],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    stems: list[str] = []
    branches: list[str] = []
    for line in completed.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("| 天干"):
            stems = [cell.strip() for cell in stripped.strip("|").split("|")[1:]]
        elif stripped.startswith("| 地支"):
            branches = [cell.strip() for cell in stripped.strip("|").split("|")[1:]]
    if len(stems) != 4 or len(branches) != 4:
        raise AssertionError(f"skill 四柱输出解析失败: {solar} {hour} {sex}")
    return tuple(
        stem + branch for stem, branch in zip(stems, branches)
    )  # type: ignore[return-value]


def _engine_pillars(solar: str, hour: str, sex: str) -> tuple[str, str, str, str]:
    year, month, day = (int(part) for part in solar.split("-"))
    hour_part, minute_part = (int(part) for part in hour.split(":"))
    moment = datetime(year, month, day, hour_part, minute_part, tzinfo=CHINA_STANDARD_TIME)
    birth = BirthInput(
        civil_datetime=moment,
        timezone_id="Etc/GMT-8",
        longitude=116.4,
        latitude=39.9,
        sex_for_rule="male" if sex == "男" else "female",
        use_apparent_solar_time=False,
    )
    snapshot = calculate_bazi(birth)
    return (snapshot.pillars.year, snapshot.pillars.month, snapshot.pillars.day, snapshot.pillars.hour)


def test_bazi_skill_parity_golden_cases() -> None:
    assert SKILL_PAI_PAN.exists(), "skills/bazi/scripts/pai_pan.py 不在仓库内"
    mismatches: list[str] = []
    for solar, hour, sex, note in CASES:
        skill_result = _skill_pillars(solar, hour, sex)
        engine_result = _engine_pillars(solar, hour, sex)
        if skill_result != engine_result:
            mismatches.append(
                f"{solar} {hour} {sex}（{note}）: "
                f"skill={skill_result} engine={engine_result}"
            )
    assert not mismatches, "八字差分不一致：\n" + "\n".join(mismatches)
