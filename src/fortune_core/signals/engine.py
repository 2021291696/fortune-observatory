"""Deterministic, fact-grounded interpretation aids.

This layer never computes a chart and never ranks a person's prospects.  It
only turns declared chart facts into small, reviewable prompts using the
language constraints inherited from the fortune-telling skill.
"""

from __future__ import annotations

from fortune_core.models import (
    BaziSnapshot,
    InsightSnapshot,
    QizhengSnapshot,
    SignalSnapshot,
    TransitLayerSnapshot,
    ZiweiSnapshot,
)

_PERIOD_LABELS = {
    "great_luck": "大运",
    "year": "流年",
    "month": "流月",
    "day": "流日",
}


def build_natal_insights(
    bazi: BaziSnapshot,
    ziwei: ZiweiSnapshot,
    qizheng: QizhengSnapshot,
) -> tuple[InsightSnapshot, ...]:
    """Describe the available sources without inferring an outcome from them."""
    return (
        InsightSnapshot(
            insight_id="natal-bazi-time-basis",
            title="先确认时间基准，再阅读本命结构",
            summary=(
                f"八字以{bazi.input_time_basis}时间计算四柱；日柱{bazi.pillars.day}"
                "只作为后续关系判断的参照，不单独推出人生结论。"
            ),
            action="若出生时间只精确到时辰或接近换日、节气，请先核对时间，再比较候选盘。",
            fact_ids=("bazi.time_basis", "bazi.day_pillar"),
        ),
        InsightSnapshot(
            insight_id="natal-ziwei-structure",
            title="紫微用宫位与星曜描述另一组结构",
            summary=(
                f"当前命宫在{ziwei.life_branch}，身宫在{ziwei.body_branch}；"
                "它与八字不是可相加的分数，而是等待同一领域、同一方向、同一来源时再交叉核对的语言。"
            ),
            action="把不同体系分别记录；只有证据指向同一件具体事情时，才把它们放在一起讨论。",
            fact_ids=("ziwei.life_palace", "ziwei.body_palace"),
        ),
        InsightSnapshot(
            insight_id="natal-qizheng-scope",
            title="七政当前只提供物理天体坐标",
            summary=(
                f"七政使用{qizheng.ephemeris_id}在出生民用时刻计算七体位置，"
                "传统宫位、限运与动态判断尚未开放。"
            ),
            action="把这部分视为待复核的坐标资料，不把它当作对未来的确定判断。",
            fact_ids=("qizheng.ephemeris_datetime", "qizheng.scope_limits"),
        ),
    )


def build_transit_signals(
    layers: tuple[TransitLayerSnapshot, ...],
) -> tuple[tuple[SignalSnapshot, ...], tuple[InsightSnapshot, ...]]:
    """Turn branch relations into bounded observation prompts with fact IDs."""
    signals: list[SignalSnapshot] = []
    insights: list[InsightSnapshot] = []
    for layer in layers:
        layer_fact = f"transit.{layer.period}.pillar"
        period_label = _PERIOD_LABELS[layer.period]
        signals.append(
            SignalSnapshot(
                signal_id=f"{layer.period}-time-axis",
                system="bazi",
                direction="neutral",
                strength="edge",
                rule_id="bazi-transit-local-noon-v1",
                fact_ids=(layer_fact,),
            )
        )
        clashes = tuple(fact for fact in layer.facts if fact.relation == "branch_clash")
        combinations = tuple(
            fact for fact in layer.facts if fact.relation in {"branch_combination", "branch_same"}
        )
        if clashes:
            ids = tuple(fact.fact_id for fact in clashes)
            signals.append(
                SignalSnapshot(
                    signal_id=f"{layer.period}-branch-tension",
                    system="bazi",
                    direction="tension",
                    strength="core" if layer.period in {"year", "month"} else "secondary",
                    rule_id="bazi-branch-clash-v1",
                    fact_ids=ids,
                )
            )
            insights.append(
                InsightSnapshot(
                    insight_id=f"{layer.period}-tension-practice",
                    title=f"{period_label}层出现需要拆解的张力",
                    summary=(
                        f"{period_label}柱{layer.pillar}与本命存在已定义的地支冲。"
                        "这描述的是需要协调的关系，不是吉凶或结果预言。"
                    ),
                    action="把重要选择拆成可逆的小步骤，先写清楚约束与下一步，再决定是否扩大投入。",
                    fact_ids=(layer_fact, *ids),
                )
            )
        if combinations:
            ids = tuple(fact.fact_id for fact in combinations)
            signals.append(
                SignalSnapshot(
                    signal_id=f"{layer.period}-branch-alignment",
                    system="bazi",
                    direction="support",
                    strength="secondary",
                    rule_id="bazi-branch-combination-v1",
                    fact_ids=ids,
                )
            )
            insights.append(
                InsightSnapshot(
                    insight_id=f"{layer.period}-alignment-practice",
                    title=f"{period_label}层有可利用的既有连接",
                    summary=(
                        f"{period_label}柱{layer.pillar}与本命出现同支或地支合。"
                        "它只提示可观察的衔接点，不代表保证发生的机会。"
                    ),
                    action="优先整理已有关系、资料或流程，把能复用的一件事落实为本周期的最小行动。",
                    fact_ids=(layer_fact, *ids),
                )
            )
        if not layer.facts:
            insights.append(
                InsightSnapshot(
                    insight_id=f"{layer.period}-no-defined-relation",
                    title=f"{period_label}层没有已定义的地支关系",
                    summary=(
                        f"{period_label}柱{layer.pillar}未检测到本规则包定义的冲、合或同支。"
                        "这不是“没有影响”，只是当前引擎没有可引用的关系事实。"
                    ),
                    action="不必强行给这个时间层下结论；回到现实目标、信息和可控步骤。",
                    fact_ids=(layer_fact,),
                )
            )
    return tuple(signals), tuple(insights)
