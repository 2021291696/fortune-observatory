import asyncio
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from time import monotonic
from typing import Any

import pytest
from pydantic import ValidationError

from fortune_core.models import BirthInput, DailyTransitRequest, TransitRequest, TransitWindowRequest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from security import RequestGuardMiddleware
from fortune_core.bazi import calculate_bazi
from fortune_core.time_location.apparent_solar import _verify_ephemeris
from fortune_core.ziwei import calculate_palaces
import app as api_module


def valid_birth(**updates: Any) -> dict[str, Any]:
    values = {
        "civil_datetime": datetime.fromisoformat("2005-12-24T00:05:00+08:00"),
        "timezone_id": "Asia/Shanghai",
        "longitude": 102.0,
        "latitude": 27.0,
        "sex_for_rule": "male",
    }
    values.update(updates)
    return values


def test_birth_input_rejects_unsupported_year_and_extra_fields() -> None:
    with pytest.raises(ValidationError):
        BirthInput(**valid_birth(civil_datetime=datetime.fromisoformat("0001-01-01T00:00:00+08:00")))
    with pytest.raises(ValidationError):
        BirthInput(**valid_birth(unexpected="value"))


def test_transit_requests_reject_unsupported_years() -> None:
    birth = BirthInput(**valid_birth())
    with pytest.raises(ValidationError):
        DailyTransitRequest(birth=birth, transit_date=date(1, 1, 1))
    with pytest.raises(ValidationError):
        TransitRequest(birth=birth, transit_date=date(9999, 1, 1))
    with pytest.raises(ValidationError):
        TransitWindowRequest(birth=birth, start_date=date(1848, 12, 31), end_date=date(1849, 1, 1))


def run_guard(
    body: bytes,
    *,
    limit: int = 16_384,
    rate: int = 90,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []

    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await receive()
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestGuardMiddleware(endpoint, max_body_bytes=limit, requests_per_minute=rate)

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/charts",
        "client": ("127.0.0.1", 1),
        "headers": headers or [],
    }
    asyncio.run(middleware(scope, receive, send))
    return messages


def test_request_guard_rejects_large_body() -> None:
    messages = run_guard(b"x" * 33, limit=32)
    start = messages[0]
    assert start["status"] == 413
    headers = dict(start["headers"])
    assert headers[b"cache-control"] == b"no-store"
    assert headers[b"x-content-type-options"] == b"nosniff"
    assert headers[b"x-frame-options"] == b"DENY"
    assert headers[b"strict-transport-security"] == b"max-age=31536000; includeSubDomains"


def test_request_guard_adds_security_headers() -> None:
    messages = run_guard(b"{}")
    start = messages[0]
    assert start["status"] == 204
    headers = dict(start["headers"])
    assert headers[b"content-security-policy"] == b"default-src 'none'; frame-ancestors 'none'"
    assert headers[b"referrer-policy"] == b"no-referrer"


def test_request_guard_rejects_oversized_declared_body_without_reading() -> None:
    messages = run_guard(b"{}", limit=32, headers=[(b"content-length", b"33")])
    assert messages[0]["status"] == 413


def test_request_guard_times_out_slow_body_and_releases_reader_slot() -> None:
    messages: list[dict[str, Any]] = []

    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await receive()
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestGuardMiddleware(
        endpoint,
        request_body_timeout_seconds=0.03,
        max_concurrent_body_readers=1,
    )
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/charts",
        "client": ("127.0.0.1", 1),
        "headers": [],
    }

    async def scenario() -> float:
        gate = asyncio.Event()

        async def stalled_receive() -> dict[str, Any]:
            await gate.wait()
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message: dict[str, Any]) -> None:
            messages.append(message)

        started = monotonic()
        await middleware(scope, stalled_receive, send)
        elapsed = monotonic() - started

        async def normal_receive() -> dict[str, Any]:
            return {"type": "http.request", "body": b"{}", "more_body": False}

        await middleware({**scope, "client": ("127.0.0.2", 1)}, normal_receive, send)
        return elapsed

    elapsed = asyncio.run(scenario())
    statuses = [message["status"] for message in messages if message["type"] == "http.response.start"]
    assert statuses == [408, 204]
    assert elapsed < 0.2


def test_ai_rate_limit_does_not_block_core_calculation_pool() -> None:
    messages: list[dict[str, Any]] = []

    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await receive()
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestGuardMiddleware(
        endpoint,
        requests_per_minute=20,
        ai_requests_per_minute=1,
        ai_global_requests_per_minute=10,
    )

    async def call(path: str) -> None:
        delivered = False

        async def receive() -> dict[str, Any]:
            nonlocal delivered
            if delivered:
                return {"type": "http.disconnect"}
            delivered = True
            return {"type": "http.request", "body": b"{}", "more_body": False}

        async def send(message: dict[str, Any]) -> None:
            messages.append(message)

        await middleware({
            "type": "http", "method": "POST", "path": path,
            "client": ("127.0.0.1", 1), "headers": [(b"content-length", b"2")],
        }, receive, send)

    async def scenario() -> None:
        await call("/v1/ai/explain")
        await call("/v1/ai/explain")
        await call("/v1/charts")

    asyncio.run(scenario())
    statuses = [message["status"] for message in messages if message["type"] == "http.response.start"]
    assert statuses == [204, 429, 204]


