from __future__ import annotations

from dataclasses import dataclass

from lunar_python import LunarYear, Solar

from fortune_core.models import BirthInput
from fortune_core.time_location import apparent_solar_datetime

BRANCHES_FROM_YIN = ("寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑")
PALACE_ORDER = ("命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄", "迁移", "交友", "官禄", "田宅", "福德", "父母")
YANG_STEMS = frozenset({"甲", "丙", "戊", "庚", "壬"})
HOUR_BRANCH_INDEX = {"子": 0, "丑": 1, "寅": 2, "卯": 3, "辰": 4, "巳": 5, "午": 6, "未": 7, "申": 8, "酉": 9, "戌": 10, "亥": 11}

STEMS = ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")
BRANCHES_FROM_ZI = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
TIGER_START_STEM = {
    "甲": "丙", "己": "丙", "乙": "戊", "庚": "戊", "丙": "庚",
    "辛": "庚", "丁": "壬", "壬": "壬", "戊": "甲", "癸": "甲",
}
FIVE_ELEMENTS_BUREAU = (3, 4, 2, 6, 5)
ZIWEI_GROUP = ((0, "紫微"), (1, "天机"), (3, "太阳"), (4, "武曲"), (5, "天同"), (8, "廉贞"))
TIANFU_GROUP = ((0, "天府"), (1, "太阴"), (2, "贪狼"), (3, "巨门"), (4, "天相"), (5, "天梁"), (6, "七杀"), (10, "破军"))
BRIGHTNESS_LABELS = {"wang": "旺", "miao": "庙", "de": "得", "li": "利", "ping": "平", "xian": "陷", "bu": "不"}
MAJOR_BRIGHTNESS = {
    "紫微": ("wang", "wang", "de", "wang", "miao", "miao", "wang", "wang", "de", "wang", "ping", "miao"),
    "天机": ("de", "wang", "li", "ping", "miao", "xian", "de", "wang", "li", "ping", "miao", "xian"),
    "太阳": ("wang", "miao", "wang", "wang", "wang", "de", "de", "xian", "bu", "xian", "xian", "bu"),
    "武曲": ("de", "li", "miao", "ping", "wang", "miao", "de", "li", "miao", "ping", "wang", "miao"),
    "天同": ("li", "ping", "ping", "miao", "xian", "bu", "wang", "ping", "ping", "miao", "wang", "bu"),
    "廉贞": ("miao", "ping", "li", "xian", "ping", "li", "miao", "ping", "li", "xian", "ping", "li"),
    "天府": ("miao", "de", "miao", "de", "wang", "miao", "de", "wang", "miao", "de", "miao", "miao"),
    "太阴": ("wang", "xian", "xian", "xian", "bu", "bu", "li", "bu", "wang", "miao", "miao", "miao"),
    "贪狼": ("ping", "li", "miao", "xian", "wang", "miao", "ping", "li", "miao", "xian", "wang", "miao"),
    "巨门": ("miao", "miao", "xian", "wang", "wang", "bu", "miao", "miao", "xian", "wang", "wang", "bu"),
    "天相": ("miao", "xian", "de", "de", "miao", "de", "miao", "xian", "de", "de", "miao", "miao"),
    "天梁": ("miao", "miao", "miao", "xian", "miao", "wang", "xian", "de", "miao", "xian", "miao", "wang"),
    "七杀": ("miao", "wang", "miao", "ping", "wang", "miao", "miao", "miao", "miao", "ping", "wang", "miao"),
    "破军": ("de", "xian", "wang", "ping", "miao", "wang", "de", "xian", "wang", "ping", "miao", "wang"),
}
MUTAGEN_NAMES = ("禄", "权", "科", "忌")
BIRTH_MUTAGENS = {
    "甲": ("廉贞", "破军", "武曲", "太阳"),
    "乙": ("天机", "天梁", "紫微", "太阴"),
    "丙": ("天同", "天机", "文昌", "廉贞"),
    "丁": ("太阴", "天同", "天机", "巨门"),
    "戊": ("贪狼", "太阴", "右弼", "天机"),
    "己": ("武曲", "贪狼", "天梁", "文曲"),
    "庚": ("太阳", "武曲", "太阴", "天同"),
    "辛": ("巨门", "太阳", "文曲", "文昌"),
    "壬": ("天梁", "紫微", "左辅", "武曲"),
    "癸": ("破军", "巨门", "太阴", "贪狼"),
}
LU_BRANCH_BY_STEM = {"甲": 0, "乙": 1, "丙": 3, "丁": 4, "戊": 3, "己": 4, "庚": 6, "辛": 7, "壬": 9, "癸": 10}
KUI_YUE_BY_STEM = {
    "甲": (11, 5), "乙": (10, 6), "丙": (9, 7), "丁": (9, 7), "戊": (11, 5),
    "己": (10, 6), "庚": (11, 5), "辛": (4, 0), "壬": (1, 3), "癸": (1, 3),
}
MA_BRANCH_BY_YEAR_BRANCH = {
    "寅": 6, "午": 6, "戌": 6, "申": 0, "子": 0, "辰": 0,
    "巳": 9, "酉": 9, "丑": 9, "亥": 3, "卯": 3, "未": 3,
}
HUO_LING_START_BY_YEAR_BRANCH = {
    "寅": (11, 1), "午": (11, 1), "戌": (11, 1), "申": (0, 8), "子": (0, 8), "辰": (0, 8),
    "巳": (1, 8), "酉": (1, 8), "丑": (1, 8), "亥": (7, 8), "卯": (7, 8), "未": (7, 8),
}


