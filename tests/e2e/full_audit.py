"""QA full-flow audit: exercise every panel, catch regressions."""

import json
import sys
from playwright.sync_api import sync_playwright

FRONTEND = "http://127.0.0.1:5173"
OUT = "tests/.artifacts/audit"
PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    (PASSED if condition else FAILED).append(f"{name}{(' :: ' + detail) if detail and not condition else ''}")
    print(("PASS " if condition else "FAIL ") + name + (f"  [{detail}]" if detail and not condition else ""))


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
        errors: list[str] = []
        page.on("console", lambda m: errors.append(m.text[:160]) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)[:160]))

        # Mock AI with a 1.5s delay to emulate real latency and exercise the
        # progress bar + background cache paths.
        def slow_explain(route):
            def _deliver():
                route.fulfill(status=200, content_type="application/json", body=json.dumps({
                    "summary": {"text": f"深度解读：{route.request.post_data_json['question'][:12]}……可以先把大事拆小。", "fact_ids": ["daily-1"]},
                    "actions": [{"text": "先做一件小事。", "fact_ids": ["daily-1"]}],
                    "caveats": [{"text": "仅供参考。", "fact_ids": ["daily-1"]}],
                }, ensure_ascii=False))
            page.wait_for_timeout(1500)
            _deliver()

        page.route("**/v1/ai/status", lambda r: r.fulfill(status=200, content_type="application/json", body='{"available":true,"mode":"on_demand","attaches_birth_profile":false}'))
        page.route("**/v1/ai/explain", slow_explain)

        page.goto(FRONTEND, wait_until="networkidle")
        page.evaluate("() => localStorage.clear()")
        page.reload(wait_until="networkidle")

        # 1. submit -> chart board
        page.locator('input[name="displayName"]').fill("我")
        page.locator('input[name="civilDate"]').fill("2000-01-01")
        page.locator('input[name="civilTime"]').fill("08:30")
        page.get_by_role("button", name="排盘并看运势").click()
        page.locator("#chart .pillars-board").wait_for(timeout=30_000)
        board = page.locator(".pillars-board").inner_text()
        check("命盘.四柱含十神藏干纳音", all(k in board for k in ["十神", "天干", "地支", "藏干", "纳音"]))
        check("命盘.大运虚岁", "9岁" in page.locator(".dayun-strip").inner_text())
        page.locator(".chart-full-details > summary").click()
        check("命盘.折叠展开十二宫", page.locator(".palace-grid article").count() >= 12)

        # 2. fortune: today auto AI with progress, then leave and come back
        page.locator('.primary-nav a[href="#fortune"]').click()
        page.locator("#fortune .fortune-reading").wait_for(timeout=30_000)
        check("运势.流日文案", "流日" in page.locator("#fortune .fortune-reading header h3").inner_text())
        check("运势.进度条出现", page.locator("#fortune .ai-progress").count() == 1)
        page.locator('.primary-nav a[href="#ask"]').click()  # leave mid-generation
        page.wait_for_timeout(3500)  # generation finishes in background
        page.locator('.primary-nav a[href="#fortune"]').click()
        page.locator("#fortune .fortune-reading").wait_for(timeout=20_000)
        check("运势.后台生成缓存命中", page.locator("#fortune .ai-answer").count() == 1)
        page.locator("#fortune .fact-details summary").click()
        check("运势.查看依据展开", page.locator("#fortune .fact-details p").first.is_visible())

        # save today, switch tomorrow, verify separate cache key
        page.get_by_role("button", name="保存今日运势").click()
        page.locator(".save-toast").wait_for()
        page.get_by_role("button", name="明日", exact=True).click()
        page.locator("#fortune .fortune-reading").wait_for(timeout=20_000)
        page.locator("#fortune .ai-answer").wait_for(timeout=15_000)
        check("运势.明日AI生成", page.locator("#fortune .ai-answer").count() == 1)

        # 3. week calendar interactions
        page.get_by_role("button", name="本周", exact=True).click()
        page.locator("#fortune .calendar-grid").wait_for(timeout=20_000)
        cells = page.locator("#fortune .calendar-cell:not(.is-blank)")
        check("运势.本周7格", cells.count() == 7, f"got {cells.count()}")
        cells.first.click()
        page.locator("#fortune .day-card .ai-answer").wait_for(timeout=15_000)
        first_day = page.locator("#fortune .day-card > header > strong").inner_text()
        cells.last.click()
        page.wait_for_timeout(2500)
        last_day = page.locator("#fortune .day-card > header > strong").inner_text()
        check("运势.日历切日联动", first_day != last_day, f"{first_day} vs {last_day}")

        # month view renders with weekday header
        page.get_by_role("button", name="本月", exact=True).click()
        page.locator("#fortune .calendar-reading header h3", has_text="本月日历").wait_for(timeout=20_000)
        check("运势.月视图周标题", page.locator(".calendar-weekday").count() == 7)
        check("运势.月视图多于20天", page.locator("#fortune .calendar-cell:not(.is-blank)").count() >= 28)
        page.get_by_role("button", name="下月", exact=True).click()
        page.locator("#fortune .calendar-reading header h3", has_text="下月日历").wait_for(timeout=20_000)
        check("运势.下月可切换", page.locator("#fortune .calendar-cell:not(.is-blank)").count() >= 28)

        # 4. ask: all four domains with independent cache, follow-up question
        page.locator('.primary-nav a[href="#ask"]').click()
        for label in ["健康", "姻缘", "事业", "财运"]:
            page.locator(".domain-choices button", has_text=label).first.click()
            page.locator("#analysis .ai-answer").wait_for(timeout=15_000)
        check("问事.四板块AI全部生成", True)
        page.locator(".domain-choices button", has_text="事业").first.click()
        page.wait_for_timeout(600)
        check("问事.板块缓存复用秒显", page.locator("#analysis .ai-answer").count() == 1)
        page.get_by_role("button", name="换个问题追问 AI").click()
        page.locator("#analysis .ai-question textarea").fill("追问：我最该避免什么？")
        page.get_by_role("button", name="按新问题重新生成").click()
        page.wait_for_timeout(3000)
        check("问事.追问生成新答案", "追问" in page.locator("#analysis .ai-answer p").first.inner_text())

        # 5. chat with progress + two turns
        page.locator(".domain-choices button", has_text="问 AI").click()
        check("问事.聊天快捷问题", page.locator(".chat-quick button").count() == 3)
        page.locator(".chat-quick button").first.click()
        page.locator(".chat-msg.is-assistant").first.wait_for(timeout=15_000)
        page.locator('.chat-input textarea').fill("再说说财运")
        page.locator('.chat-input button[type=submit]').click()
        page.locator(".chat-msg.is-assistant").nth(1).wait_for(timeout=15_000)
        check("问事.聊天多轮", page.locator(".chat-msg.is-user").count() == 2)

        # 6. profile: saved items per user, theme, privacy copy
        page.get_by_role("link", name="我的").click()
        saved_text = page.locator("#saved").inner_text()
        check("我的.收藏含运势与专项", "运势" in saved_text and "我 ·" in saved_text)
        page.get_by_title("切换到GGBond").click()
        page.locator(".theme-wipe").wait_for(state="detached", timeout=5_000)
        check("我的.主题切换", page.locator(".app-shell").get_attribute("data-theme") == "ggbond")

        # 7. second user isolation
        page.locator('.primary-nav a[href="#fortune"]').click()
        page.get_by_role("button", name="新用户").click()
        page.locator('input[name="displayName"]').fill("妈妈")
        page.locator('input[name="civilDate"]').fill("1965-03-08")
        page.locator('input[name="civilTime"]').fill("06:10")
        page.locator('select[aria-label="省份"]').select_option("310000")
        page.locator('select[aria-label="城市或辖区"]').select_option("310104")
        page.get_by_role("button", name="排盘并看运势").click()
        page.locator("#chart .pillars-board").wait_for(timeout=30_000)
        check("多用户.妈妈盘四柱", page.locator("#chart .pillars-board").inner_text() != board)
        page.locator('.primary-nav a[href="#fortune"]').click()
        page.locator("#fortune .fortune-reading").wait_for(timeout=20_000)
        page.locator("#fortune .ai-progress").wait_for(timeout=10_000)
        check("多用户.AI缓存隔离(妈妈重新生成)", page.locator("#fortune .ai-progress").count() == 1)
        page.locator("#fortune .ai-answer").wait_for(timeout=15_000)
        check("多用户.妈妈AI生成", True)

        # console errors across the whole run
        check("全站.零console错误", len(errors) == 0, "; ".join(errors[:3]))

        browser.close()

    print(f"\n===== {len(PASSED)} passed, {len(FAILED)} failed =====")
    if FAILED:
        for item in FAILED:
            print("FAILED:", item)
        sys.exit(1)


if __name__ == "__main__":
    main()
