"""奇门视图 E2E：表单 → 起局（真引擎确定性计算）→ 流式解读（route mock，零配额）。

需要本地 vite:5173 + api:8000 在跑；AI 流式端点用 page.route mock 保证确定性。
"""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from fortune_core.qimen import build_output

FRONTEND = "http://127.0.0.1:5173"

# 固定起局时刻 → 确定性盘面（与差分基线同源）
CHART_REQUEST = {
    "question_type": "事业",
    "question_goal": "能不能动，什么时候动更稳",
    "time_mode": "custom",
    "time_input": "2026-03-24 10:30",
    "city": "上海",
}


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


def _deterministic_chart() -> dict:
    payload = {
        "question_type": CHART_REQUEST["question_type"],
        "question_goal": CHART_REQUEST["question_goal"],
        "time_input": CHART_REQUEST["time_input"],
        "calendar_type": "solar",
        "location": {"country": "", "city": CHART_REQUEST["city"], "timezone": ""},
        "ruleset": "mainline-cn-v1",
    }
    out = build_output(payload)
    return {
        "question_type": CHART_REQUEST["question_type"],
        "question_goal": CHART_REQUEST["question_goal"],
        "detail_level": "brief",
        "city": CHART_REQUEST["city"],
        "used_now": False,
        "calendar_solar": out["calendar"]["solar"]["ymd_hms"],
        "calendar_lunar": out["calendar"]["lunar"],
        "jieqi": out["calendar"]["jieqi"],
        "ganzhi": out["ganzhi"],
        "chart": out["chart"],
        "warnings": out["warnings"],
    }


def _mock_qimen(page: Page) -> None:
    chart = json.dumps(_deterministic_chart(), ensure_ascii=False)
    page.route("**/v1/qimen/chart", lambda route: route.fulfill(
        status=200, content_type="application/json", body=chart,
    ))
    page.route("**/v1/qimen/interpret/stream", lambda route: route.fulfill(
        status=200, content_type="text/event-stream",
        body=(
            'data: {"type":"think","text":"盘面已读"}\n\n'
            'data: {"type":"delta","text":"阳遁一局，缓动为宜。"}\n\n'
            'data: {"type":"done"}\n\n'
        ),
    ))


def test_qimen_view_cast_and_interpret(require_servers: None) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
        _mock_qimen(page)
        page.goto(f"{FRONTEND}/#qimen", wait_until="networkidle")
        page.locator("#qimen select").first.select_option("事业")
        page.locator("#qimen textarea").fill("能不能动，什么时候动更稳")
        page.get_by_role("button", name="起局", exact=True).click()
        page.locator(".qimen-chart-card").wait_for(timeout=15_000)
        expect(page.locator(".qimen-chart-card")).to_contain_text("阳遁1局", timeout=10_000)
        expect(page.locator(".qimen-chart-card")).to_contain_text("三奇配吉门", timeout=10_000)
        page.get_by_role("button", name="读盘").click()
        page.locator(".dream-result").wait_for(timeout=15_000)
        # 打字机节奏器在 done 后仍需排空尾部字符，断言必须自动重试等全文。
        expect(page.locator(".dream-result")).to_contain_text("缓动为宜", timeout=10_000)
        browser.close()


def test_qimen_nav_present(require_servers: None) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
        _mock_qimen(page)
        page.goto(FRONTEND, wait_until="networkidle")
        expect(page.locator('.primary-nav a[href="#qimen"]')).to_contain_text("奇门")
        browser.close()
