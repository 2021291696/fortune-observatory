from __future__ import annotations

import json
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


FRONTEND_URL = "http://127.0.0.1:5173"
ARTIFACTS = Path(__file__).resolve().parents[1] / ".artifacts"


def assert_no_overflow(page: Page) -> None:
    metrics = page.evaluate(
        """() => ({
          viewport: document.documentElement.clientWidth,
          body: document.body.scrollWidth,
          document: document.documentElement.scrollWidth,
        })"""
    )
    assert metrics["body"] <= metrics["viewport"] + 1, metrics
    assert metrics["document"] <= metrics["viewport"] + 1, metrics


def assert_touch_targets(page: Page) -> None:
    too_small = page.evaluate(
        """() => [...document.querySelectorAll('button,input,select,textarea,summary,a')]
          .filter((node) => {
            const rect = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 1 && rect.height > 1 && (rect.height < 44 || rect.width < 44);
          })
          .map((node) => ({tag: node.tagName, name: node.getAttribute('name'), text: node.textContent?.trim(), height: node.getBoundingClientRect().height}))"""
    )
    assert not too_small, too_small


def fill_birth(page: Page, name: str = "我", prov: str = "110000", city: str = "110101", date: str = "2000-01-01", time: str = "08:30") -> None:
    page.locator('input[name="displayName"]').fill(name)
    page.locator('input[name="civilDate"]').fill(date)
    page.locator('input[name="civilTime"]').fill(time)
    page.locator('select[aria-label="省份"]').select_option(prov)
    if city:
        page.locator('select[aria-label="城市或辖区"]').select_option(city)


def submit_and_wait(page: Page, name: str = "我") -> None:
    page.get_by_role("button", name="排盘并看运势").click()
    page.locator("#chart .pillars-board").wait_for(timeout=20_000)
    page.locator("#chart .dayun-strip").wait_for(timeout=20_000)
    page.get_by_text(f"{name}的盘已就绪", exact=True).wait_for(timeout=20_000)
    page.locator('.primary-nav a[href="#fortune"]').click()
    page.locator("#fortune .fortune-reading").wait_for(timeout=20_000)
    page.wait_for_timeout(700)


def capture_console(page: Page) -> list[str]:
    errors: list[str] = []
    page.on("console", lambda message: errors.append(f"console:{message.type}:{message.text}") if message.type in {"error", "warning"} else None)
    page.on("pageerror", lambda error: errors.append(f"pageerror:{error}"))
    return errors


