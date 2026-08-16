"""Live verification: progress continuity, mobile pills, retry, glass render."""

from playwright.sync_api import sync_playwright

URL = "https://sol-d2ga5fpq8bcf67f5a-1410845958.tcloudbaseapp.com/"
OUT = "tests/.artifacts/round5"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    pg.goto(URL, wait_until="networkidle")
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="networkidle")
    pg.locator('input[name="displayName"]').fill("我")
    pg.locator('select[aria-label="出生年"]').select_option("2000")
    pg.locator('select[aria-label="出生月"]').select_option("1")
    pg.locator('select[aria-label="出生日"]').select_option("1")
    pg.locator('select[aria-label="出生时（24 小时制）"]').select_option("8")
    pg.locator('select[aria-label="出生分"]').select_option("30")
    pg.get_by_role("button", name="排盘并看运势").click()
    pg.locator("#chart .pillars-board").wait_for(timeout=60000)
    pg.locator('.primary-nav a[href="#fortune"]').click()
    pg.locator("#fortune .fortune-reading").wait_for(timeout=30000)
    pg.wait_for_timeout(4000)
    pct1 = pg.locator("#fortune .ai-progress > span").inner_text() if pg.locator("#fortune .ai-progress").count() else "(none)"
    # switch away mid-generation, come back: progress must not restart from 0
    pg.locator('.primary-nav a[href="#ask"]').click()
    pg.wait_for_timeout(2500)
    pg.locator('.primary-nav a[href="#fortune"]').click()
    pg.locator("#fortune .fortune-reading").wait_for(timeout=20000)
    pg.wait_for_timeout(800)
    pct2 = pg.locator("#fortune .ai-progress > span").inner_text() if pg.locator("#fortune .ai-progress").count() else "(done)"
    print("1. progress before leave:", pct1, "| after return:", pct2)
    pg.locator("#fortune .ai-answer").wait_for(timeout=30000)
    print("1b. answer landed:", pg.locator("#fortune .ai-answer p").first.inner_text()[:40])
    # desktop pills left edge
    tb = pg.locator("#fortune .fortune-toolbar").bounding_box()
    print("2. desktop toolbar x:", tb["x"])
    # glass visuals: backdrop-filter present on console card
    glass = pg.evaluate("() => { const el = document.querySelector('.fortune-console'); return getComputedStyle(el).backdropFilter }")
    print("4. console backdrop-filter:", glass)
    pg.screenshot(path=f"{OUT}/fortune-glass.png")

    # mobile pill grid
    pg.set_viewport_size({"width": 390, "height": 844})
    pg.reload(wait_until="networkidle")
    pg.locator('.primary-nav a[href="#fortune"]').click()
    pg.locator("#fortune .fortune-reading, #fortune .calendar-grid").first.wait_for(timeout=30000)
    pills = pg.evaluate("""() => [...document.querySelectorAll('.fortune-scopes button')].map(b => {
      const r = b.getBoundingClientRect()
      return {t: b.textContent.trim(), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width)}
    })""")
    print("2b. mobile pills:", pills)
    pg.screenshot(path=f"{OUT}/mobile-pills.png")

    # retry: ask view domain reading on live (real provider) works
    pg.set_viewport_size({"width": 1440, "height": 1000})
    pg.locator('.primary-nav a[href="#ask"]').click()
    pg.locator('.domain-choices button', has_text="事业").first.click()
    pg.locator("#analysis .ai-answer").wait_for(timeout=55000)
    print("3. career AI ok on live")
    b.close()
print("ALL DONE")
