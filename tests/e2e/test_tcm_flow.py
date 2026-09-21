"""中医问诊视图 E2E：自由问诊 → 流式回答（route mock，零配额）。

需要本地 vite:5173 + api:8000 在跑；AI 流式端点用 page.route mock 保证确定性。
"""

from __future__ import annotations

import socket

import pytest
from playwright.sync_api import Page, expect, sync_playwright

FRONTEND = "http://127.0.0.1:5173"


def _up(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


@pytest.fixture(scope="module")
def require_servers() -> None:
    if not (_up("127.0.0.1", 5173) and _up("127.0.0.1", 8000)):
        pytest.skip("vite:5173 or api:8000 not running")


def _mock_tcm(page: Page) -> None:
    page.route("**/v1/tcm/consult/stream", lambda route: route.fulfill(
        status=200, content_type="text/event-stream",
        body=(
            'data: {"type":"think","text":"先辨六经"}\n\n'
            'data: {"type":"delta","text":"我跟你说，这是太阳中风，桂枝汤主之，汗一透就没了。"}\n\n'
            'data: {"type":"done","sources":[{"work":"《伤寒论》","quote":"太阳中风，阳浮而阴弱"}]}\n\n'
        ),
    ))


def test_tcm_view_consult_flow(require_servers: None) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
        _mock_tcm(page)
        page.goto(f"{FRONTEND}/#tcm", wait_until="networkidle")
        page.locator("#tcm textarea").fill("感冒出汗怕风，脖子后面发僵")
        page.get_by_role("button", name="开始问诊", exact=True).click()
        page.locator(".dream-result").wait_for(timeout=15_000)
        # 打字机节奏器在 done 后仍需排空尾部字符，断言必须自动重试等全文。
        expect(page.locator(".dream-result")).to_contain_text("桂枝汤主之", timeout=10_000)
        expect(page.locator(".dream-result")).to_contain_text("本次引用的口径", timeout=10_000)
        browser.close()


def test_tcm_nav_present(require_servers: None) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
        _mock_tcm(page)
        page.goto(FRONTEND, wait_until="networkidle")
        expect(page.locator('.primary-nav a[href="#tcm"]')).to_contain_text("中医")
        browser.close()
