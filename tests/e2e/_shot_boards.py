"""临时：截三盘布局（桌面 + 390px 手机），验证盘一/二/三标注与七政盘面。"""

from playwright.sync_api import sync_playwright

FRONTEND = "http://127.0.0.1:5173"


def flow(page):
    page.goto(FRONTEND, wait_until="networkidle")
    page.evaluate("() => localStorage.clear()")
    page.reload(wait_until="networkidle")
    page.locator('#chart .task-gate a[href="#fortune"]').click()
    page.locator("#birth-form").wait_for(timeout=10_000)
    page.locator('input[name="displayName"]').fill("我")
    page.locator('select[aria-label="出生年"]').select_option("2000")
    page.locator('select[aria-label="出生月"]').select_option("1")
    page.locator('select[aria-label="出生日"]').select_option("1")
    page.locator('select[aria-label="出生时（24 小时制）"]').select_option("8")
    page.locator('select[aria-label="出生分"]').select_option("30")
    page.get_by_role("button", name="排盘并看运势").click()
    page.locator("#chart .pillars-board").wait_for(timeout=30_000)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    desktop = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    flow(desktop)
    boards = desktop.locator(".qizheng-board")
    boards.wait_for(timeout=10_000)
    print("盘一 kicker:", desktop.locator(".board-kicker span").inner_text())
    print("盘二 kicker:", desktop.locator(".ziwei-section:not(.qizheng-board) .section-kicker span").inner_text())
    print("盘三 kicker:", boards.locator(".section-kicker span").inner_text())
    print("七政宫格数:", boards.locator(".palace-grid article").count())
    print("命宫格:", boards.locator("article", has_text="命宫").count())
    star_chips = boards.locator(".star-chip:not(.is-empty)")
    print("星标总数:", star_chips.count(), "（应为 11）")
    print("逆行标:", boards.locator(".star-chip b").count())
    boards.locator(".qz-details > summary").click()
    boards.screenshot(path="tests/.artifacts/audit/qz_board_desktop.png")

    mobile = browser.new_page(viewport={"width": 390, "height": 844}, locale="zh-CN", device_scale_factor=2)
    flow(mobile)
    mboards = mobile.locator(".qizheng-board")
    mboards.wait_for(timeout=10_000)
    mboards.scroll_into_view_if_needed()
    mboards.locator(".qz-details > summary").click()
    mboards.screenshot(path="tests/.artifacts/audit/qz_board_390.png")
    overflow = mobile.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
    print("手机横向溢出(px):", overflow)
    browser.close()