def _guard_call(
    middleware: RequestGuardMiddleware,
    *,
    path: str,
    body: bytes,
    client: str = "127.0.0.1",
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> int:
    messages: list[dict[str, Any]] = []
    delivered = False

    async def receive() -> dict[str, Any]:
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    headers = [(b"content-length", str(len(body)).encode())]
    if extra_headers:
        headers.extend(extra_headers)
    asyncio.run(middleware({
        "type": "http",
        "method": "POST",
        "path": path,
        "client": (client, 1),
        "headers": headers,
    }, receive, send))
    start = next(message for message in messages if message["type"] == "http.response.start")
    return int(start["status"])


def test_ai_rate_limit_charges_each_split_question() -> None:
    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await receive()
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestGuardMiddleware(
        endpoint,
        requests_per_minute=20,
        ai_requests_per_minute=4,
        ai_global_requests_per_minute=20,
    )
    payload = json.dumps({
        "question": "讲讲",
        "context_tokens": ["x" * 32],
        "split_questions": ["早年", "中年", "晚年"],
    }).encode()
    assert _guard_call(middleware, path="/v1/ai/explain", body=payload) == 204
    assert _guard_call(middleware, path="/v1/ai/explain", body=b"{}") == 429
    assert _guard_call(middleware, path="/v1/charts", body=b"{}") == 204


def test_ai_rate_limit_rejects_request_that_exceeds_budget_in_one_call() -> None:
    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await receive()
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestGuardMiddleware(
        endpoint,
        ai_requests_per_minute=3,
        ai_global_requests_per_minute=20,
    )
    payload = json.dumps({
        "question": "讲讲",
        "split_questions": ["a", "b", "c"],
    }).encode()
    assert _guard_call(middleware, path="/v1/ai/explain", body=payload) == 429


def test_trusted_proxy_rate_limits_by_rightmost_forwarded_ip() -> None:
    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await receive()
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestGuardMiddleware(
        endpoint,
        requests_per_minute=1,
        trust_proxy=True,
    )
    assert _guard_call(
        middleware,
        path="/v1/charts",
        body=b"{}",
        client="10.0.0.1",
        extra_headers=[(b"x-forwarded-for", b"8.8.8.8, 203.0.113.10")],
    ) == 204
    assert _guard_call(
        middleware,
        path="/v1/charts",
        body=b"{}",
        client="10.0.0.1",
        extra_headers=[(b"x-forwarded-for", b"1.1.1.1, 198.51.100.20")],
    ) == 204
    assert _guard_call(
        middleware,
        path="/v1/charts",
        body=b"{}",
        client="10.0.0.1",
        extra_headers=[(b"x-forwarded-for", b"9.9.9.9, 203.0.113.10")],
    ) == 429


def test_untrusted_forwarded_for_does_not_split_rate_limit_buckets() -> None:
    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await receive()
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestGuardMiddleware(endpoint, requests_per_minute=1)
    assert _guard_call(
        middleware,
        path="/v1/charts",
        body=b"{}",
        extra_headers=[(b"x-forwarded-for", b"203.0.113.10")],
    ) == 204
    assert _guard_call(
        middleware,
        path="/v1/charts",
        body=b"{}",
        extra_headers=[(b"x-forwarded-for", b"198.51.100.20")],
    ) == 429


def test_calculation_timeout_cancels_task_and_keeps_core_available() -> None:
    messages: list[tuple[str, int]] = []
    calc_cancelled = False

    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        nonlocal calc_cancelled
        await receive()
        if scope["path"] == "/v1/charts":
            try:
                await asyncio.Event().wait()
            finally:
                calc_cancelled = True
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestGuardMiddleware(
        endpoint,
        calculation_timeout_seconds=0.03,
        max_concurrent_calculations=1,
    )

    async def call(path: str) -> None:
        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": b"{}", "more_body": False}

        async def send(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                messages.append((path, message["status"]))

        await middleware({
            "type": "http", "method": "POST", "path": path,
            "client": ("127.0.0.1", 1), "headers": [(b"content-length", b"2")],
        }, receive, send)

    async def scenario() -> None:
        await call("/v1/charts")
        await call("/v1/transits/daily")

    asyncio.run(scenario())
    assert calc_cancelled
    assert messages == [("/v1/charts", 504), ("/v1/transits/daily", 204)]


def test_static_security_middleware_adds_frame_deny_and_csp() -> None:
    from security import StaticSecurityMiddleware

    messages: list[dict[str, Any]] = []

    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/html")],
        })
        await send({"type": "http.response.body", "body": b"<html></html>"})

    middleware = StaticSecurityMiddleware(endpoint)

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    asyncio.run(middleware({
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
    }, receive, send))
    start = next(message for message in messages if message["type"] == "http.response.start")
    headers = dict(start["headers"])
    assert headers[b"x-frame-options"] == b"DENY"
    assert headers[b"x-content-type-options"] == b"nosniff"
    assert b"frame-ancestors 'none'" in headers[b"content-security-policy"]
    assert headers[b"referrer-policy"] == b"no-referrer"


