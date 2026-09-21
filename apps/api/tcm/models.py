from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ConsultRequest(StrictModel):
    question: str = Field(min_length=4, max_length=2000)


class SourceOut(StrictModel):
    work: str
    quote: str


class ConsultResponse(StrictModel):
    essay: str = ""
    sources: list[SourceOut] = Field(default_factory=list, max_length=3)
    referral: str | None = None
