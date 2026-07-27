"""Production API entrypoint for the verified v1 calculation path.

Run with PowerShell:
    $env:PYTHONPATH = "$PWD\\src"
    .\\.venv\\Scripts\\python.exe -m uvicorn app:app --app-dir apps/api
"""

from __future__ import annotations

import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from security import RequestGuardMiddleware

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
)
from fortune_core.qizheng import calculate_physical_baseline
from fortune_core.signals import build_natal_insights
from fortune_core.time_location import build_time_trace
from fortune_core.transit import calculate_daily_transit, calculate_transit, calculate_transit_window
from fortune_core.ziwei import calculate_palaces

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

app = FastAPI(
    title="Fortune Observatory API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
app.add_middleware(
    RequestGuardMiddleware,
    max_body_bytes=16_384,
    requests_per_minute=90,
    global_requests_per_minute=900,
    max_concurrent_calculations=8,
    calculation_timeout_seconds=12.0,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "bazi-v1"}


@app.post("/v1/charts", response_model=ChartResponse)
def create_chart(birth: BirthInput) -> ChartResponse:
    try:
        snapshot = calculate_bazi(birth)
        ziwei = ZiweiSnapshot.model_validate(
            calculate_palaces(birth), from_attributes=True
        )
        qizheng = calculate_physical_baseline(birth.civil_datetime)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="计算输入超出当前支持范围。") from error
    return ChartResponse(
        bazi=snapshot,
        ziwei=ziwei,
        qizheng=qizheng,
        time_trace=build_time_trace(birth, snapshot),
        natal_insights=build_natal_insights(snapshot, ziwei, qizheng),
        trace_id=str(uuid4()),
    )


@app.post("/v1/transits/daily", response_model=DailyTransitResponse)
def create_daily_transit(request: DailyTransitRequest) -> DailyTransitResponse:
    try:
        bazi = calculate_bazi(request.birth)
        pillars = bazi.pillars
        transit = DailyTransitSnapshot.model_validate(
            calculate_daily_transit(
                request.transit_date,
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
    return DailyTransitResponse(transit=transit, trace_id=str(uuid4()))


@app.post("/v1/transits/window", response_model=TransitWindowResponse)
def create_transit_window(request: TransitWindowRequest) -> TransitWindowResponse:
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
    return TransitWindowResponse(transit=transit, trace_id=str(uuid4()))


@app.post("/v1/transits", response_model=TransitResponse)
def create_transit(request: TransitRequest) -> TransitResponse:
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
    return TransitResponse(transit=transit, trace_id=str(uuid4()))
