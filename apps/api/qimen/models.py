"""奇门遁甲端点的请求/响应契约（pydantic）。

解读请求把第一步排盘返回的完整响应原样带回（无服务端盘面存储），
解读只消费盘面事实，不重算。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# 事项分类（表单下拉），对应 skills/qimen-dunjia/references/yongshen.md 的取用神映射
QUESTION_TYPES: tuple[str, ...] = (
    "事业", "求财", "感情", "学业", "健康", "出行", "诉讼", "寻人寻物", "其他",
)


class QimenChartRequest(StrictModel):
    question_type: str = Field(min_length=1, max_length=8)
    question_goal: str = Field(min_length=2, max_length=120)
    time_mode: Literal["now", "custom"] = "now"
    time_input: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=40)
    detail_level: Literal["brief", "detailed"] = "brief"

    @model_validator(mode="after")
    def _check_type_and_time(self) -> "QimenChartRequest":
        if self.question_type not in QUESTION_TYPES:
            raise ValueError(f"未知的事项类型：{self.question_type}")
        if self.time_mode == "custom" and not self.time_input:
            raise ValueError("自定义起局时间不能为空")
        return self


class LunarDate(StrictModel):
    year: int
    month: int
    day: int
    month_text: str
    day_text: str
    is_leap_month: bool


class Jieqi(StrictModel):
    active_jie: str
    active_jie_started_at: str
    next_jie: str | None = None
    next_jie_at: str | None = None


class Ganzhi(StrictModel):
    year: str
    month: str
    day: str
    time: str
    day_xun_exact: str
    day_xunkong_exact: str
    time_xun: str
    time_xunkong: str


class StemPosition(StrictModel):
    stem: str
    raw_palace: int | None = None
    palace: int | None = None
    note: str | None = None


class Yima(StrictModel):
    branch: str | None = None
    palace: int | None = None


class Zhifu(StrictModel):
    star: str
    palace: int


class Zhishi(StrictModel):
    door: str
    palace: int


class Pattern(StrictModel):
    name: str
    palace: int
    detail: str
    nature: str


class Palace(StrictModel):
    palace: int
    name: str
    direction: str
    trigram: str
    element: str
    earth_stem: str | None = None
    sky_stem: str | None = None
    stem_relation: str | None = None
    star: str | None = None
    star_element: str | None = None
    star_palace_relation: str | None = None
    door: str | None = None
    door_element: str | None = None
    door_palace_relation: str | None = None
    god: str | None = None
    is_center: bool = False
    hosts_center: bool = False
    hosting_note: str | None = None


class QimenChartOut(StrictModel):
    dun_type: str
    yuan: str
    ju_number: int
    xunshou: str
    hidden_yi: str
    kongwang: list[str]
    kongwang_palaces: list[int]
    day_kongwang: list[str]
    day_kongwang_palaces: list[int]
    time_stem_visible: str
    day_stem: StemPosition
    year_stem: StemPosition
    month_stem: StemPosition
    yima: Yima
    zhifu: Zhifu
    zhishi: Zhishi
    door_index: dict[str, int]
    star_index: dict[str, int]
    detected_patterns: list[Pattern]
    grid_order: list[int]
    palaces: list[Palace]


class QimenChartResponse(StrictModel):
    question_type: str
    question_goal: str
    detail_level: Literal["brief", "detailed"]
    city: str | None = None
    used_now: bool
    calendar_solar: str
    calendar_lunar: LunarDate
    jieqi: Jieqi
    ganzhi: Ganzhi
    chart: QimenChartOut
    warnings: list[str] = Field(default_factory=list)


class QimenInterpretRequest(StrictModel):
    chart: QimenChartResponse
