"""七政四余传统层 alpha（qizheng-traditional-alpha-v1）verified 单测。

数据来源标注：
- 距星黄经锚点：HYG v4.1（Hipparcos）交叉校验 28/28 ≤12″
  （scripts/cross_check_mansions_hyg.py，2026-08-16 运行）。
- 四余公式常数：Meeus《Astronomical Algorithms》47.1/47.4/47.7（Chapront ELP）。
- 命身宫规则：果老星宗通行安法；样本值未对在线排盘复核（candidates_not_golden）。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fortune_core.qizheng.four_remainders import (
    four_remainders,
    mean_ascending_node,
    mean_lunar_apogee,
)
from fortune_core.qizheng.houses import BRANCHES, HOUSE_NAMES, arrange_houses
from fortune_core.qizheng.mansions import MANSION_STARS, mansion_of, mansion_table
from fortune_core.qizheng.traditional import _precession_deg, calculate_traditional

UTC = timezone.utc


def test_mansion_table_order_and_widths():
    table = mansion_table()
    order = "".join(entry.name for entry in table)
    assert order == "壁奎娄胃昴毕觜参井鬼柳星张翼轸角亢氐房心尾箕斗牛女虚危室"
    longitudes = [entry.longitude_deg for entry in table]
    widths = [
        (b - a) % 360.0 for a, b in zip(longitudes, longitudes[1:] + [longitudes[0]])
    ]
    assert all(width > 0.5 for width in widths), widths
    assert sum(widths) == pytest.approx(360.0, abs=0.01)


def test_determinative_star_anchor_longitudes():
    """锚星黄经 vs HYG v4.1（≤12″ 时 ≤0.0035°；此处放宽到 0.01°）。"""
    table = {entry.name: entry for entry in mansion_table()}
    anchors = {
        "角": 203.841,  # α Vir Spica
        "亢": 214.494,  # κ Vir（HYG proper 名 Kang）
        "危": 333.352,  # α Aqr Sadalmelik，回归：南纬 0° 区符号不得丢失
        "觜": 83.606,   # φ¹ Ori（明清调整后距星）
        "参": 84.681,   # ζ Ori Alnitak
        "张": 155.691,  # υ¹ Hya（HYG proper 名 Zhang）
    }
    for name, expected in anchors.items():
        assert table[name].longitude_deg == pytest.approx(expected, abs=0.01), name


def test_mansion_ingress_boundaries():
    # 觜界 [83.606, 84.681)：跨过觜距星即换宿，跨过参距星再换。
    assert mansion_of(83.61)[0].name == "觜"
    assert mansion_of(84.20)[0].name == "觜"
    assert mansion_of(84.69)[0].name == "参"
    # 环回：轸界尾段（>190.726）一直到角界（203.841）之前。
    assert mansion_of(200.0)[0].name == "轸"
    assert mansion_of(203.9)[0].name == "角"


def test_palace_branches_by_mansion():
    table = {entry.name: entry for entry in mansion_table()}
    assert table["角"].branch == "辰"
    assert table["翼"].branch == "巳"
    assert table["柳"].branch == "午"
    assert table["井"].branch == "未"
    assert table["觜"].branch == "申"
    assert table["胃"].branch == "酉"
    assert table["奎"].branch == "戌"
    assert table["室"].branch == "亥"
    assert table["女"].branch == "子"
    assert table["斗"].branch == "丑"
    assert table["尾"].branch == "寅"
    assert table["房"].branch == "卯"


def test_four_remainders_j2000_and_rates():
    j2000 = datetime(2000, 1, 1, 12, 0, tzinfo=UTC)
    # Meeus 47.7 常数项即 J2000 平升交点公认值。
    assert mean_ascending_node(j2000) == pytest.approx(125.0445, abs=0.001)
    # 平远地点 = L'(0) − M'(0) + 180（Meeus 47.1/47.4 常数项推导）。
    assert mean_lunar_apogee(j2000) == pytest.approx(263.353, abs=0.01)

    remainders = four_remainders(j2000)
    assert remainders["计都"][0] == pytest.approx((remainders["罗睺"][0] + 180) % 360, abs=1e-6)
    assert remainders["紫炁"][0] == pytest.approx((remainders["月孛"][0] + 180) % 360, abs=1e-6)
    # 行度：罗计 −0.05295°/日（1934.136°/世纪），孛炁 +0.111°/日。
    assert remainders["罗睺"][1] == pytest.approx(-0.05295, abs=0.0005)
    assert remainders["月孛"][1] == pytest.approx(0.1113, abs=0.001)


def test_precession_frame_reduction_magnitude():
    assert _precession_deg(0.266) == pytest.approx(0.372, abs=0.005)
    assert _precession_deg(-0.5) < 0


def test_arrange_houses_textbook_samples():
    # 太阳在子、酉时生 → 命宫午（口算样例：子(酉)…午(卯)）。
    assert arrange_houses("子", "酉").life_branch == "午"
    # 身宫恒为命宫对宫。
    layout = arrange_houses("午", "午")
    assert layout.life_branch == "卯"
    assert layout.body_branch == "酉"
    # 十二宫自命宫逆布：财帛在命宫前一支，十二宫名次序固定。
    assert [house.branch for house in layout.houses] == [
        BRANCHES[(BRANCHES.index("卯") - i) % 12] for i in range(12)
    ]
    assert [house.name for house in layout.houses] == list(HOUSE_NAMES)
    assert len({house.branch for house in layout.houses}) == 12


def test_traditional_snapshot_fixture_2026_08_16():
    """集成 fixture（candidates_not_golden：未对在线排盘，仅 de440s+口径自洽）。"""
    instant = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)
    snap = calculate_traditional(instant, "午", 39.9042, 116.4074)
    by_key = {body.body: body for body in snap.bodies}
    assert len(snap.bodies) == 11
    assert by_key["sun"].mansion == "柳"
    assert by_key["sun"].mansion_offset_deg == pytest.approx(12.98, abs=0.01)
    assert by_key["sun"].mansion_branch == "午"
    assert by_key["rahu"].mansion == "虚"
    assert by_key["rahu"].mansion_branch == "子"
    assert by_key["rahu"].motion == "retrograde"
    assert by_key["apogee"].motion == "direct"
    # 帧一致性：罗睺 J2000 帧黄经 = 平黄经 − p_A。
    raw = mean_ascending_node(instant)
    precession = _precession_deg((instant - datetime(2000, 1, 1, 12, tzinfo=UTC)).total_seconds() / 86400 / 36525)
    assert by_key["rahu"].longitude_deg == pytest.approx((raw - precession) % 360, abs=0.01)
    assert snap.houses is not None
    assert snap.houses.life_branch == "卯"
    assert snap.houses.body_branch == "酉"
    assert snap.anchor == "j2000_mean_ecliptic"
    assert "dynamic_fortune_limited" in snap.scope_limits
    assert snap.verification_status == "ambiguous"


def test_traditional_3b_fixture_2026_08_16():
    """3B：昼夜/命主/庙旺/恩难/洞微大限（candidates_not_golden，口径自洽）。"""
    instant = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)  # 北京时间 20:00，八月日落后
    night = calculate_traditional(instant, "午", 39.9042, 116.4074)
    assert night.is_day_chart is False
    noon = calculate_traditional(datetime(2026, 8, 16, 4, 0, tzinfo=UTC), "辰", 39.9042, 116.4074)
    assert noon.is_day_chart is True
    # 命宫卯 → 宫主火星；身宫酉 → 宫主金星。
    assert night.life_lord == "mars"
    assert night.body_lord == "venus"
    # 太阳入柳宿（午宫）→ 居垣（日垣在午）。
    by_key = {body.body: body for body in night.bodies}
    assert by_key["sun"].dignity == "居垣"
    # 命主火星（火）五行：木生火=恩，水克火=难，火克金=用，火生土=仇。
    assert by_key["jupiter"].relation == "恩"
    assert by_key["mercury"].relation == "难"
    assert by_key["venus"].relation == "用"
    assert by_key["saturn"].relation == "仇"
    # 出童限与行限表。
    assert night.childhood_exit_age == pytest.approx(10 + by_key["sun"].mansion_offset_deg / 3, abs=0.05)
    assert len(night.limit_rows) == 12
    assert [row.palace for row in night.limit_rows][:4] == ["命宫", "相貌", "福德", "官禄"]
    assert [row.branch for row in night.limit_rows][:3] == ["卯", "辰", "巳"]
    assert sum(row.years for row in night.limit_rows) == pytest.approx(100.5)
    assert [row.segment for row in night.limit_rows] == ["昼"] * 6 + ["夜"] * 6


def test_mansion_star_table_matches_rule_pack_dedication():
    """距星身份抽查（维基二十八宿表 + 明清调整）：表内注释与规则包口径一致。"""
    stars = {name: star for name, _branch, star, *_ in MANSION_STARS}
    assert stars["奎"] == "ζ And"
    assert stars["昴"] == "17 Tau"
    assert stars["觜"] == "φ¹ Ori"
    assert stars["参"] == "ζ Ori"
    assert stars["氐"] == "α² Lib"