@dataclass(frozen=True)
class ZiweiPalace:
    name: str
    branch: str
    is_body_palace: bool
    decadal_range: tuple[int, int]
    minor_limit_ages: tuple[int, ...]
    major_stars: tuple[str, ...]
    major_star_brightness: tuple[tuple[str, str], ...]
    minor_stars: tuple[str, ...]


@dataclass(frozen=True)
class ZiweiBirthMutagen:
    star: str
    mutagen: str


@dataclass(frozen=True)
class ZiweiPalaceSnapshot:
    lunar_month: int
    hour_branch: str
    life_branch: str
    body_branch: str
    five_elements_bureau: int
    year_stem: str
    birth_mutagens: tuple[ZiweiBirthMutagen, ...]
    palaces: tuple[ZiweiPalace, ...]
    verification_status: str


def _time_index(hour: int) -> int:
    """Map a wall-clock hour to iztro's 0..12 early/late-zi index."""
    return 0 if hour == 0 else (hour + 1) // 2


def _profile_lunar_month(lunar_month: int, lunar_day: int, hour: int) -> int:
    """Apply this profile's `fix_leap=true` convention before palace math."""
    is_leap_month = lunar_month < 0
    month = abs(lunar_month)
    if is_leap_month and lunar_day > 15 and _time_index(hour) != 12:
        return month + 1
    return month


def _five_elements_bureau(lunar, life_index: int) -> int:
    """Return the five-elements bureau used by the Ziwei/Tianfu start rule."""
    year_stem = lunar.getYearGanExact()
    soul_stem = STEMS[(STEMS.index(TIGER_START_STEM[year_stem]) + life_index) % 10]
    life_branch = BRANCHES_FROM_YIN[life_index]
    stem_number = STEMS.index(soul_stem) // 2 + 1
    branch_number = (BRANCHES_FROM_ZI.index(life_branch) % 6) // 2 + 1
    combined = stem_number + branch_number
    while combined > 5:
        combined -= 5
    return FIVE_ELEMENTS_BUREAU[combined - 1]


def _lunar_month_days(lunar) -> int:
    signed_month = lunar.getMonth()
    for month in LunarYear.fromYear(lunar.getYear()).getMonths():
        if month.getMonth() == signed_month:
            return month.getDayCount()
    raise ValueError(f"could not find lunar month {signed_month}")


