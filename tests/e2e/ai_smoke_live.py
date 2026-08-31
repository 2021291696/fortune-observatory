"""Local live AI smoke: one explain + one interpret against local uvicorn.

Usage:
    DESTINY_SMOKE_BASE=http://127.0.0.1:8000 \\
    .venv/Scripts/python.exe tests/e2e/ai_smoke_live.py

Skip (exit 0) when FORTUNE_AI_API_KEY is unset or /v1/ai/status.available is false.
Refuse any host other than 127.0.0.1 / localhost.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlparse

import httpx

DEFAULT_BASE = "http://127.0.0.1:8000"
BANNED_HOST_FRAGMENT = "tcloudbase.com"

BIRTH = {
    "civil_datetime": "1995-06-15T08:30:00+08:00",
    "timezone_id": "Asia/Shanghai",
    "longitude": 116.4074,
    "latitude": 39.9042,
    "sex_for_rule": "male",
    "use_apparent_solar_time": True,
}


def _base() -> str:
    raw = os.environ.get("DESTINY_SMOKE_BASE", DEFAULT_BASE).rstrip("/")
    host = (urlparse(raw).hostname or "").lower()
    if BANNED_HOST_FRAGMENT in host or host not in {"127.0.0.1", "localhost"}:
        raise SystemExit(f"refusing non-local smoke base: {raw}")
    return raw


def _fact_ids(payload: dict) -> set[str]:
    ids: set[str] = set()
    block = payload.get("summary") or {}
    ids.update(block.get("fact_ids") or [])
    for key in ("actions", "caveats"):
        for item in payload.get(key) or []:
            ids.update(item.get("fact_ids") or [])
    return ids


def main() -> int:
    if not os.environ.get("FORTUNE_AI_API_KEY"):
        print("SKIP: FORTUNE_AI_API_KEY unset")
        return 0
    base = _base()
    client = httpx.Client(timeout=60)
    status = client.get(f"{base}/v1/ai/status")
    status.raise_for_status()
    body = status.json()
    if not body.get("available"):
        print("SKIP: provider unavailable", body)
        return 0

    chart = client.post(f"{base}/v1/charts", json=BIRTH)
    chart.raise_for_status()
    contexts = chart.json().get("ai_contexts") or {}
    ziwei = contexts.get("ziwei")
    if not ziwei:
        print("FAIL: chart has no ziwei ai_context")
        return 1
    known = {fact["id"] for fact in ziwei["facts"]}

    explain = client.post(
        f"{base}/v1/ai/explain",
        json={
            "question": "请用白话讲讲命宫主星，不要编造盘面里没有的星曜。",
            "context_tokens": [ziwei["token"]],
        },
    )
    if explain.status_code >= 500:
        print("ENV: explain upstream", explain.status_code, explain.text[:200])
        return 0
    explain.raise_for_status()
    answer = explain.json()
    cited = _fact_ids(answer)
    unknown = cited - known
    if unknown:
        print("FAIL: explain cited unknown fact ids", unknown)
        return 1

    print("PASS explain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
