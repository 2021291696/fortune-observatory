"""七政四余庙旺（居垣/升殿）、宫主命主身主、五行恩难仇用（3B）。

口径（qizheng-traditional-alpha-v2，来源见规则包）：
- 宫主（子丑土、寅亥木、卯戌火、辰酉金、巳申水、午日、未月）——果老星宗通行。
- 居垣 = 星在其五行本宫（水巳申、金辰酉、火卯戌、木寅亥、土子丑、日午、月未）；
  四余随五行落垣（罗火→卯戌、计土→子丑、孛水→巳申、炁木→寅亥）为派生约定。
- 升殿 = 躔本属宿：木角斗奎井、金亢牛娄鬼、土氐女胃柳、日房虚昴星、
  月心危毕张、火尾室觜翼、水箕壁参轸（《七政四余天星择日讲义》）。四余升殿无统一源，不做。
- 五行：五星本行 + 炁木、孛水、罗火、计土；日月为君主不参与生克（辅从/掩蔽论）。
- 恩难仇用相对命主星五行：恩=生我、难=克我、用=我克（财）、仇=我生（泄）；
  恩/难定义有典源（杰赫星命辑古），用/仇为通行读法（派生标注）。
"""

from __future__ import annotations

# 宫支 → 宫主星（body key）
PALACE_LORDS: dict[str, str] = {
    "子": "saturn", "丑": "saturn",
    "寅": "jupiter", "亥": "jupiter",
    "卯": "mars", "戌": "mars",
    "辰": "venus", "酉": "venus",
    "巳": "mercury", "申": "mercury",
    "午": "sun", "未": "moon",
}

# 星 → 五行（日月不参与生克，故无条目）
BODY_ELEMENTS: dict[str, str] = {
    "jupiter": "wood", "mars": "fire", "saturn": "earth",
    "venus": "metal", "mercury": "water",
    "ziqi": "wood", "apogee": "water", "rahu": "fire", "ketu": "earth",
}

# 星 → 居垣宫支（四余为五行派生）
HOME_BRANCHES: dict[str, tuple[str, ...]] = {
    "sun": ("午",),
    "moon": ("未",),
    "mercury": ("巳", "申"),
    "venus": ("辰", "酉"),
    "mars": ("卯", "戌"),
    "jupiter": ("寅", "亥"),
    "saturn": ("子", "丑"),
    "rahu": ("卯", "戌"),
    "ketu": ("子", "丑"),
    "apogee": ("巳", "申"),
    "ziqi": ("寅", "亥"),
}

# 宿 → 七政（日/月单列，与五行键区分）
MANSION_LORDS: dict[str, str] = {
    # 木：角斗奎井
    "角": "jupiter", "斗": "jupiter", "奎": "jupiter", "井": "jupiter",
    # 金：亢牛娄鬼
    "亢": "venus", "牛": "venus", "娄": "venus", "鬼": "venus",
    # 土：氐女胃柳
    "氐": "saturn", "女": "saturn", "胃": "saturn", "柳": "saturn",
    # 日：房虚昴星
    "房": "sun", "虚": "sun", "昴": "sun", "星": "sun",
    # 月：心危毕张
    "心": "moon", "危": "moon", "毕": "moon", "张": "moon",
    # 火：尾室觜翼
    "尾": "fire", "室": "fire", "觜": "fire", "翼": "fire",
    # 水：箕壁参轸
    "箕": "water", "壁": "water", "参": "water", "轸": "water",
}

_GENERATES = {  # 生：键生值
    "wood": "fire", "fire": "earth", "earth": "metal",
    "metal": "water", "water": "wood",
}


def dignity_of(body: str, branch: str, mansion: str) -> str | None:
    """居垣优先，其次升殿；无则 None。四余升殿不做。"""
    if branch in HOME_BRANCHES.get(body, ()):  # type: ignore[arg-type]
        return "居垣"
    if body in ("sun", "moon"):
        lord = MANSION_LORDS.get(mansion)
        if lord == body:
            return "升殿"
        return None
    lord = MANSION_LORDS.get(mansion)
    if lord is not None and BODY_ELEMENTS.get(body) == lord:
        return "升殿"
    return None


def relation_to_lord(body: str, lord_body: str) -> str | None:
    """恩难仇用：相对命主星五行。恩=生我、难=克我、用=我克（财）、仇=我生（泄）。

    日月与命主为日月时返回 None（君主不参与生克）。
    """
    base = BODY_ELEMENTS.get(lord_body)
    other = BODY_ELEMENTS.get(body)
    if base is None or other is None or body == lord_body:
        return None
    # 克：木克土、土克水、水克火、火克金、金克木
    _OVERCOMES = {"wood": "earth", "earth": "water", "water": "fire",
                  "fire": "metal", "metal": "wood"}
    if _GENERATES[other] == base:
        return "恩"  # 生我者恩
    if _OVERCOMES[other] == base:
        return "难"  # 克我者难
    if _OVERCOMES[base] == other:
        return "用"  # 我克者为用（财）
    return "仇"  # 我生者为仇（泄）


def palace_lord(branch: str) -> str:
    return PALACE_LORDS[branch]