def desktop_flow(browser) -> dict[str, object]:
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    errors = capture_console(page)
    page.goto(FRONTEND_URL, wait_until="networkidle")
    page.screenshot(path=ARTIFACTS / "desktop-before.png", full_page=False)
    assert_no_overflow(page)

    def attach_test_context(route) -> None:
        response = route.fetch()
        body = response.json()
        body["ai_contexts"]["career"] = {
            "token": "t" * 64,
            "facts": [
                {"id": "domain-1", "text": "官禄宫位于午"},
                {"id": "domain-2", "text": "该宫主星为紫微"},
            ],
        }
        route.fulfill(status=response.status, content_type="application/json", body=json.dumps(body, ensure_ascii=False))

    page.route("**/v1/charts", attach_test_context)
    fill_birth(page)
    submit_and_wait(page)
    page.screenshot(path=ARTIFACTS / "desktop-result.png", full_page=False)
    assert "日柱" in page.locator("#fortune").inner_text()

    # Second profile via the side panel: multi-user switching.
    page.get_by_role("button", name="新用户").click()
    fill_birth(page, name="妈妈", date="1965-03-08", time="06:10", prov="310000", city="310104")
    submit_and_wait(page, "妈妈")
    assert page.locator(".header-users .user-chip").count() == 2
    page.locator(".header-users .user-pick", has_text="我").first.click()
    page.get_by_text("我的盘已就绪", exact=True).wait_for(timeout=20_000)
    page.locator("#fortune .fortune-reading").wait_for(timeout=20_000)
    assert page.locator('select[aria-label="省份"]').input_value() == "110000"
    assert page.locator('select[aria-label="城市或辖区"]').input_value() == "110101"
    # Third-level cascade on a regular province: 河北 -> 石家庄市 -> 长安区.
    page.locator('select[aria-label="省份"]').select_option("130000")
    page.locator('select[aria-label="城市或辖区"]').select_option("130100")
    page.locator('select[aria-label="区县"]').select_option("130102")
    assert page.locator('input[name="placePreset"]').input_value() == "130102"
    page.locator('select[aria-label="省份"]').select_option("110000")
    page.locator('select[aria-label="城市或辖区"]').select_option("110101")

    page.locator('.primary-nav a[href="#ask"]').click()

    ai_request: dict[str, object] = {}
    page.route("**/v1/ai/status", lambda route: route.fulfill(
        status=200, content_type="application/json",
        body='{"available":true,"mode":"on_demand","attaches_birth_profile":false}',
    ))

    explain_calls: list[dict] = []

    def explain_from_signed_facts(route) -> None:
        body = route.request.post_data_json
        explain_calls.append(body)
        route.fulfill(status=200, content_type="application/json", body=json.dumps({
            "summary": {"text": f"这段结果可以先理解为：把职业推进拆成可验证的小步骤。（第{len(explain_calls)}轮）", "fact_ids": ["domain-1"]},
            "actions": [{"text": "先完成一个可以复查的最小成果。", "fact_ids": ["domain-1", "domain-2"]}],
            "caveats": [{"text": "这不是确定的职业结果。", "fact_ids": ["domain-1"]}],
        }, ensure_ascii=False))

    page.route("**/v1/ai/explain", explain_from_signed_facts)

    # Career domain: AI reading generates automatically (auto mode).
    page.locator(".domain-choices button", has_text="事业").click()
    page.locator(".domain-reading").wait_for()
    page.locator("#analysis .ai-answer").wait_for(timeout=15_000)
    assert "把职业推进拆成可验证的小步骤" in page.locator("#analysis .ai-answer").inner_text()
    ai_request = explain_calls[-1]
    assert set(ai_request) == {"question", "context_tokens"}
    assert ai_request["context_tokens"] == ["t" * 64]
    assert "civil_datetime" not in json.dumps(ai_request)
    assert "longitude" not in json.dumps(ai_request)
    cache = page.evaluate("() => localStorage.getItem('fortune-ai-cache-v1')")
    assert cache and "ai-" in cache
    page.locator("#analysis .ai-explain-panel").screenshot(path=ARTIFACTS / "desktop-ai-explanation.png")

    page.get_by_role("button", name="保存这项分析").click()
    page.locator(".save-toast").wait_for()

    # AI chat tab: multi-turn conversation carries history.
    page.locator(".domain-choices button", has_text="问 AI").click()
    page.locator(".chat-input textarea").fill("我的事业下一步怎么走？")
    page.locator(".chat-input button[type=submit]").click()
    page.locator(".chat-msg.is-assistant").first.wait_for(timeout=15_000)
    page.locator(".chat-input textarea").fill("那感情上呢？")
    page.locator(".chat-input button[type=submit]").click()
    page.locator(".chat-msg.is-assistant").nth(1).wait_for(timeout=15_000)
    chat_calls = [call for call in explain_calls if "感情" in call["question"] or "事业" in call["question"]]
    assert len(chat_calls) == 2 and len(chat_calls[1]["history"]) == 3
    assert chat_calls[1]["history"][0]["role"] == "user"
    assert chat_calls[1]["history"][1]["role"] == "assistant"

    page.locator('.primary-nav a[href="#fortune"]').click()
    page.get_by_role("button", name="明日", exact=True).click()
    page.locator("#fortune .fortune-reading").wait_for(timeout=20_000)
    page.locator("#fortune .ai-answer").wait_for(timeout=15_000)
    page.get_by_role("button", name="保存明日运势").click()
    page.locator(".save-toast").wait_for()

    # Week scope renders the calendar grid; picking a day shows the day card.
    page.get_by_role("button", name="本周", exact=True).click()
    page.locator("#fortune .calendar-grid").wait_for(timeout=20_000)
    page.locator(".calendar-cell:not(.is-blank)").nth(3).click()
    page.wait_for_timeout(400)
    page.locator("#fortune .day-card > header > strong").wait_for(timeout=10_000)
    page.locator("#fortune .day-card .ai-answer").wait_for(timeout=15_000)
    assert "查看依据" in page.locator("#fortune .day-card").inner_text()

    # Cached scope re-renders instantly without another explain call.
    calls_before_cache_check = len(explain_calls)
    page.get_by_role("button", name="明日", exact=True).click()
    page.locator("#fortune .fortune-reading").wait_for(timeout=20_000)
    page.locator("#fortune .ai-answer").wait_for(timeout=5_000)
    print("DEBUG explain questions:", [call["question"][:24] for call in explain_calls], file=sys.stderr)
    assert len(explain_calls) == calls_before_cache_check, f"expected {calls_before_cache_check}, got {len(explain_calls)}"

    # Real status (no provider locally) → fresh scope shows unavailable notice.
    page.unroute("**/v1/ai/status")
    page.unroute("**/v1/ai/explain")
    page.evaluate("() => localStorage.removeItem('fortune-ai-cache-v1')")
    page.get_by_role("button", name="今日", exact=True).click()
    page.locator("#fortune .fortune-reading").wait_for(timeout=20_000)
    page.locator("#fortune .ai-unavailable").wait_for(timeout=10_000)
    assert "AI 讲解暂未配置" in page.locator("#fortune .ai-unavailable").inner_text()

    saved = page.evaluate("() => localStorage.getItem('fortune-saved-readings-v1')")
    assert saved and "civil_datetime" not in saved and "longitude" not in saved
    assert len(json.loads(saved)) == 2
    assert any(item.get("userName") == "我" for item in json.loads(saved))
    users = json.loads(page.evaluate("() => localStorage.getItem('fortune-users-v1')"))
    assert len(users) == 2 and {user["name"] for user in users} == {"我", "妈妈"}

    # Chart view: rename a profile through the manage bar.
    page.locator('.primary-nav a[href="#chart"]').click()
    page.locator(".chart-result").wait_for()
    page.get_by_label("重命名 妈妈").click()
    page.get_by_label("重命名 妈妈").fill("老妈")
    page.get_by_label("重命名 妈妈").press("Enter")
    page.locator(".chart-view .user-pick", has_text="老妈").wait_for()

    page.get_by_role("link", name="我的").click()
    page.get_by_title("切换到GGBond").click()
    page.locator(".theme-wipe").wait_for(state="detached", timeout=5_000)
    assert page.locator(".app-shell").get_attribute("data-theme") == "ggbond"
    page.close()
    return {"console_errors": errors, "saved_items": 2, "users": 2}


