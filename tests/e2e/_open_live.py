"""打开线上站点给用户看：预置一个用户，直达命盘页并展开七政四余区，保持浏览器窗口。"""

import json
import time

from playwright.sync_api import sync_playwright

URL = "https://sol-d2ga5fpq8bcf67f5a-1410845958.tcloudbaseapp.com/"

USER = {
    "id": "demo-1995",
    "name": "演示",
    "createdAt": "2026-08-16T10:00:00.000Z",
    "placeAdcode": "110105",
    "birth": {
        "civil_datetime": "1995-08-16T12:00:00+08:00",
        "timezone_id": "Asia/Shanghai",
        "longitude": 116.4074,
        "latitude": 39.9042,
        "sex_for_rule": "male",
        "use_apparent_solar_time": True,
    },
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1280, "height": 900}, locale="zh-CN")
    page.goto(URL, wait_until="networkidle")
    page.evaluate(
        "(user) => { localStorage.setItem('fortune-users-v1', JSON.stringify([user]));"
        " localStorage.setItem('fortune-current-user-v1', JSON.stringify(user)); }",
        USER,
    )
    page.goto(URL + "#chart", wait_until="networkidle")
    page.reload(wait_until="networkidle")
    page.locator("#chart .pillars-board").wait_for(timeout=30_000)
    board = page.locator(".qizheng-board")
    board.wait_for(timeout=15_000)
    board.locator(".qz-details > summary").first.click()
    board.scroll_into_view_if_needed()
    page.wait_for_timeout(600)
    board.screenshot(path="tests/.artifacts/audit/qz_live_board.png")
    print("READY: 七政区已展开，窗口保持打开（关掉浏览器窗口即可）")
    try:
        for _ in range(360):  # 保持窗口 ~30 分钟
            time.sleep(5)
            page.title()
    except Exception:
        pass
    browser.close()
