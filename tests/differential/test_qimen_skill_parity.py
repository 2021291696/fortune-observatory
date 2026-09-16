"""奇门排盘差分校验：项目引擎（fortune_core.qimen）vs skill 脚本（skills/qimen-dunjia/scripts/qimen_cli.py）。

仓库内 skill 副本是第二实现（与本地 ~/.agents/skills/qimen-dunjia 独立）；
两侧在相同输入下输出 JSON 必须逐字段一致。改任一侧必须同步另一侧并重跑本文件。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from fortune_core.qimen import build_output

PROJECT_ROOT = Path(__file__).parents[2]
SKILL_CLI = PROJECT_ROOT / "skills" / "qimen-dunjia" / "scripts" / "qimen_cli.py"


def _payload(time_input: str, *, timezone: str = "Asia/Shanghai", country: str = "中国",
             city: str = "上海", calendar_type: str = "solar") -> dict:
    return {
        "question_type": "事业",
        "question_goal": "能不能动",
        "time_input": time_input,
        "calendar_type": calendar_type,
        "location": {"country": country, "city": city, "timezone": timezone},
        "ruleset": "mainline-cn-v1",
    }


# (time_input, 覆盖点)
FIXED_CASES: tuple[tuple[str, str], ...] = (
    ("2026-03-24 10:30", "基准例（skill 示例：阳遁1局）"),
    ("2026-07-15 14:00", "夏至后阴遁"),
    ("2025-12-21 12:00", "冬至交节附近（节气边界提醒）"),
    ("2025-12-23 09:00", "冬至后阳遁"),
    ("2026-04-10 08:00", "清明节气内另一三元"),
    ("2026-09-16 12:00", "当前月份常规例"),
    ("2026-06-05 06:30", "芒种节气内"),
    ("1988-06-11 23:30", "夜子时历史例"),
)


def _scan_case(warning_marker: str) -> dict:
    """程序化扫描出覆盖特定分支的用例：时干甲入盘 / 旬首或时干落中宫寄坤。"""
    for day_offset in range(0, 90):
        for hour in (23, 12):
            time_input = f"2026-03-{1 + day_offset:02d} {hour:02d}:00" if day_offset < 31 else (
                f"2026-04-{1 + day_offset - 31:02d} {hour:02d}:00"
            )
            if day_offset >= 61:
                time_input = f"2026-05-{1 + day_offset - 61:02d} {hour:02d}:00"
            out = build_output(_payload(time_input))
            if any(warning_marker in warning for warning in out["warnings"]):
                return _payload(time_input)
    raise AssertionError(f"90 天内未扫描到命中「{warning_marker}」的用例")


SCAN_CASES: tuple[tuple[dict, str], ...] = (
    (_scan_case("时干为甲"), "时干为甲，按旬首所遁之仪入盘"),
    (_scan_case("寄坤处理"), "旬首或时干落中宫，寄坤路径"),
)

# 固定结构用例：海外时区 / 海外缺时区回退 / 农历输入
SPECIAL_CASES: tuple[tuple[dict, str], ...] = (
    (_payload("2026-03-24 10:30", timezone="America/New_York", country="美国", city="纽约"), "海外明确时区"),
    (_payload("2026-03-24 10:30", timezone="", country="美国", city="纽约"), "海外缺时区回退默认"),
    ({
        "question_type": "求财",
        "question_goal": "这笔交易能不能谈成",
        "time_input": {"year": 2026, "month": 6, "day": 15, "hour": 10, "minute": 30, "second": 0},
        "calendar_type": "lunar",
        "is_leap_month": True,
        "location": {"country": "中国", "city": "成都", "timezone": ""},
        "ruleset": "mainline-cn-v1",
    }, "农历输入（闰月）"),
)


def _skill_output(payload: dict) -> dict:
    with tempfile.TemporaryDirectory() as td:
        input_path = os.path.join(td, "input.json")
        output_path = os.path.join(td, "output.json")
        Path(input_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        subprocess.run(
            [sys.executable, str(SKILL_CLI), "--input", input_path, "--output", output_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        )
        return json.loads(Path(output_path).read_text(encoding="utf-8"))


def _assert_parity(payload: dict, note: str) -> None:
    engine = build_output(payload)
    skill = _skill_output(payload)
    assert engine == skill, f"差分不一致（{note}）：engine != skill"


def test_qimen_skill_parity_fixed_cases() -> None:
    assert SKILL_CLI.exists(), "skills/qimen-dunjia/scripts/qimen_cli.py 不在仓库内"
    for time_input, note in FIXED_CASES:
        _assert_parity(_payload(time_input), f"{time_input} {note}")


def test_qimen_skill_parity_scan_cases() -> None:
    for payload, note in SCAN_CASES:
        _assert_parity(payload, note)


def test_qimen_skill_parity_special_cases() -> None:
    for payload, note in SPECIAL_CASES:
        _assert_parity(payload, note)


def test_qimen_scan_cases_hit_expected_branches() -> None:
    for payload, note in SCAN_CASES:
        out = build_output(payload)
        assert out["warnings"], f"扫描用例应带警告（{note}）"
    out = build_output(_payload("2026-03-24 10:30"))
    assert out["chart"]["dun_type"] == "阳遁"
    assert out["chart"]["ju_number"] == 1
