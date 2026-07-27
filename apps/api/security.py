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
        max_concurrent_calculations: int = 8,
        calculation_timeout_seconds: float = 12.0,
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.requests_per_minute = requests_per_minute
        self.global_requests_per_minute = global_requests_per_minute
        self.calculation_timeout_seconds = calculation_timeout_seconds
        self._calculation_slots = asyncio.Semaphore(max_concurrent_calculations)
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._global_requests: deque[float] = deque()
        self._background_tasks: set[asyncio.Task[None]] = set()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        guarded_send = self._security_headers(send)
        method = str(scope.get("method", "GET")).upper()
        path = str(scope.get("path", ""))
        is_calculation = method == "POST" and path.startswith("/v1/")
        if is_calculation:
            client = scope.get("client") or ("unknown", 0)
            if not self._allow_request(str(client[0])):
                await self._send_json(guarded_send, 429, b'{"detail":"Too many requests"}', [(b"retry-after", b"60")])
                return
            body = await self._read_limited_body(receive)
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

        try:
            await asyncio.wait_for(self._calculation_slots.acquire(), timeout=1.5)
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
                self._calculation_slots.release()

        task = asyncio.create_task(run_calculation())
        self._background_tasks.add(task)
        task.add_done_callback(self._finish_background_task)
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=self.calculation_timeout_seconds)
        except TimeoutError:
            if task.done():
                await task
                return
            response_expired = True
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
