"""Small, dependency-free HTTP guards for the public calculation API."""

from __future__ import annotations

import asyncio
import ipaddress
import json
from collections import defaultdict, deque
from time import monotonic
from typing import Any, Awaitable, Callable


Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


# AI 流式路径（reading/解梦 SSE）是长连接：M3 思考+输出可达数分钟，
# 不套用单次调用总时长门（12s/28s），超时由 provider 侧 FORTUNE_AI_TIMEOUT_SECONDS
# 兜底；客户端断开时生成器随之取消。仍走 AI 并发槽与限流。
_STREAMING_AI_PATHS = frozenset({"/v1/ai/reading", "/v1/dreams/interpret/stream"})


class RequestGuardMiddleware:
    def __init__(
        self,
        app: Callable[..., Awaitable[None]],
        *,
        max_body_bytes: int = 16_384,
        requests_per_minute: int = 90,
        global_requests_per_minute: int = 900,
        ai_requests_per_minute: int = 6,
        ai_global_requests_per_minute: int = 60,
        max_concurrent_body_readers: int = 32,
        request_body_timeout_seconds: float = 5.0,
        max_concurrent_calculations: int = 8,
        calculation_timeout_seconds: float = 12.0,
        max_concurrent_ai_requests: int = 3,
        ai_timeout_seconds: float = 10.5,
        trust_proxy: bool = False,
        client_ip_header: str = "x-forwarded-for",
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.requests_per_minute = requests_per_minute
        self.global_requests_per_minute = global_requests_per_minute
        self.ai_requests_per_minute = ai_requests_per_minute
        self.ai_global_requests_per_minute = ai_global_requests_per_minute
        self.request_body_timeout_seconds = request_body_timeout_seconds
        self.calculation_timeout_seconds = calculation_timeout_seconds
        self.ai_timeout_seconds = ai_timeout_seconds
        self.trust_proxy = trust_proxy
        self.client_ip_header = client_ip_header.lower().encode("ascii")
        self._body_reader_slots = asyncio.Semaphore(max_concurrent_body_readers)
        self._calculation_slots = asyncio.Semaphore(max_concurrent_calculations)
        self._ai_slots = asyncio.Semaphore(max_concurrent_ai_requests)
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._global_requests: deque[float] = deque()
        self._ai_requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._ai_global_requests: deque[float] = deque()
        self._background_tasks: set[asyncio.Task[None]] = set()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        guarded_send = self._security_headers(send)
        method = str(scope.get("method", "GET")).upper()
        path = str(scope.get("path", ""))
        is_streaming_ai = path in _STREAMING_AI_PATHS
        is_ai = method == "POST" and (
            path in {"/v1/ai/explain", "/v1/dreams/interpret", "/v1/dreams/questions"} or is_streaming_ai
        )
        is_calculation = method == "POST" and path.startswith("/v1/")
        if is_calculation:
            client = self._client_ip(scope)
            if not self._allow_request(client):
                await self._send_json(guarded_send, 429, b'{"detail":"Too many requests"}', [(b"retry-after", b"60")])
                return
            declared_length = self._content_length(scope)
            if declared_length is None:
                await self._send_json(guarded_send, 400, b'{"detail":"Invalid Content-Length"}')
                return
            if declared_length > self.max_body_bytes:
                await self._send_json(guarded_send, 413, b'{"detail":"Request body too large"}')
                return
            try:
                await asyncio.wait_for(self._body_reader_slots.acquire(), timeout=1.0)
            except TimeoutError:
                await self._send_json(guarded_send, 503, b'{"detail":"Server is busy"}', [(b"retry-after", b"2")])
                return
            try:
                body = await asyncio.wait_for(
                    self._read_limited_body(receive),
                    timeout=self.request_body_timeout_seconds,
                )
            except TimeoutError:
                await self._send_json(guarded_send, 408, b'{"detail":"Request body timed out"}')
                return
            finally:
                self._body_reader_slots.release()
            if body is None:
                await self._send_json(guarded_send, 413, b'{"detail":"Request body too large"}')
                return
            if is_ai and not self._allow_ai_request(client, self._ai_request_units(body)):
                await self._send_json(guarded_send, 429, b'{"detail":"Too many AI requests"}', [(b"retry-after", b"60")])
                return

            delivered = False
            original_receive = receive

            async def replay_receive() -> Message:
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": body, "more_body": False}
                # body 已交付后的后续读：转发真实 receive（挂起等待真实断开）。
                # 不能用二次调用即报 disconnect——Starlette 旧 ASGI spec 的
                # StreamingResponse 会把该信号误判为客户端断开而取消响应流。
                return await original_receive()

            receive = replay_receive

        if not is_calculation:
            await self.app(scope, receive, guarded_send)
            return

        work_slots = self._ai_slots if is_ai else self._calculation_slots
        try:
            await asyncio.wait_for(work_slots.acquire(), timeout=1.5)
        except TimeoutError:
            await self._send_json(guarded_send, 503, b'{"detail":"Server is busy"}', [(b"retry-after", b"2")])
            return
        response_expired = False

        async def deadline_send(message: Message) -> None:
            if not response_expired:
                await guarded_send(message)

        async def run_calculation() -> None:
            try:
                await self.app(scope, receive, deadline_send)
            finally:
                work_slots.release()

        task = asyncio.create_task(run_calculation())
        self._background_tasks.add(task)
        task.add_done_callback(self._finish_background_task)
        if is_streaming_ai:
            # 长连接不设总时长门：await 到生成器自然结束（客户端断开即取消）。
            try:
                await task
            except asyncio.CancelledError:
                raise
            return
        try:
            timeout_seconds = self.ai_timeout_seconds if is_ai else self.calculation_timeout_seconds
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout_seconds)
        except TimeoutError:
            if task.done():
                await task
                return
            response_expired = True
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await self._send_json(guarded_send, 504, b'{"detail":"Calculation timed out"}', [(b"retry-after", b"2")])

    def _finish_background_task(self, task: asyncio.Task[None]) -> None:
        self._background_tasks.discard(task)
        if not task.cancelled():
            task.exception()

    async def _read_limited_body(self, receive: Receive) -> bytes | None:
        chunks: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message.get("type") == "http.disconnect":
                return b""
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > self.max_body_bytes:
                return None
            chunks.append(chunk)
            if not message.get("more_body", False):
                return b"".join(chunks)

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        values = [value for name, value in scope.get("headers", []) if name.lower() == b"content-length"]
        if not values:
            return 0
        if len(values) != 1:
            return None
        try:
            value = int(values[0])
        except (TypeError, ValueError):
            return None
        return value if value >= 0 else None

    def _client_ip(self, scope: Scope) -> str:
        peer = str((scope.get("client") or ("unknown", 0))[0])
        if not self.trust_proxy:
            return peer
        values = [
            value.decode("latin-1")
            for name, value in scope.get("headers", [])
            if name.lower() == self.client_ip_header
        ]
        if len(values) != 1:
            return peer
        parts = [item.strip() for item in values[0].split(",") if item.strip()]
        if not parts:
            return peer
        candidate = parts[-1]
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            return peer
        return candidate

    @staticmethod
    def _ai_request_units(body: bytes) -> int:
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return 1
        if not isinstance(payload, dict):
            return 1
        splits = payload.get("split_questions")
        if not isinstance(splits, list):
            return 1
        return 1 + min(len(splits), 4)

    def _allow_request(self, client: str) -> bool:
        now = monotonic()
        cutoff = now - 60
        while self._global_requests and self._global_requests[0] < cutoff:
            self._global_requests.popleft()
        if len(self._global_requests) >= self.global_requests_per_minute:
            return False
        bucket = self._requests[client]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.requests_per_minute:
            return False
        self._global_requests.append(now)
        bucket.append(now)
        if len(self._requests) > 2_048:
            active = {key: value for key, value in self._requests.items() if value and value[-1] >= cutoff}
            self._requests = defaultdict(deque, active)
        return True

    def _allow_ai_request(self, client: str, units: int = 1) -> bool:
        now = monotonic()
        cutoff = now - 60
        charge = max(1, units)
        while self._ai_global_requests and self._ai_global_requests[0] < cutoff:
            self._ai_global_requests.popleft()
        if len(self._ai_global_requests) + charge > self.ai_global_requests_per_minute:
            return False
        bucket = self._ai_requests[client]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) + charge > self.ai_requests_per_minute:
            return False
        for _ in range(charge):
            self._ai_global_requests.append(now)
            bucket.append(now)
        if len(self._ai_requests) > 2_048:
            active = {key: value for key, value in self._ai_requests.items() if value and value[-1] >= cutoff}
            self._ai_requests = defaultdict(deque, active)
        return True

    @staticmethod
    def _security_headers(send: Send) -> Send:
        async def wrapped(message: Message) -> None:
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                additions = (
                    (b"cache-control", b"no-store"),
                    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
                    (b"cross-origin-resource-policy", b"same-site"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=()"),
                    (b"referrer-policy", b"no-referrer"),
                    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                )
                headers.extend((name, value) for name, value in additions if name not in present)
                message = {**message, "headers": headers}
            await send(message)

        return wrapped

    @staticmethod
    async def _send_json(send: Send, status: int, body: bytes, extra_headers: list[tuple[bytes, bytes]] | None = None) -> None:
        headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
        if extra_headers:
            headers.extend(extra_headers)
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})


class StaticSecurityMiddleware:
    """Security headers for the Docker-served SPA (not the JSON API)."""

    _additions = (
        (b"content-security-policy", (
            b"default-src 'self'; img-src 'self' data:; media-src 'self'; "
            b"style-src 'self'; style-src-attr 'unsafe-inline'; script-src 'self'; "
            b"connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; "
            b"form-action 'self'; object-src 'none'"
        )),
        (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=()"),
        (b"referrer-policy", b"no-referrer"),
        (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
    )

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        async def wrapped(message: Message) -> None:
            if message.get("type") == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                headers.extend((name, value) for name, value in self._additions if name not in present)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, wrapped)
