"""命宫/身宫/十二宫（七政四余传统层 alpha）。

口径（qizheng-traditional-alpha-v1）：
- 命宫 = 从太阳所在宫支起生时，顺数至卯，卯落之宫即命宫；
  身宫 = 同法数至酉（恒为命宫对宫）。
- 十二宫自命宫逆布（果老星宗通行次序：命财兄田子女奴妻疾迁官福相）。
"""

from __future__ import annotations

from dataclasses import dataclass

BRANCHES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
HOUSE_NAMES = (
    "命宫", "财帛", "兄弟", "田宅", "子女", "奴仆",
    "夫妻", "疾厄", "迁移", "官禄", "福德", "相貌",
)


@dataclass(frozen=True)
class HousePlacement:
    name: str
    branch: str


@dataclass(frozen=True)
class HouseLayout:
    life_branch: str
    body_branch: str
    houses: tuple[HousePlacement, ...]


def arrange_houses(sun_branch: str, hour_branch: str) -> HouseLayout:
    """依太阳宫支与生时宫支排命身十二宫。"""
    sun = BRANCHES.index(sun_branch)
    hour = BRANCHES.index(hour_branch)
    life = (sun + BRANCHES.index("卯") - hour) % 12
    body = (sun + BRANCHES.index("酉") - hour) % 12
    houses = tuple(
        HousePlacement(HOUSE_NAMES[index], BRANCHES[(life - index) % 12])
        for index in range(12)
    )
    return HouseLayout(BRANCHES[life], BRANCHES[body], houses)
