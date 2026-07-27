from __future__ import annotations

from datetime import date

from lunar_python import Solar

from fortune_core.models import ZiweiAnnualPalace, ZiweiAnnualTransitSnapshot

from .palaces import BRANCHES_FROM_YIN


# Annual palace terminology follows the frozen reference's traditional label.
ANNUAL_PALACE_ORDER = (
    "命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄",
    "迁移", "仆役", "官禄", "田宅", "福德", "父母",
)


def calculate_annual_palaces(target_date: date) -> ZiweiAnnualTransitSnapshot:
    """Calculate annual palace names using the explicit local-noon convention.

    Annual life palace is anchored to the year's earthly branch.  Palace names
    then proceed in the chart's inverse branch order from that branch.
    """
    lunar = Solar.fromYmdHms(
        target_date.year,
        target_date.month,
        target_date.day,
        12,
        0,
        0,
    ).getLunar()
    eight_char = lunar.getEightChar()
    eight_char.setSect(1)
    year_pillar = eight_char.getYear()
    life_branch = year_pillar[1]
    life_index = BRANCHES_FROM_YIN.index(life_branch)
    palaces = tuple(
        ZiweiAnnualPalace(
            branch=branch,
            name=ANNUAL_PALACE_ORDER[(life_index - index) % len(ANNUAL_PALACE_ORDER)],
        )
        for index, branch in enumerate(BRANCHES_FROM_YIN)
    )
    return ZiweiAnnualTransitSnapshot(
        target_date=target_date,
        year_pillar=year_pillar,
        life_branch=life_branch,
        palaces=palaces,
        verification_status="verified",
    )