def _major_star_positions(lunar, life_index: int, hour: int) -> tuple[int, dict[int, tuple[str, ...]]]:
    """Calculate fourteen major stars using the frozen iztro 2.5.8 rule profile."""
    bureau = _five_elements_bureau(lunar, life_index)
    lunar_day = lunar.getDay()
    if _time_index(hour) == 12:
        lunar_day += 1
    max_days = _lunar_month_days(lunar)
    if lunar_day > max_days:
        lunar_day -= max_days

    offset = 0
    while (lunar_day + offset) % bureau:
        offset += 1
    quotient = ((lunar_day + offset) // bureau) % 12
    ziwei_index = quotient - 1
    ziwei_index = (ziwei_index + offset if offset % 2 == 0 else ziwei_index - offset) % 12
    tianfu_index = (-ziwei_index) % 12

    positions: dict[int, list[str]] = {index: [] for index in range(12)}
    for offset, star in ZIWEI_GROUP:
        positions[(ziwei_index - offset) % 12].append(star)
    for offset, star in TIANFU_GROUP:
        positions[(tianfu_index + offset) % 12].append(star)
    return bureau, {index: tuple(stars) for index, stars in positions.items()}


def _minor_star_positions(lunar, lunar_month: int, hour: int) -> dict[int, tuple[str, ...]]:
    """Calculate the fourteen traditional minor stars in the frozen rule profile."""
    time_index = _time_index(hour) % 12
    year_stem = lunar.getYearGanExact()
    year_branch = lunar.getYearZhiExact()
    positions: dict[int, list[str]] = {index: [] for index in range(12)}

    def put(index: int, star: str) -> None:
        positions[index % 12].append(star)

    put(2 + lunar_month - 1, "左辅")
    put(8 - (lunar_month - 1), "右弼")
    put(8 - time_index, "文昌")
    put(2 + time_index, "文曲")
    kui_index, yue_index = KUI_YUE_BY_STEM[year_stem]
    put(kui_index, "天魁")
    put(yue_index, "天钺")
    lu_index = LU_BRANCH_BY_STEM[year_stem]
    put(lu_index, "禄存")
    put(MA_BRANCH_BY_YEAR_BRANCH[year_branch], "天马")
    put(9 - time_index, "地空")
    put(9 + time_index, "地劫")
    huo_start, ling_start = HUO_LING_START_BY_YEAR_BRANCH[year_branch]
    put(huo_start + time_index, "火星")
    put(ling_start + time_index, "铃星")
    put(lu_index + 1, "擎羊")
    put(lu_index - 1, "陀罗")
    return {index: tuple(stars) for index, stars in positions.items()}


def _decadal_ranges(
    lunar,
    life_index: int,
    five_elements_bureau: int,
    sex_for_rule: str,
) -> dict[str, tuple[int, int]]:
    """Apply the frozen iztro 2.5.8 decade-palace profile.

    The direction is Yang-male/Yin-female forward, otherwise reverse; each
    palace carries a ten-year nominal-age range beginning at the five-elements
    bureau value.  These ranges are Ziwei limits, distinct from BaZi DaYun.
    """
    year_stem = lunar.getYearGanExact()
    forward = (sex_for_rule == "male") == (year_stem in YANG_STEMS)
    ranges: dict[str, tuple[int, int]] = {}
    for offset in range(12):
        index = (life_index + offset if forward else life_index - offset) % 12
        start_age = five_elements_bureau + 10 * offset
        ranges[BRANCHES_FROM_YIN[index]] = (start_age, start_age + 9)
    return ranges


def _minor_limit_ages(lunar, sex_for_rule: str) -> dict[str, tuple[int, ...]]:
    """Assign small-limit nominal ages with the frozen iztro 2.5.8 rule."""
    birth_year_branch = lunar.getYearZhiExact()
    if birth_year_branch in {"寅", "午", "戌"}:
        start_index = 2  # 辰
    elif birth_year_branch in {"申", "子", "辰"}:
        start_index = 8  # 戌
    elif birth_year_branch in {"巳", "酉", "丑"}:
        start_index = 5  # 未
    else:
        start_index = 11  # 丑, expressed in the 寅-origin index
    ages: dict[str, tuple[int, ...]] = {}
    for offset in range(12):
        index = (start_index + offset if sex_for_rule == "male" else start_index - offset) % 12
        ages[BRANCHES_FROM_YIN[index]] = tuple(12 * cycle + offset + 1 for cycle in range(10))
    return ages


def calculate_palaces(birth: BirthInput) -> ZiweiPalaceSnapshot:
    """Calculate 命宫/身宫 and twelve-palace mapping from declared time basis.

    The profile is `yin_month_forward_then_birth_hour_reverse` for 命宫 and
    `yin_month_forward_then_birth_hour_forward` for 身宫. It intentionally does
    not expose major/minor stars or limits before their differential suite passes.
    """
    moment = birth.civil_datetime
    if birth.use_apparent_solar_time:
        moment = birth.apparent_solar_datetime or apparent_solar_datetime(moment, birth.longitude)
    lunar = Solar.fromYmdHms(moment.year, moment.month, moment.day, moment.hour, moment.minute, moment.second).getLunar()
    lunar_month = _profile_lunar_month(lunar.getMonth(), lunar.getDay(), moment.hour)
    hour_branch = lunar.getTimeZhi()
    hour_index = HOUR_BRANCH_INDEX[hour_branch]
    month_index = lunar_month - 1
    life_index = (month_index - hour_index) % 12
    body_index = (month_index + hour_index) % 12
    bureau, major_star_positions = _major_star_positions(lunar, life_index, moment.hour)
    minor_star_positions = _minor_star_positions(lunar, lunar_month, moment.hour)
    decadal_ranges = _decadal_ranges(lunar, life_index, bureau, birth.sex_for_rule)
    minor_limit_ages = _minor_limit_ages(lunar, birth.sex_for_rule)
    year_stem = lunar.getYearGanExact()
    birth_mutagens = tuple(
        ZiweiBirthMutagen(star=star, mutagen=mutagen)
        for star, mutagen in zip(BIRTH_MUTAGENS[year_stem], MUTAGEN_NAMES, strict=True)
    )
    palaces = tuple(
        ZiweiPalace(
            name=name,
            branch=BRANCHES_FROM_YIN[(life_index - offset) % 12],
            is_body_palace=BRANCHES_FROM_YIN[(life_index - offset) % 12] == BRANCHES_FROM_YIN[body_index],
            decadal_range=decadal_ranges[BRANCHES_FROM_YIN[(life_index - offset) % 12]],
            minor_limit_ages=minor_limit_ages[BRANCHES_FROM_YIN[(life_index - offset) % 12]],
            major_stars=major_star_positions[(life_index - offset) % 12],
            major_star_brightness=tuple(
                (star, BRIGHTNESS_LABELS[MAJOR_BRIGHTNESS[star][(life_index - offset) % 12]])
                for star in major_star_positions[(life_index - offset) % 12]
            ),
            minor_stars=minor_star_positions[(life_index - offset) % 12],
        )
        for offset, name in enumerate(PALACE_ORDER)
    )
    return ZiweiPalaceSnapshot(
        lunar_month=lunar_month,
        hour_branch=hour_branch,
        life_branch=BRANCHES_FROM_YIN[life_index],
        body_branch=BRANCHES_FROM_YIN[body_index],
        five_elements_bureau=bureau,
        year_stem=year_stem,
        birth_mutagens=birth_mutagens,
        palaces=palaces,
        verification_status="verified" if birth.use_apparent_solar_time else "ambiguous",
    )
