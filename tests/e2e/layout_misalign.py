"""Capture all views desktop+mobile to diagnose layout misalignment."""

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:5173/"
OUT = "tests/.artifacts/misalign"


def setup(pg, width, height):
    pg.set_viewport_size({"width": width, "height": height})
    pg.goto(URL, wait_until="networkidle")
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="networkidle")
    pg.route("**/v1/ai/status", lambda r: r.fulfill(status=200, content_type="application/json", body='{"available":false}'))
    pg.locator('input[name="displayName"]').fill("我")
    pg.locator('select[aria-label="出生年"]').select_option("2000")
    pg.locator('select[aria-label="出生月"]').select_option("1")
    pg.locator('select[aria-label="出生日"]').select_option("1")
    pg.locator('select[aria-label="出生时（24 小时制）"]').select_option("8")
    pg.locator('select[aria-label="出生分"]').select_option("30")
    pg.get_by_role("button", name="排盘并看运势").click()
    pg.locator("#chart .pillars-board").wait_for(timeout=60000)
    pg.wait_for_timeout(500)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    setup(pg, 1440, 1000)
    pg.screenshot(path=f"{OUT}/d1-chart.png", full_page=True)
    pg.locator('.primary-nav a[href="#fortune"]').click()
    pg.locator("#fortune .fortune-reading").wait_for(timeout=30000)
    pg.wait_for_timeout(400)
    pg.screenshot(path=f"{OUT}/d2-fortune.png", full_page=True)
    pg.get_by_role("button", name="本周", exact=True).click()
    pg.locator("#fortune .calendar-grid").wait_for(timeout=30000)
    pg.screenshot(path=f"{OUT}/d3-week.png", full_page=True)
    pg.locator('.primary-nav a[href="#ask"]').click()
    pg.wait_for_timeout(400)
    pg.screenshot(path=f"{OUT}/d4-ask.png", full_page=True)
    pg.locator('.domain-choices button', has_text="事业").first.click()
    pg.wait_for_timeout(400)
    pg.screenshot(path=f"{OUT}/d5-career.png", full_page=True)
    pg.locator('.primary-nav a[href="#profile"]').click()
    pg.wait_for_timeout(400)
    pg.screenshot(path=f"{OUT}/d6-profile.png", full_page=True)

    setup(pg, 390, 844)
    pg.screenshot(path=f"{OUT}/m1-chart.png", full_page=True)
    pg.locator('.primary-nav a[href="#fortune"]').click()
    pg.locator("#fortune .fortune-reading").wait_for(timeout=30000)
    pg.wait_for_timeout(400)
    pg.screenshot(path=f"{OUT}/m2-fortune.png", full_page=True)
    pg.locator('.primary-nav a[href="#ask"]').click()
    pg.wait_for_timeout(400)
    pg.screenshot(path=f"{OUT}/m3-ask.png", full_page=True)
    b.close()
print("done")
