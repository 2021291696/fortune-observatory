"""Capture current live-site screenshots for layout review."""

from playwright.sync_api import sync_playwright

URL = "https://sol-d2ga5fpq8bcf67f5a-1410845958.tcloudbaseapp.com/"
OUT = "tests/.artifacts/layout"


def shoot(page, name, full=True):
    page.wait_for_timeout(900)
    page.screenshot(path=f"{OUT}/{name}.png", full_page=full)
    print("shot", name)


def fill_and_submit(page):
    page.goto(URL, wait_until="networkidle")
    page.wait_for_timeout(2000)
    page.locator('input[name="civilDate"]').fill("2000-01-01")
    page.locator('input[name="civilTime"]').fill("08:30")
    page.locator('select[name="placePreset"]').select_option("beijing")
    page.get_by_role("button", name="查看今天重点").click()
    page.locator("#today-brief .daily-card").first.wait_for(timeout=60_000)


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    fill_and_submit(page)
    shoot(page, "desktop-today-ready")
    page.locator('.primary-nav a[href="#ask"]').click(); shoot(page, "desktop-ask")
    page.locator(".domain-choices button", has_text="事业").click()
    page.locator(".domain-reading").wait_for(); shoot(page, "desktop-ask-career")
    page.locator('.primary-nav a[href="#chart"]').click()
    page.locator(".chart-result").wait_for(); shoot(page, "desktop-chart")
    page.locator('.primary-nav a[href="#profile"]').click(); shoot(page, "desktop-profile")
    page.goto(URL, wait_until="networkidle"); shoot(page, "desktop-today-empty")
    browser.close()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 390, "height": 844}, locale="zh-CN")
    fill_and_submit(page)
    shoot(page, "mobile-today")
    page.locator('.primary-nav a[href="#ask"]').click(); shoot(page, "mobile-ask")
    browser.close()
print("done")
