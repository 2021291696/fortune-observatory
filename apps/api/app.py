"""Production API entrypoint for the verified v1 calculation path.

Run with PowerShell:
    $env:PYTHONPATH = "$PWD\\src"
    .\\.venv\\Scripts\\python.exe -m uvicorn app:app --app-dir apps/api
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, time as dtime, timedelta, timezone as tzone
from collections import Counter
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from security import RequestGuardMiddleware
from ai_explainer import (
    AiBudgetExceeded,
    AiConfigurationError,
    AiContextBundle,
    AiExplainRequest,
    AiExplainResponse,
    AiFact,
    AiProviderError,
    AiStatusResponse,
    build_signed_context,
    derive_context_group,
    explain_with_ai,
    provider_is_available,
)
from dreams.models import InterpretRequest, InterpretResponse, QuestionsRequest, QuestionsResponse
from dreams.service import generate_questions, interpret_dream_request

from fortune_core.bazi import active_great_luck, calculate_bazi
from fortune_core.models import (
    BirthInput,
    ChartResponse,
    DailyTransitRequest,
    DailyTransitResponse,
    DailyTransitSnapshot,
    TransitWindowRequest,
    TransitWindowResponse,
    TransitWindowSnapshot,
    TransitRequest,
    TransitResponse,
    TransitSnapshot,
    ZiweiSnapshot,
    ZiweiYearlySnapshot,
)
from fortune_core.qizheng import calculate_physical_baseline
from fortune_core.qizheng.traditional import calculate_traditional, sun_moon_mansions
from fortune_core.signals import build_natal_insights
from fortune_core.time_location import build_time_trace
from fortune_core.transit import calculate_daily_transit, calculate_transit, calculate_transit_window
from fortune_core.ziwei import calculate_palaces
from fortune_core.ziwei.limits import calculate_yearly_limit
from fortune_core.ziwei.palaces import BRANCHES_FROM_YIN, surrounding_indices

logger = logging.getLogger("fortune.api")

RELATION_LABELS = {
    "branch_clash": "地支冲",
    "branch_combination": "地支合",
    "branch_same": "同支",
}
PERIOD_LABELS = {"great_luck": "大运", "year": "流年", "month": "流月", "day": "流日"}

ERROR_SECURITY_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cross-Origin-Resource-Policy": "same-site",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "FORTUNE_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip() and origin.strip() != "*"
]
allowed_hosts = [
    host.strip()
    for host in os.getenv("FORTUNE_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver").split(",")
    if host.strip() and host.strip() != "*"
]
if not os.getenv("FORTUNE_ALLOWED_HOSTS"):
    # Fail-closed guard: leaving the local defaults in a gateway deployment makes
    # TrustedHostMiddleware reject every public request (400), which is confusing
    # to diagnose from the outside — surface it in the function log instead.
    logger.warning(
        "FORTUNE_ALLOWED_HOSTS not set; TrustedHostMiddleware only allows local hosts (%s). "
        "Gateway deployments must configure it with the public service host.",
        ", ".join(allowed_hosts),
    )

app = FastAPI(
    title="Fortune Observatory API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
# When the hosting gateway already injects CORS headers (CloudBase does for
# HTTP functions), a second copy here duplicates Access-Control-Allow-Origin
# and browsers reject the response. Leave CORS to the gateway unless the
# deployment explicitly lists browser origins (local dev does).
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["accept", "content-type"],
    )
app.add_middleware(
    RequestGuardMiddleware,
    max_body_bytes=16_384,
    requests_per_minute=90,
    global_requests_per_minute=900,
    max_concurrent_body_readers=32,
    request_body_timeout_seconds=5.0,
    max_concurrent_calculations=8,
    calculation_timeout_seconds=12.0,
    ai_timeout_seconds=28.0,
    trust_proxy=os.getenv("FORTUNE_TRUST_PROXY", "").lower() == "true",
    client_ip_header=os.getenv("FORTUNE_CLIENT_IP_HEADER", "x-forwarded-for").strip().lower()
    or "x-forwarded-for",
)


class ChartApiResponse(ChartResponse):
    ai_contexts: dict[str, AiContextBundle]


class DailyTransitApiResponse(DailyTransitResponse):
    ai_context: AiContextBundle | None = None


class TransitWindowApiResponse(TransitWindowResponse):
    ai_context: AiContextBundle | None = None


class TransitApiResponse(TransitResponse):
    ai_context: AiContextBundle | None = None


def _chart_ai_contexts(chart: ChartResponse, sex_for_rule: str = "") -> dict[str, AiContextBundle]:
    # Domain facts below come only from the Ziwei snapshot; unrelated Qizheng
    # ambiguity must not suppress an otherwise verified palace context.
    if chart.ziwei.verification_status != "verified":
        return {}
    # All four domains share AI context; the provider prompt already blocks
    # medical diagnosis and investment instructions, so facts stay on star
    # placements and lifestyle framing only.
    domain_palaces = {"health": "疾厄", "relationship": "夫妻", "career": "官禄", "wealth": "财帛"}
    # 跨盘锚点（四柱+紫微整体格局），给各领域解读提供领域宫之外的语境。
    STEM_ELEMENTS = {
        "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
        "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
    }
    day_stem = chart.bazi.pillars.day[0]
    day_element = STEM_ELEMENTS.get(day_stem, "")
    life_palace = next((item for item in chart.ziwei.palaces if item.name == "命宫"), None)
    body_palace = next((item for item in chart.ziwei.palaces if item.is_body_palace), None)
    life_anchor = (
        f"命宫在{life_palace.branch}，坐"
        + ("、".join(life_palace.major_stars) or "无主星")
        if life_palace
        else ""
    )
    body_anchor = (
        f"身宫落于{body_palace.name}宫（{body_palace.branch}）" if body_palace else ""
    )
    daymaster_anchor = f"八字日主为{day_stem}（{day_element}）" if day_element else ""
    mutagen_anchor = (
        "生年四化：" + "、".join(f"{item.star}化{item.mutagen}" for item in chart.ziwei.birth_mutagens)
        if chart.ziwei.birth_mutagens
        else ""
    )
    traditional = chart.qizheng.traditional
    qizheng_anchors: list[str] = []
    if traditional is not None and traditional.bodies:
        if traditional.life_lord:
            day_night = (
                "昼" if traditional.is_day_chart
                else "夜" if traditional.is_day_chart is False
                else None
            )
            qizheng_anchors.append(
                "七政四余盘（第三盘）："
                + (f"{day_night}盘，" if day_night else "")
                + f"命主{QIZHENG_STAR_NAMES[traditional.life_lord]}（命宫支守护星）、"
                + f"身主{QIZHENG_STAR_NAMES[traditional.body_lord]}"
            )
        dignified = "、".join(
            f"{QIZHENG_STAR_NAMES[body.body]}{body.dignity}"
            for body in traditional.bodies if body.dignity
        )
        grouped: dict[str, list[str]] = {}
        for body in traditional.bodies:
            if body.relation:
                grouped.setdefault(body.relation, []).append(QIZHENG_STAR_NAMES[body.body])
        bits = []
        if dignified:
            bits.append(f"庙旺：{dignified}")
        if grouped:
            bits.append("恩难仇用：" + "，".join(f"{key}星{'、'.join(names)}" for key, names in grouped.items()))
        if bits:
            qizheng_anchors.append("七政星曜：" + "；".join(bits))
        if traditional.verification_status != "verified":
            qizheng_anchors = [f"{item}（传统层未核验）" for item in qizheng_anchors]
    # 当前人生阶段锚（治"泛泛一生描述"：让解读聚焦当下大限/行限阶段）。
    current_stage_anchor = ""
    birth_year = chart.bazi.calculation_datetime.year
    nominal_age = datetime.now(tzone.utc).year - birth_year + 1
    stage_bits = [f"当前虚岁{nominal_age}"]
    decadal_palace = next(
        (item for item in chart.ziwei.palaces if item.decadal_range[0] <= nominal_age <= item.decadal_range[1]),
        None,
    )
    if decadal_palace is not None:
        stage_bits.append(
            f"紫微大限行{decadal_palace.name}宫（{decadal_palace.decadal_range[0]}-{decadal_palace.decadal_range[1]}岁）"
        )
    if traditional is not None and traditional.limit_rows:
        limit_row = next(
            (row for row in traditional.limit_rows if row.start_age <= nominal_age < row.end_age),
            None,
        )
        if limit_row is not None:
            palace_label = limit_row.palace if limit_row.palace.endswith("宫") else f"{limit_row.palace}宫"
            stage_bits.append(
                f"七政洞微行限在{palace_label}（{limit_row.branch}支，"
                f"{limit_row.start_age:.0f}-{limit_row.end_age:.0f}岁，{limit_row.segment}段）"
            )
    if len(stage_bits) > 1:
        current_stage_anchor = (
            "当前人生阶段：" + "，".join(stage_bits) + "。"
            + _life_stage_line(nominal_age, sex_for_rule)
        )
        if traditional is not None and traditional.verification_status != "verified" and "七政" in current_stage_anchor:
            current_stage_anchor += "（传统层未核验）"
    buckets = _decadal_buckets(chart.ziwei.palaces, nominal_age)
    decadal_rows = _decadal_fact_rows(buckets)
    contexts: dict[str, AiContextBundle] = {}
    for domain, palace_name in domain_palaces.items():
        palace = next((item for item in chart.ziwei.palaces if item.name == palace_name), None)
        if palace is None:
            continue
        major_stars = (
            "、".join(f"{star}（{brightness}）" for star, brightness in palace.major_star_brightness)
            or "、".join(palace.major_stars)
            or "当前无主星数据"
        )
        minor_stars = "、".join(palace.minor_stars) or "当前无辅星数据"
        palace_stars = set((*palace.major_stars, *palace.minor_stars))
        mutagens = [
            f"{item.star}化{item.mutagen}"
            for item in chart.ziwei.birth_mutagens
            if item.star in palace_stars
        ]
        fact_texts = [
            f"{palace_name}宫位于{palace.branch}",
            f"该宫大限范围为{palace.decadal_range[0]}至{palace.decadal_range[1]}",
            f"该宫主星为{major_stars}",
            f"该宫辅星为{minor_stars}",
            *( [f"该宫可追溯四化为{'、'.join(mutagens)}"] if mutagens else [] ),
        ]
        palace_index = BRANCHES_FROM_YIN.index(palace.branch)
        _, opposite, trinity_a, trinity_b = surrounding_indices(palace_index)
        branch_by_index = {BRANCHES_FROM_YIN.index(item.branch): item for item in chart.ziwei.palaces}

        def _label(other) -> str:
            name = other.name if other.name.endswith("宫") else f"{other.name}宫"
            stars = "、".join(other.major_stars)
            return f"{name}（{stars}）" if stars else f"{name}（无主星）"

        opposite_palace = branch_by_index.get(opposite)
        if opposite_palace:
            fact_texts.append(f"该宫对宫为{_label(opposite_palace)}，对宫星情与本品互为表里")
        trinity_palaces = [branch_by_index.get(idx) for idx in (trinity_a, trinity_b)]
        trinity_labels = [_label(other) for other in trinity_palaces if other]
        if trinity_labels:
            fact_texts.append(f"该宫三合会照：{'；'.join(trinity_labels)}")
        # 锚点合并（命宫+身宫一行），为七政三盘联动腾出事实位（上限 12）。
        palace_anchors = []
        if life_anchor and body_anchor:
            palace_anchors.append(f"{life_anchor}；{body_anchor}")
        elif life_anchor or body_anchor:
            palace_anchors.append(life_anchor or body_anchor)
        if daymaster_anchor:
            palace_anchors.append(daymaster_anchor)
        if current_stage_anchor:
            palace_anchors.append(current_stage_anchor)
        if mutagen_anchor:
            palace_anchors.append(mutagen_anchor)
        fact_texts.extend(palace_anchors)
        fact_texts.extend(qizheng_anchors)
        fact_texts.extend(decadal_rows)
        bundle = build_signed_context(
            "domain",
            [AiFact(id=f"domain-{index + 1}", text=text) for index, text in enumerate(fact_texts[:24])],
            bundle_type=f"domain.{domain}",
            context_group=chart.trace_id,
        )
        if bundle is not None:
            contexts[domain] = bundle
    palace_texts: list[str] = []
    for palace in chart.ziwei.palaces:
        palace_stars = set((*palace.major_stars, *palace.minor_stars))
        mutagens = [
            f"{item.star}化{item.mutagen}"
            for item in chart.ziwei.birth_mutagens
            if item.star in palace_stars
        ]
        self_mutagens = [
            entry.mutagen
            for entry in chart.ziwei.flying_mutagens
            if entry.from_branch == palace.branch and entry.is_self
        ]
        stars = "、".join(f"{star}（{brightness}）" for star, brightness in palace.major_star_brightness) or "无主星"
        palace_label = palace.name if palace.name.endswith("宫") else f"{palace.name}宫"
        text = (
            f"{palace_label}干支{palace.stem}{palace.branch}"
            + ("（身宫）" if palace.is_body_palace else "")
            + (f"，{('、'.join(mutagens))}" if mutagens else "")
            + ("，自化" if self_mutagens else "")
            + ("、".join(self_mutagens) if self_mutagens else "")
            + f"，主星：{stars}"
            + (f"，辅星：{'、'.join(palace.minor_stars)}" if palace.minor_stars else "")
            + f"，大限{palace.decadal_range[0]}至{palace.decadal_range[1]}岁"
        )
        palace_texts.append(text[:400])
    ziwei_summary_texts: list[str] = []
    if decadal_palace is not None:
        ziwei_summary_texts.append(
            f"当前虚岁{nominal_age}，紫微大限行{decadal_palace.name}宫"
            f"（{decadal_palace.decadal_range[0]}-{decadal_palace.decadal_range[1]}岁）：该宫为当前十年主旋律所在"
        )

    def _ziwei_star_palace_label(star: str) -> str:
        found = next(
            (item for item in chart.ziwei.palaces if star in item.major_stars or star in item.minor_stars),
            None,
        )
        if found is None:
            return "不入十二宫"
        return found.name if found.name.endswith("宫") else f"{found.name}宫"

    mutagen_summary = "、".join(
        f"{item.star}化{item.mutagen}落{_ziwei_star_palace_label(item.star)}"
        for item in chart.ziwei.birth_mutagens
    )
    if mutagen_summary:
        ziwei_summary_texts.append(f"生年四化落宫：{mutagen_summary}——四化所在宫位即人生资源与课题所在")
    ziwei_bundle = build_signed_context(
        "domain",
        [
            AiFact(id=f"ziwei-{index + 1}", text=text)
            for index, text in enumerate((palace_texts[:12] + ziwei_summary_texts)[:24])
        ],
        bundle_type="ziwei.chart",
        context_group=chart.trace_id,
    )
    if ziwei_bundle is not None:
        contexts["ziwei"] = ziwei_bundle

    traditional = chart.qizheng.traditional
    if traditional is not None and traditional.bodies:
        by_key = {body.body: body for body in traditional.bodies}
        qz_texts: list[str] = []
        if traditional.is_day_chart is not None:
            qz_texts.append(
                f"七政昼夜盘：{'昼' if traditional.is_day_chart else '夜'}生"
                f"（太阳{'在地平之上' if traditional.is_day_chart else '在地平之下'}，昼盘重太阳、夜盘重太阴）"
            )
        if traditional.life_lord:
            qz_texts.append(
                f"命主{QIZHENG_STAR_NAMES[traditional.life_lord]}（命宫{traditional.houses.life_branch}的宫主）、"
                f"身主{QIZHENG_STAR_NAMES[traditional.body_lord]}（身宫{traditional.houses.body_branch}的宫主）"
            )
        for key in ("sun", "moon"):
            body = by_key.get(key)
            if body:
                extras = "，居垣" if body.dignity == "居垣" else ("，升殿" if body.dignity == "升殿" else "")
                qz_texts.append(
                    f"{QIZHENG_STAR_NAMES[key]}入{body.mansion}宿{body.mansion_offset_deg:.0f}度（{body.mansion_branch}宫{extras}）"
                )
        others = [
            f"{QIZHENG_STAR_NAMES[body.body]}入{body.mansion}宿"
            for body in traditional.bodies
            if body.body not in ("sun", "moon")
        ]
        if others:
            qz_texts.append("其余星曜入宿：" + "、".join(others))
        dignified = [
            f"{QIZHENG_STAR_NAMES[body.body]}{body.dignity}于{'本垣' if body.dignity == '居垣' else '本宿'}"
            for body in traditional.bodies if body.dignity
        ]
        if dignified:
            qz_texts.append("庙旺（居垣=在本命宫最有力，升殿=躔本属宿）：" + "、".join(dignified))
        grouped: dict[str, list[str]] = {}
        for body in traditional.bodies:
            if body.relation:
                grouped.setdefault(body.relation, []).append(QIZHENG_STAR_NAMES[body.body])
        if grouped:
            qz_texts.append(
                "相对命主五星的恩难仇用（恩=生我助力，难=克我压力，用=我克可控之财，仇=我生泄耗）："
                + "；".join(f"{relation}星{'、'.join(names)}" for relation, names in grouped.items())
            )
        if traditional.childhood_exit_age is not None and traditional.limit_rows:
            first = traditional.limit_rows[0]
            qz_texts.append(
                f"洞微大限：{traditional.childhood_exit_age:.1f}虚岁出童限入命宫限"
                f"（{first.years:.0f}年），此后行限为"
                + "→".join(f"{row.palace}{row.years:g}年" for row in traditional.limit_rows[1:5])
            )
        if traditional.verification_status != "verified":
            qz_texts = [f"{item}（传统层未核验）" for item in qz_texts]
        qz_bundle = build_signed_context(
            "domain",
            [AiFact(id=f"qizheng-{index + 1}", text=text) for index, text in enumerate(qz_texts[:12])],
            bundle_type="qizheng.chart",
            context_group=chart.trace_id,
        )
        if qz_bundle is not None:
            contexts["qizheng"] = qz_bundle
    return contexts


def _fortune_context_group(
    calculation_datetime: str,
    pillars: tuple[str, str, str, str],
    sex_for_rule: str,
    *parts: str,
) -> str:
    return derive_context_group(
        calculation_datetime,
        *pillars,
        sex_for_rule,
        *parts,
    ) or "context_unavailable"


PILLAR_POSITION_LABELS = ("年柱", "月柱", "日柱", "时柱")
PILLAR_DOMAIN_HINTS = (
    "年柱象征根基与长辈议题",
    "月柱象征环境与同辈议题",
    "日柱象征自身与亲密关系议题",
    "时柱象征表达、作品与晚辈议题",
)
SIGNAL_DIRECTION_LABELS = {"support": "支持", "tension": "张力", "neutral": "中性"}


def _life_stage_line(nominal_age: int, sex_for_rule: str) -> str:
    sex_label = "男" if sex_for_rule == "male" else "女" if sex_for_rule == "female" else "未知"
    if nominal_age < 22:
        roles = "学生/求职：学业考试、同学室友、兴趣作品；不要写成已婚、已育、已当管理、已养家糊口"
    elif nominal_age < 28:
        roles = "起步：恋爱相处、实习或第一份工作、作品表达；可谈原生家庭，不要写成已婚已育、已当领导、已有房贷"
    elif nominal_age < 36:
        roles = "成家窗口：婚恋和职业用假设语气；不要写成已经结婚、已有孩子、已是高管"
    else:
        roles = "中年后：家庭事业钱都用「如果」——如果已婚/如果有孩子/如果在带团队，不要把宫位当成履历"
    return f"排盘性别{sex_label}，虚岁约{nominal_age}。按此阶段写日常：{roles}"


def _decadal_buckets(palaces: list[Any], age: int) -> dict[str, Any]:
    ordered = sorted(palaces, key=lambda item: item.decadal_range[0])
    past: list[Any] = []
    current: Any | None = None
    future: list[Any] = []
    for item in ordered:
        start, end = item.decadal_range
        if end < age:
            past.append(item)
        elif start <= age <= end and current is None:
            current = item
        elif start > age:
            future.append(item)
        elif start <= age <= end:
            future.append(item)
    if current is None and ordered:
        current = ordered[-1]
        past = [item for item in ordered if item is not current]
        future = []
    return {
        "past": past,
        "current": current,
        "upcoming": future[:2],
        "dropped": future[2:],
    }


def _decadal_fact_rows(buckets: dict[str, Any]) -> list[str]:
    def line(item: Any) -> str:
        stars = "、".join(item.major_stars[:2]) or "无主星"
        name = item.name if str(item.name).endswith("宫") else f"{item.name}宫"
        return f"{item.decadal_range[0]}-{item.decadal_range[1]}岁{name}（{item.branch}支）坐{stars}"

    rows: list[str] = []
    if buckets["past"]:
        rows.append("已过大限：" + "；".join(line(item) for item in buckets["past"]))
    if buckets["current"] is not None:
        rows.append("当前大限：" + line(buckets["current"]))
    if buckets["upcoming"]:
        rows.append("未到大限：" + "；".join(line(item) for item in buckets["upcoming"]))
    return rows


def _pillar_position(fact: Any) -> str:
    index = fact.fact_id.rsplit("-", 1)[-1]
    return PILLAR_POSITION_LABELS[int(index)] if index.isdigit() and int(index) < 4 else "本命"


def _pillar_domain(fact: Any) -> str:
    index = fact.fact_id.rsplit("-", 1)[-1]
    return PILLAR_DOMAIN_HINTS[int(index)] if index.isdigit() and int(index) < 4 else "本命盘对应领域"


def _daily_ai_context(
    response: DailyTransitResponse,
    context_group: str,
    internal: Any = None,
    transit_qizheng_fact: str | None = None,
    sex_for_rule: str = "",
) -> AiContextBundle | None:
    transit = response.transit
    if transit.verification_status != "verified":
        return None
    texts = [f"{transit.transit_date}的日柱为{transit.day_pillar}"]
    yearly = response.ziwei_yearly
    if yearly is not None:
        texts.append(_life_stage_line(yearly.nominal_age, sex_for_rule))
    for fact in transit.facts[:4]:
        texts.append(
            f"{RELATION_LABELS[fact.relation]}：流日{fact.transit_pillar}作用于本命{_pillar_position(fact)}{fact.natal_pillar}"
            f"，主要涉及{_pillar_domain(fact)}"
        )
    if not transit.facts:
        texts.append("该日未检测到已定义的地支冲、合或同支关系")
    signals = tuple(getattr(internal, "signals", ()) or ())
    if signals:
        counts = Counter(SIGNAL_DIRECTION_LABELS[signal.direction] for signal in signals)
        texts.append(
            f"当日规则信号共{len(signals)}条："
            + "、".join(f"{direction}{count}条" for direction, count in counts.items())
        )
    annual = getattr(internal, "ziwei_annual", None)
    if annual is not None and getattr(annual, "life_branch", None):
        texts.append(f"{annual.year_pillar}年紫微流年命宫位于{annual.life_branch}")
    yearly = response.ziwei_yearly
    if yearly is not None:
        def _palace_label(entry: Any) -> str:
            name = entry.palace_name or entry.palace_branch
            return name if name.endswith("宫") else f"{name}宫"
        mutagen_line = "、".join(
            f"{entry.star}化{entry.mutagen}入{_palace_label(entry)}"
            for entry in yearly.yearly_mutagens
        )
        texts.append(f"{yearly.year_pillar}年四化：{mutagen_line}")
        court_stars = [
            star.star for star in yearly.flowing_stars if star.branch == yearly.life_branch
        ]
        if court_stars:
            texts.append(
                f"流年命宫在{yearly.life_branch}，坐{'、'.join(court_stars)}（流曜：随年流转的辅星）"
            )
        decadal = yearly.decadal
        decadal_mutagens = "、".join(f"{entry.star}化{entry.mutagen}" for entry in decadal.mutagens)
        texts.append(
            f"当前{'童限' if decadal.is_childhood else '大限'}{decadal.branch}宫（{decadal.stem}{decadal.branch}，"
            f"{decadal.start_age}-{decadal.end_age}岁），限内四化：{decadal_mutagens}"
        )
    # period 上下文最多 7 条、两包合并上限 12：daily 已达 8 条时不再追加七政流日。
    if transit_qizheng_fact and len(texts) < 8:
        texts.insert(1, transit_qizheng_fact)
    return build_signed_context(
        "fortune",
        [AiFact(id=f"daily-{index + 1}", text=text) for index, text in enumerate(texts[:12])],
        bundle_type="fortune.daily",
        context_group=context_group,
    )


def _transit_ai_context(response: TransitResponse, context_group: str) -> AiContextBundle | None:
    transit = response.transit
    if transit.verification_status != "verified":
        return None
    texts = [
        f"{PERIOD_LABELS[layer.period]}为{layer.pillar}"
        + (f"，出现{'、'.join(RELATION_LABELS[fact.relation] for fact in layer.facts)}" if layer.facts else "，未出现已定义关系")
        for layer in transit.layers
    ]
    texts.extend(f"{insight.title}：{insight.summary}；{insight.action}" for insight in transit.insights[:3])
    return build_signed_context(
        "fortune",
        [AiFact(id=f"period-{index + 1}", text=text) for index, text in enumerate(texts[:7])],
        bundle_type="fortune.period",
        context_group=context_group,
    )


def _window_ai_context(response: TransitWindowResponse, context_group: str) -> AiContextBundle | None:
    transit = response.transit
    if transit.verification_status != "verified":
        return None
    all_facts = [fact for day in transit.daily for fact in day.facts]
    active_days = [day for day in transit.daily if day.facts]
    texts = [
        f"时间范围为{transit.start_date}至{transit.end_date}，共{len(transit.daily)}天",
        f"其中{len(active_days)}天出现可追溯关系",
        "，".join(
            (
                f"地支合{sum(fact.relation == 'branch_combination' for fact in all_facts)}次",
                f"地支冲{sum(fact.relation == 'branch_clash' for fact in all_facts)}次",
                f"同支{sum(fact.relation == 'branch_same' for fact in all_facts)}次",
            )
        ),
        *(
            f"{day.transit_date}：{'、'.join(RELATION_LABELS[fact.relation] for fact in day.facts)}"
            for day in active_days[:9]
        ),
    ]
    return build_signed_context(
        "fortune",
        [AiFact(id=f"window-{index + 1}", text=text) for index, text in enumerate(texts[:12])],
        bundle_type="fortune.window",
        context_group=context_group,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, error: RequestValidationError) -> JSONResponse:
    detail = [
        {
            "type": item.get("type", "value_error"),
            "loc": list(item.get("loc", ())),
            "msg": item.get("msg", "Invalid input"),
        }
        for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
    trace_id = str(uuid4())
    logger.error(
        "Unhandled API error trace_id=%s path=%s error_type=%s",
        trace_id,
        request.url.path,
        type(error).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "trace_id": trace_id},
        headers=ERROR_SECURITY_HEADERS,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "bazi-v1"}


QIZHENG_STAR_NAMES = {
    "sun": "太阳", "moon": "太阴", "mercury": "水星", "venus": "金星",
    "mars": "火星", "jupiter": "木星", "saturn": "土星",
    "rahu": "罗睺", "ketu": "计都", "apogee": "月孛", "ziqi": "紫炁",
}


@app.get("/v1/ai/status", response_model=AiStatusResponse)
def ai_status() -> AiStatusResponse:
    return AiStatusResponse(available=provider_is_available())


@app.post("/v1/ai/explain", response_model=AiExplainResponse)
async def explain_result(request: AiExplainRequest) -> AiExplainResponse:
    try:
        return await explain_with_ai(request)
    except AiConfigurationError as error:
        logger.warning("AI provider unavailable error_type=%s", type(error).__name__)
        raise HTTPException(
            status_code=503,
            detail="AI 讲解暂未配置，规则结果不受影响。",
        ) from error
    except AiBudgetExceeded as error:
        raise HTTPException(
            status_code=429,
            detail="今日 AI 讲解额度已用完，规则结果仍可正常使用。",
            headers={"Retry-After": "3600"},
        ) from error
    except AiProviderError as error:
        trace_id = str(uuid4())
        logger.warning(
            "AI explanation failed trace_id=%s error_type=%s",
            trace_id,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail="AI 讲解这次没有生成，请稍后重试。",
            headers={"X-Trace-Id": trace_id},
        ) from error


@app.post("/v1/dreams/questions", response_model=QuestionsResponse)
async def dream_questions(request: QuestionsRequest) -> QuestionsResponse:
    try:
        return await generate_questions(request.dream)
    except AiConfigurationError as error:
        raise HTTPException(status_code=503, detail="解梦暂未配置，排盘不受影响。") from error
    except AiBudgetExceeded as error:
        raise HTTPException(
            status_code=429,
            detail="今日解梦额度已用完，排盘仍可正常使用。",
            headers={"Retry-After": "3600"},
        ) from error
    except AiProviderError as error:
        raise HTTPException(status_code=502, detail="题目没写成，请稍后重试。") from error


@app.post("/v1/dreams/interpret", response_model=InterpretResponse)
async def interpret_dream(request: InterpretRequest) -> InterpretResponse:
    try:
        return await interpret_dream_request(request)
    except AiConfigurationError as error:
        logger.warning("dream interpret unavailable error_type=%s", type(error).__name__)
        raise HTTPException(
            status_code=503,
            detail="解梦暂未配置，排盘不受影响。",
        ) from error
    except AiBudgetExceeded as error:
        raise HTTPException(
            status_code=429,
            detail="今日解梦额度已用完，排盘仍可正常使用。",
            headers={"Retry-After": "3600"},
        ) from error
    except AiProviderError as error:
        trace_id = str(uuid4())
        logger.warning(
            "dream interpret failed trace_id=%s error_type=%s",
            trace_id,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=502,
            detail="这一梦没写成，请稍后重试。",
            headers={"X-Trace-Id": trace_id},
        ) from error


@app.post("/v1/charts", response_model=ChartApiResponse)
def create_chart(birth: BirthInput) -> ChartApiResponse:
    try:
        snapshot = calculate_bazi(birth)
        ziwei = ZiweiSnapshot.model_validate(
            calculate_palaces(birth), from_attributes=True
        )
        qizheng = calculate_physical_baseline(birth.civil_datetime)
        traditional = calculate_traditional(
            birth.civil_datetime, snapshot.pillars.hour[1], birth.latitude, birth.longitude
        )
        qizheng = qizheng.model_copy(update={"traditional": traditional})
    except ValueError as error:
        raise HTTPException(status_code=422, detail="计算输入超出当前支持范围。") from error
    chart = ChartResponse(
        bazi=snapshot,
        ziwei=ziwei,
        qizheng=qizheng,
        time_trace=build_time_trace(birth, snapshot),
        natal_insights=build_natal_insights(snapshot, ziwei, qizheng),
        trace_id=str(uuid4()),
    )
    return ChartApiResponse(**chart.model_dump(), ai_contexts=_chart_ai_contexts(chart, birth.sex_for_rule))


@app.post("/v1/transits/daily", response_model=DailyTransitApiResponse)
def create_daily_transit(request: DailyTransitRequest) -> DailyTransitApiResponse:
    try:
        bazi = calculate_bazi(request.birth)
        pillars = bazi.pillars
        daily_internal = calculate_daily_transit(
            request.transit_date,
            (pillars.year, pillars.month, pillars.day, pillars.hour),
        )
        transit = DailyTransitSnapshot.model_validate(
            daily_internal,
            from_attributes=True,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail="计算输入超出当前支持范围。") from error
    if bazi.verification_status != "verified":
        transit = transit.model_copy(
            update={"verification_status": bazi.verification_status}
        )
    ziwei_yearly = None
    try:
        ziwei_snapshot = calculate_palaces(request.birth)
        if ziwei_snapshot.verification_status == "verified":
            ziwei_yearly = ZiweiYearlySnapshot.model_validate(
                calculate_yearly_limit(ziwei_snapshot, request.birth, request.transit_date),
                from_attributes=True,
            )
    except ValueError:
        ziwei_yearly = None
    response = DailyTransitResponse(transit=transit, trace_id=str(uuid4()), ziwei_yearly=ziwei_yearly)
    try:
        transit_noon = datetime.combine(
            request.transit_date, dtime(12, 0), tzinfo=tzone(timedelta(hours=8))
        )
        sun_mansion, sun_branch, moon_mansion, _moon_branch = sun_moon_mansions(transit_noon)
        transit_qizheng_fact = (
            f"七政流日：太阳入{sun_mansion}宿（{sun_branch}宫）、月亮入{moon_mansion}宿（恒星黄道口径）"
        )
    except ValueError:
        transit_qizheng_fact = None
    context_group = _fortune_context_group(
        bazi.calculation_datetime.isoformat(),
        (pillars.year, pillars.month, pillars.day, pillars.hour),
        request.birth.sex_for_rule,
        request.transit_date.isoformat(),
    )
    return DailyTransitApiResponse(
        **response.model_dump(),
        ai_context=_daily_ai_context(
            response, context_group, daily_internal, transit_qizheng_fact, request.birth.sex_for_rule
        ),
    )


@app.post("/v1/transits/window", response_model=TransitWindowApiResponse)
def create_transit_window(request: TransitWindowRequest) -> TransitWindowApiResponse:
    try:
        bazi = calculate_bazi(request.birth)
        pillars = bazi.pillars
        transit = TransitWindowSnapshot.model_validate(
            calculate_transit_window(
                request.start_date,
                request.end_date,
                (pillars.year, pillars.month, pillars.day, pillars.hour),
            ),
            from_attributes=True,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail="计算输入超出当前支持范围。") from error
    if bazi.verification_status != "verified":
        transit = transit.model_copy(
            update={"verification_status": bazi.verification_status}
        )
    response = TransitWindowResponse(transit=transit, trace_id=str(uuid4()))
    context_group = _fortune_context_group(
        bazi.calculation_datetime.isoformat(),
        (pillars.year, pillars.month, pillars.day, pillars.hour),
        request.birth.sex_for_rule,
        request.start_date.isoformat(),
        request.end_date.isoformat(),
    )
    return TransitWindowApiResponse(
        **response.model_dump(),
        ai_context=_window_ai_context(response, context_group),
    )


@app.post("/v1/transits", response_model=TransitApiResponse)
def create_transit(request: TransitRequest) -> TransitApiResponse:
    try:
        bazi = calculate_bazi(request.birth)
        pillars = bazi.pillars
        great_luck = active_great_luck(bazi, request.transit_date)
        transit = TransitSnapshot.model_validate(
            calculate_transit(
                request.transit_date,
                (pillars.year, pillars.month, pillars.day, pillars.hour),
                great_luck.pillar if great_luck else None,
            ),
            from_attributes=True,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail="计算输入超出当前支持范围。") from error
    if bazi.verification_status != "verified":
        transit = transit.model_copy(
            update={"verification_status": bazi.verification_status}
        )
    response = TransitResponse(transit=transit, trace_id=str(uuid4()))
    context_group = _fortune_context_group(
        bazi.calculation_datetime.isoformat(),
        (pillars.year, pillars.month, pillars.day, pillars.hour),
        request.birth.sex_for_rule,
        request.transit_date.isoformat(),
    )
    return TransitApiResponse(
        **response.model_dump(),
        ai_context=_transit_ai_context(response, context_group),
    )