def mobile_flow(browser) -> dict[str, object]:
    context = browser.new_context(viewport={"width": 390, "height": 844}, locale="zh-CN")
    page = context.new_page()
    page.on("dialog", lambda dialog: dialog.accept())
    errors = capture_console(page)
    page.goto(FRONTEND_URL, wait_until="networkidle")
    page.evaluate("() => localStorage.clear()")
    page.reload(wait_until="networkidle")
    page.screenshot(path=ARTIFACTS / "mobile-before.png", full_page=False)
    assert_no_overflow(page)
    assert_touch_targets(page)
    nav_position = page.locator(".primary-nav").evaluate("node => getComputedStyle(node).position")
    assert nav_position == "fixed"
    assert page.locator(".primary-nav a").count() == 4

    fill_birth(page, "小明", "310000", "310104")
    submit_and_wait(page, "小明")
    page.screenshot(path=ARTIFACTS / "mobile-result.png", full_page=False)
    assert_no_overflow(page)
    assert_touch_targets(page)
    page.locator("#fortune .fortune-reading").wait_for(timeout=20_000)

    partial_error_index = len(errors)

    def fail_window(route) -> None:
        route.fulfill(status=503, content_type="application/json", body='{"detail":"测试用时间层繁忙"}')

    page.route("**/v1/transits/daily", fail_window, times=1)
    page.get_by_role("button", name="明日", exact=True).click()
    page.locator("#fortune .fortune-error").wait_for(timeout=20_000)
    assert "测试用时间层繁忙" in page.locator("#fortune .fortune-error").inner_text()
    page.screenshot(path=ARTIFACTS / "mobile-fortune-error.png", full_page=False)
    del errors[partial_error_index:]
    page.get_by_role("button", name="今日", exact=True).click()
    page.locator("#fortune .fortune-reading").wait_for(timeout=20_000)

    page.locator('.primary-nav a[href="#ask"]').click()
    page.locator(".domain-choices button", has_text="事业").click()
    page.locator("#analysis .ai-unavailable").wait_for(timeout=10_000)
    assert_no_overflow(page)
    assert_touch_targets(page)
    page.screenshot(path=ARTIFACTS / "mobile-ai-unavailable.png", full_page=False)

    # Delete the only profile, then retry a chart through the fresh empty state.
    expected_error_index = len(errors)

    def fail_chart(route) -> None:
        route.fulfill(status=503, content_type="application/json", body='{"detail":"测试用服务繁忙"}')

    page.route("**/v1/charts", fail_chart, times=1)
    page.locator('.primary-nav a[href="#chart"]').click()
    page.get_by_label("删除 小明").click()
    page.locator(".task-gate").first.wait_for(timeout=5_000)
    page.locator('.primary-nav a[href="#fortune"]').click()
    page.locator("#birth-form").wait_for()
    fill_birth(page)
    page.get_by_role("button", name="排盘并看运势").click()
    page.locator("#birth-form-error").wait_for()
    assert "测试用服务繁忙" in page.locator("#birth-form-error").inner_text()
    del errors[expected_error_index:]

    page.set_viewport_size({"width": 375, "height": 812})
    page.reload(wait_until="networkidle")
    assert_no_overflow(page)
    assert_touch_targets(page)
    page.screenshot(path=ARTIFACTS / "mobile-375.png", full_page=False)
    context.close()
    return {"console_errors": errors, "error_state": True, "small_viewport": 375}


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            result = {"desktop": desktop_flow(browser), "mobile": mobile_flow(browser)}
        finally:
            browser.close()
    all_errors = result["desktop"]["console_errors"] + result["mobile"]["console_errors"]
    if all_errors:
        raise AssertionError(all_errors)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"E2E_FAILED: {error}", file=sys.stderr)
        raise
