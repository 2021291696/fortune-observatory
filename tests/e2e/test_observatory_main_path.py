from __future__ import annotations

import json
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


def fill_birth(page: Page) -> None:
    page.locator('input[name="displayName"]').fill("我")
    page.locator('select[aria-label="出生年"]').select_option("2000")
    page.locator('select[aria-label="出生月"]').select_option("1")
    page.locator('select[aria-label="出生日"]').select_option("1")
    page.locator('select[aria-label="出生时（24 小时制）"]').select_option("8")
    page.locator('select[aria-label="出生分"]').select_option("30")
    page.locator('select[aria-label="省份"]').select_option("110000")
    page.locator('select[aria-label="城市或辖区"]').select_option("110101")


def ensure_ai_contexts(page: Page) -> None:
    # api:8000 未带 FORTUNE_AI_CONTEXT_SECRET 启动时 /v1/charts 不发签名
    # 上下文，问事 AI 卡走 unavailable 分支，.ai-answer 永不出现——环境问题
    # 在这里给出可行动提示，而不是让断言超时假死。
    response = page.request.post(
        "http://127.0.0.1:8000/v1/charts",
        data={
            "civil_datetime": "2000-01-01T08:30:00+08:00",
            "timezone_id": "Asia/Shanghai",
            "longitude": 116.4,
            "latitude": 39.9,
            "sex_for_rule": "male",
            "use_apparent_solar_time": True,
        },
        headers={"content-type": "application/json"},
        timeout=10_000,
    )
    if response.ok and not (response.json() or {}).get("ai_contexts"):
        pytest.skip("api:8000 未带 FORTUNE_AI_CONTEXT_SECRET 启动，/v1/charts 无签名上下文；重启命令见 AGENTS.md「本地跑」")


def mock_ai(page: Page) -> None:
    page.route("**/v1/ai/status", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='{"available":true,"mode":"on_demand","attaches_birth_profile":false}',
    ))
    page.route("**/v1/ai/explain", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=json.dumps({
            "summary": {"text": "把这一步拆小再验证。", "fact_ids": ["domain-1"]},
            "actions": [{"text": "先做一件能复查的小事。", "fact_ids": ["domain-1"]}],
            "caveats": [{"text": "这不是确定结果。", "fact_ids": ["domain-1"]}],
        }, ensure_ascii=False),
    ))
    page.route("**/v1/dreams/interpret", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body=json.dumps({
            "essay": "蛇入怀，传统多作亲近或子息之象。",
            "sources": [{"work": "周公解梦", "quote": "蛇入怀中生贵子", "channel": "字面"}],
            "overlay": None,
            "referral": None,
        }, ensure_ascii=False),
    ))
    # 流式解读/解梦（真实模型思考时长波动大，必须 mock 保证 e2e 确定、不烧配额）。
    page.route("**/v1/ai/reading", lambda route: route.fulfill(
        status=200, content_type="text/event-stream",
        body=(
            'data: {"type":"think","text":"推演中"}\n\n'
            'data: {"type":"delta","text":"把这一步拆小再验证。"}\n\n'
            'data: {"type":"done"}\n\n'
        ),
    ))
    page.route("**/v1/dreams/interpret/stream", lambda route: route.fulfill(
        status=200, content_type="text/event-stream",
        body=(
            'data: {"type":"delta","text":"蛇入怀，传统多作亲近或子息之象。"}\n\n'
            'data: {"type":"done","sources":[{"work":"周公解梦","quote":"蛇入怀中生贵子","channel":"字面"}]}\n\n'
        ),
    ))


def test_observatory_main_path_desktop(require_servers: None) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
        mock_ai(page)
        ensure_ai_contexts(page)
        page.goto(FRONTEND, wait_until="networkidle")
        page.locator('.primary-nav a[href="#fortune"]').click()
        page.locator("#birth-form").wait_for(timeout=10_000)
        fill_birth(page)
        page.get_by_role("button", name="排盘并看运势").click()
        page.locator("#chart .pillars-board").wait_for(timeout=20_000)
        page.get_by_text("我的盘已就绪", exact=True).wait_for(timeout=20_000)
        page.locator('.primary-nav a[href="#fortune"]').click()
        page.locator("#fortune .fortune-reading").wait_for(timeout=20_000)
        page.locator('.primary-nav a[href="#ask"]').click()
        page.locator(".domain-choices button", has_text="事业").click()
        page.locator("#analysis .ai-answer").wait_for(timeout=15_000)
        # 打字机节奏器在 done 后仍需十几毫秒排空尾部字符，断言必须自动重试等全文。
        expect(page.locator("#analysis .ai-answer")).to_contain_text("拆小再验证", timeout=10_000)
        page.locator('.primary-nav a[href="#dream"]').click()
        page.locator("#dream textarea").fill("梦见一条蛇钻进怀里然后醒了")
        page.get_by_role("button", name="解读").click()
        page.locator(".dream-result").wait_for(timeout=15_000)
        expect(page.locator(".dream-result")).to_contain_text("蛇入怀", timeout=10_000)
        browser.close()


def test_observatory_main_path_mobile_375(require_servers: None) -> None:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 375, "height": 812}, locale="zh-CN")
        mock_ai(page)
        ensure_ai_contexts(page)
        page.goto(FRONTEND, wait_until="networkidle")
        page.locator('.primary-nav a[href="#fortune"]').click()
        page.locator("#birth-form").wait_for(timeout=10_000)
        fill_birth(page)
        page.get_by_role("button", name="排盘并看运势").click()
        page.locator("#chart .pillars-board").wait_for(timeout=20_000)
        metrics = page.evaluate(
            """() => ({
              viewport: document.documentElement.clientWidth,
              body: document.body.scrollWidth,
            })"""
        )
        assert metrics["body"] <= metrics["viewport"] + 1, metrics
        assert page.locator(".primary-nav a").count() == 6
        browser.close()
