"""Small, dependency-free HTTP guards for the public calculation API."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from time import monotonic
from typing import Any, Awaitable, Callable


Scope = dict[str, Any]
Message = dict[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


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
        is_ai = method == "POST" and path in {"/v1/ai/explain", "/v1/dreams/interpret"}
        is_calculation = method == "POST" and path.startswith("/v1/")
        if is_calculation:
            client = scope.get("client") or ("unknown", 0)
            if not self._allow_request(str(client[0])):
                await self._send_json(guarded_send, 429, b'{"detail":"Too many requests"}', [(b"retry-after", b"60")])
                return
            if is_ai and not self._allow_ai_request(str(client[0])):
                await self._send_json(guarded_send, 429, b'{"detail":"Too many AI requests"}', [(b"retry-after", b"60")])
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

            delivered = False

            async def replay_receive() -> Message:
                nonlocal delivered
                if delivered:
                    return {"type": "http.disconnect"}
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}

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
        try:
            timeout_seconds = self.ai_timeout_seconds if is_ai else self.calculation_timeout_seconds
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout_seconds)
        except TimeoutError:
            if task.done():
                await task
                return
            response_expired = True
            if is_ai:
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

    def _allow_ai_request(self, client: str) -> bool:
        now = monotonic()
        cutoff = now - 60
        while self._ai_global_requests and self._ai_global_requests[0] < cutoff:
            self._ai_global_requests.popleft()
        if len(self._ai_global_requests) >= self.ai_global_requests_per_minute:
            return False
        bucket = self._ai_requests[client]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.ai_requests_per_minute:
            return False
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
