"""洞微大限（七政行限，3B）。

口径（qizheng-traditional-alpha-v2）：
- 出童限虚岁 = 10 + 太阳躔本宫度数/3（果老星宗站修正公式，不加月）。
  "太阳度数"取太阳在其所在宫支内离宫首（该宫支首宿距星）的黄经差，
  宫支按 3A 宿界口径（宽度不均，与均分 30° 派的差异记入口径）。
- 行限年数依《十二宫年分歌》（百度百科·七政四余 / 古今图书集成）：
  命15 相10 福11 官15 迁8 疾7 妻11 奴4.5 男(子女)4.5 田4.5 兄5 财5，
  合 100.5 年（果老星宗站·洞微百六限说：昼段命至疾厄 66 年、夜段夫妻至财帛 34.5 年）。
- 行限自命宫起顺宫支而行（命→相→福→官→迁→疾→妻→奴→男→田→兄→财）。
- 未做：竹罗三限、飞限、月限、行年细化（3C）。
"""

from __future__ import annotations

from fortune_core.qizheng.houses import BRANCHES
from fortune_core.qizheng.mansions import mansion_table

# (宫名, 年数, 昼夜段)
LIMIT_YEARS: tuple[tuple[str, float, str], ...] = (
    ("命宫", 15.0, "昼"),
    ("相貌", 10.0, "昼"),
    ("福德", 11.0, "昼"),
    ("官禄", 15.0, "昼"),
    ("迁移", 8.0, "昼"),
    ("疾厄", 7.0, "昼"),
    ("夫妻", 11.0, "夜"),
    ("奴仆", 4.5, "夜"),
    ("子女", 4.5, "夜"),
    ("田宅", 4.5, "夜"),
    ("兄弟", 5.0, "夜"),
    ("财帛", 5.0, "夜"),
)


def palace_start_longitudes() -> dict[str, float]:
    """各宫支首宿黄经（黄经升序中宫支切换处）。"""
    table = mansion_table()
    starts: dict[str, float] = {}
    count = len(table)
    for index, entry in enumerate(table):
        previous = table[(index - 1) % count]
        if previous.branch != entry.branch:
            starts.setdefault(entry.branch, entry.longitude_deg)
    return starts


def degree_in_palace(longitude_deg: float, branch: str) -> float:
    """天体离所在宫支宫首的黄经差（宫支按宿界，宽度不均）。"""
    return (longitude_deg - palace_start_longitudes()[branch]) % 360.0


def childhood_exit_age(sun_longitude_deg: float, sun_branch: str) -> float:
    """出童限虚岁 = 10 + 太阳躔本宫度数 / 3。"""
    return 10.0 + degree_in_palace(sun_longitude_deg, sun_branch) / 3.0


def limit_table(life_branch: str, exit_age: float) -> tuple[tuple[str, str, float, float, float, str], ...]:
    """行限表：(宫名, 宫支, 年数, 起虚岁, 止虚岁, 昼夜段)。"""
    life = BRANCHES.index(life_branch)
    rows = []
    age = exit_age
    for index, (name, years, segment) in enumerate(LIMIT_YEARS):
        branch = BRANCHES[(life + index) % 12]
        rows.append((name, branch, years, age, age + years, segment))
        age += years
    return tuple(rows)


def limit_at_age(life_branch: str, exit_age: float, nominal_age: float) -> tuple[str, str, str] | None:
    """虚岁所在限：(宫名, 宫支, 昼夜段)；童限期返回 None。"""
    if nominal_age < exit_age:
        return None
    for name, branch, _years, start, end, segment in limit_table(life_branch, exit_age):
        if start <= nominal_age < end:
            return name, branch, segment
    return None
