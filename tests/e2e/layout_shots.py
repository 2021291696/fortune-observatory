"""Capture live-site screenshots of the four-page IA for layout review."""

from playwright.sync_api import sync_playwright

URL = "https://sol-d2ga5fpq8bcf67f5a-1410845958.tcloudbaseapp.com/"
OUT = "tests/.artifacts/layout-v3"


def shoot(page, name, full=True):
    page.wait_for_timeout(900)
    page.screenshot(path=f"{OUT}/{name}.png", full_page=full)
    print("shot", name)


def fill(page, name, city="beijing", date="2000-01-01"):
    province = {"beijing": "北京", "shanghai": "上海"}[city]
    page.locator('input[name="displayName"]').fill(name)
    page.locator('input[name="civilDate"]').fill(date)
    page.locator('input[name="civilTime"]').fill("08:30")
    page.locator('select[name="province"]').select_option(province)
    page.locator('select[name="placePreset"]').select_option(city)


def submit(page, name):
    page.get_by_role("button", name="排盘并看运势").click()
    page.locator("#fortune .fortune-reading").wait_for(timeout=60_000)
    page.get_by_text(f"{name}的盘已就绪", exact=True).wait_for(timeout=60_000)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    page.goto(URL, wait_until="networkidle")
    page.evaluate("() => localStorage.clear()")
    page.reload(wait_until="networkidle")
    shoot(page, "desktop-fortune-empty")
    fill(page, "我")
    submit(page, "我")
    page.wait_for_timeout(1500)
    shoot(page, "desktop-fortune-today")
    page.get_by_role("button", name="新用户").click()
    fill(page, "妈妈", "shanghai", "1965-03-08")
    submit(page, "妈妈")
    shoot(page, "desktop-fortune-mama")
    page.locator(".header-users .user-pick", has_text="我").first.click()
    page.get_by_text("我的盘已就绪", exact=True).wait_for(timeout=60_000)
    page.locator('.primary-nav a[href="#ask"]').click(); shoot(page, "desktop-ask")
    page.locator(".domain-choices button", has_text="事业").click()
    page.locator(".domain-reading").wait_for(); shoot(page, "desktop-ask-career")
    page.locator('.primary-nav a[href="#chart"]').click()
    page.locator(".chart-result").wait_for(); shoot(page, "desktop-chart")
    page.locator('.primary-nav a[href="#profile"]').click(); shoot(page, "desktop-profile")
    browser.close()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844}, locale="zh-CN")
    page.goto(URL, wait_until="networkidle")
    page.evaluate("() => localStorage.clear()")
    page.reload(wait_until="networkidle")
    fill(page, "我")
    submit(page, "我")
    shoot(page, "mobile-fortune")
    page.locator('.primary-nav a[href="#ask"]').click(); shoot(page, "mobile-ask")
    browser.close()
print("done")