def test_ai_timeout_cancels_provider_task_and_keeps_core_available() -> None:
    messages: list[tuple[str, int]] = []
    ai_cancelled = False

    async def endpoint(scope: dict[str, Any], receive: Any, send: Any) -> None:
        nonlocal ai_cancelled
        await receive()
        if scope["path"] == "/v1/ai/explain":
            try:
                await asyncio.Event().wait()
            finally:
                ai_cancelled = True
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestGuardMiddleware(
        endpoint,
        ai_timeout_seconds=0.03,
        max_concurrent_ai_requests=1,
        max_concurrent_calculations=1,
    )

    async def call(path: str) -> None:
        async def receive() -> dict[str, Any]:
            return {"type": "http.request", "body": b"{}", "more_body": False}

        async def send(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                messages.append((path, message["status"]))

        await middleware({
            "type": "http", "method": "POST", "path": path,
            "client": ("127.0.0.1", 1), "headers": [(b"content-length", b"2")],
        }, receive, send)

    async def scenario() -> None:
        await call("/v1/ai/explain")
        await call("/v1/charts")

    asyncio.run(scenario())
    assert ai_cancelled
    assert messages == [("/v1/ai/explain", 504), ("/v1/charts", 204)]


def test_ephemeris_integrity_check_accepts_only_expected_digest(tmp_path: Path) -> None:
    ephemeris = tmp_path / "ephemeris.bsp"
    ephemeris.write_bytes(b"trusted fixture")
    expected = hashlib.sha256(b"trusted fixture").hexdigest()
    assert _verify_ephemeris(ephemeris, expected) == expected

    ephemeris.write_bytes(b"tampered fixture")
    with pytest.raises(RuntimeError, match="integrity"):
        _verify_ephemeris(ephemeris, expected)
    with pytest.raises(RuntimeError, match="missing"):
        _verify_ephemeris(tmp_path / "missing.bsp", expected)


def test_unverified_manual_solar_time_is_not_marked_verified() -> None:
    moment = datetime.fromisoformat("2005-12-24T00:05:00+08:00")
    birth = BirthInput(**valid_birth(apparent_solar_datetime=moment))
    bazi = calculate_bazi(birth)
    ziwei = calculate_palaces(birth)
    assert bazi.apparent_solar_source == "provided"
    assert bazi.verification_status == "ambiguous"
    assert bazi.warnings
    assert ziwei.verification_status == "ambiguous"


def api_birth(civil_datetime: str = "2005-12-24T00:05:00+08:00") -> dict[str, Any]:
    return {
        "civil_datetime": civil_datetime,
        "timezone_id": "Asia/Shanghai",
        "longitude": 102.0,
        "latitude": 27.0,
        "sex_for_rule": "male",
        "use_apparent_solar_time": True,
    }


def call_api(path: str, payload: dict[str, Any]) -> tuple[int, dict[bytes, bytes], str]:
    body = json.dumps(payload).encode()
    messages: list[dict[str, Any]] = []
    delivered = False

    async def receive() -> dict[str, Any]:
        nonlocal delivered
        if delivered:
            return {"type": "http.disconnect"}
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "http",
        "method": "POST",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ],
        "client": ("127.0.0.1", 1),
        "server": ("testserver", 80),
    }
    try:
        asyncio.run(api_module.app(scope, receive, send))
    except Exception:
        if not messages:
            raise
    start = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
    return start["status"], dict(start["headers"]), response_body.decode()


def test_validation_response_omits_submitted_birth_input() -> None:
    status, headers, response_text = call_api("/v1/charts", api_birth("2005-12-24T00:05:00+07:00"))
    assert status == 422
    body = json.loads(response_text)
    assert body["detail"]
    assert all("input" not in item and "ctx" not in item for item in body["detail"])
    assert "2005-12-24" not in response_text
    assert headers[b"cache-control"] == b"no-store"


def test_unhandled_error_is_generic_and_keeps_security_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_closed(_birth: Any) -> None:
        raise RuntimeError("SENSITIVE_INTERNAL_MARKER")

    monkeypatch.setattr(api_module, "calculate_bazi", fail_closed)
    status, headers, response_text = call_api("/v1/charts", api_birth())
    assert status == 500
    assert json.loads(response_text)["detail"] == "Internal server error"
    assert "SENSITIVE_INTERNAL_MARKER" not in response_text
    assert headers[b"cache-control"] == b"no-store"
    assert headers[b"x-content-type-options"] == b"nosniff"
