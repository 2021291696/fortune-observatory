from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Layer(str, Enum):
    classic = "classic"
    theory = "theory"
    science = "science"
    note = "note"


class Polar(str, Enum):
    auspicious = "auspicious"
    inauspicious = "inauspicious"
    mixed = "mixed"
    none = "none"


class CorpusRecord(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    work_id: str
    title: str
    layer: Layer
    text: str = Field(min_length=1, max_length=4000)
    citation_eligible: bool
    polarity: Polar = Polar.none
    edition: str = ""
    quote_zh_is_paraphrase: bool = False


class SpanHit(StrictModel):
    record_id: str
    work_id: str
    title: str
    quote: str
    start: int
    end: int
    layer: Layer
    polarity: Polar
    quote_zh_is_paraphrase: bool = False


class ComplexAnswer(StrictModel):
    id: str = Field(min_length=1, max_length=32)
    question: str = Field(min_length=1, max_length=80)
    answer: str | None = Field(default=None, max_length=80)


class QuestionOut(StrictModel):
    id: str = Field(min_length=1, max_length=32)
    label: str = Field(min_length=1, max_length=80)


class InterpretRequest(StrictModel):
    dream: str = Field(min_length=4, max_length=2000)
    mode: Literal["simple", "complex"] = "simple"
    answers: list[ComplexAnswer] = Field(default_factory=list, max_length=3)
    overlay: bool = False
    context_tokens: list[str] = Field(default_factory=list, max_length=2)


class QuestionsRequest(StrictModel):
    dream: str = Field(min_length=4, max_length=2000)


class QuestionsResponse(StrictModel):
    questions: list[QuestionOut] = Field(min_length=3, max_length=3)


class SourceOut(StrictModel):
    work: str
    quote: str
    channel: Literal["字面", "近邻"]


class InterpretResponse(StrictModel):
    essay: str = ""
    sources: list[SourceOut] = Field(default_factory=list, max_length=24)
    overlay: str | None = None
    referral: str | None = None
