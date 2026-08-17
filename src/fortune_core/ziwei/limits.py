"""Yearly Ziwei limits: annual mutagens, decadal mutagens and flowing stars.

Rule profile stays frozen against iztro 2.5.8 (`horoscopeDivide: 'exact'`,
`ageDivide: 'normal'`): the year pillar follows the exact 立春 divide at local
noon, nominal age counts calendar years since birth plus one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from lunar_python import Solar

from fortune_core.models import BirthInput

from .palaces import (
    BRANCHES_FROM_YIN,
    BRANCHES_FROM_ZI,
    BIRTH_MUTAGENS,
    KUI_YUE_BY_STEM,
    LU_BRANCH_BY_STEM,
    MA_BRANCH_BY_YEAR_BRANCH,
    MUTAGEN_NAMES,
    ZiweiPalaceSnapshot,
    palace_stem,
    _star_to_branch,
)

# 流昌/流曲按流年天干（寅起索引）：昌、曲。
CHANG_QU_BY_STEM = {
    "甲": (3, 7), "乙": (4, 6), "丙": (6, 4), "戊": (6, 4),
    "丁": (7, 3), "己": (7, 3), "庚": (9, 1), "辛": (10, 0),
    "壬": (0, 10), "癸": (1, 9),
}

# 童限（未入五行局起运岁前的虚岁宫位）。
CHILDHOOD_LIMIT_PALACES = ("命宫", "财帛", "疾厄", "夫妻", "福德", "官禄")


@dataclass(frozen=True)
class ZiweiMutagenPlacement:
    star: str
    mutagen: str
    palace_branch: str
    palace_name: str


@dataclass(frozen=True)
class ZiweiDecadalLimit:
    branch: str
    stem: str
    start_age: int
    end_age: int
    is_childhood: bool
    mutagens: tuple[ZiweiMutagenPlacement, ...]


@dataclass(frozen=True)
class ZiweiFlowingStar:
    star: str
    branch: str


@dataclass(frozen=True)
class ZiweiYearlySnapshot:
    year_pillar: str
    nominal_age: int
    life_branch: str
    yearly_mutagens: tuple[ZiweiMutagenPlacement, ...]
    decadal: ZiweiDecadalLimit
    flowing_stars: tuple[ZiweiFlowingStar, ...]


def _year_pillar_at_noon(target_date: date) -> str:
    lunar = Solar.fromYmdHms(target_date.year, target_date.month, target_date.day, 12, 0, 0).getLunar()
    eight_char = lunar.getEightChar()
    eight_char.setSect(1)
    return eight_char.getYear()


def _placements(stem: str, snapshot: ZiweiPalaceSnapshot, star_to_branch: dict[str, str]) -> tuple[ZiweiMutagenPlacement, ...]:
    name_by_branch = {palace.branch: palace.name for palace in snapshot.palaces}
    return tuple(
        ZiweiMutagenPlacement(
            star=star,
            mutagen=mutagen,
            palace_branch=star_to_branch.get(star, ""),
            palace_name=name_by_branch.get(star_to_branch.get(star, ""), ""),
        )
        for star, mutagen in zip(BIRTH_MUTAGENS[stem], MUTAGEN_NAMES, strict=True)
    )


def _locate_decadal(
    snapshot: ZiweiPalaceSnapshot, nominal_age: int, star_to_branch: dict[str, str]
) -> ZiweiDecadalLimit:
    for palace in snapshot.palaces:
        start, end = palace.decadal_range
        if start <= nominal_age <= end:
            branch_index = BRANCHES_FROM_YIN.index(palace.branch)
            stem = palace_stem(snapshot.year_stem, branch_index)
            return ZiweiDecadalLimit(
                branch=palace.branch,
                stem=stem,
                start_age=start,
                end_age=end,
                is_childhood=False,
                mutagens=_placements(stem, snapshot, star_to_branch),
            )
    name = CHILDHOOD_LIMIT_PALACES[min(nominal_age, len(CHILDHOOD_LIMIT_PALACES)) - 1]
    palace = next(item for item in snapshot.palaces if item.name == name)
    branch_index = BRANCHES_FROM_YIN.index(palace.branch)
    return ZiweiDecadalLimit(
        branch=palace.branch,
        stem=palace_stem(snapshot.year_stem, branch_index),
        start_age=1,
        end_age=snapshot.five_elements_bureau - 1,
        is_childhood=True,
        mutagens=_placements(palace_stem(snapshot.year_stem, branch_index), snapshot, star_to_branch),
    )


def _flowing_stars(year_stem: str, year_branch: str) -> tuple[ZiweiFlowingStar, ...]:
    kui, yue = KUI_YUE_BY_STEM[year_stem]
    chang, qu = CHANG_QU_BY_STEM[year_stem]
    lu = LU_BRANCH_BY_STEM[year_stem]
    ma = MA_BRANCH_BY_YEAR_BRANCH[year_branch]
    luan = (1 - BRANCHES_FROM_ZI.index(year_branch)) % 12
    xi = (luan + 6) % 12
    # 年解：解神从戌上起子，逆数至太岁（iztro getNianjieIndex 同源）。
    nianjie_name = ("戌", "酉", "申", "未", "午", "巳", "辰", "卯", "寅", "丑", "子", "亥")[
        BRANCHES_FROM_ZI.index(year_branch)
    ]
    nianjie = BRANCHES_FROM_YIN.index(nianjie_name)
    entries = (
        ("流魁", kui), ("流钺", yue), ("流昌", chang), ("流曲", qu),
        ("流禄", lu), ("流羊", (lu + 1) % 12), ("流陀", (lu - 1) % 12),
        ("流马", ma), ("流鸾", luan), ("流喜", xi), ("年解", nianjie),
    )
    return tuple(ZiweiFlowingStar(star=star, branch=BRANCHES_FROM_YIN[index]) for star, index in entries)


def calculate_yearly_limit(
    snapshot: ZiweiPalaceSnapshot,
    birth: BirthInput,
    target_date: date,
) -> ZiweiYearlySnapshot:
    year_pillar = _year_pillar_at_noon(target_date)
    year_stem, year_branch = year_pillar[0], year_pillar[1]
    nominal_age = target_date.year - birth.civil_datetime.year + 1
    star_to_branch = _star_to_branch(snapshot)
    return ZiweiYearlySnapshot(
        year_pillar=year_pillar,
        nominal_age=nominal_age,
        life_branch=year_branch,
        yearly_mutagens=_placements(year_stem, snapshot, star_to_branch),
        decadal=_locate_decadal(snapshot, nominal_age, star_to_branch),
        flowing_stars=_flowing_stars(year_stem, year_branch),
    )


__all__ = [
    "ZiweiYearlySnapshot",
    "ZiweiDecadalLimit",
    "ZiweiMutagenPlacement",
    "ZiweiFlowingStar",
    "calculate_yearly_limit",
    "CHANG_QU_BY_STEM",
]
