"""Diagnose chart-page alignment and glass visuals."""

from playwright.sync_api import sync_playwright

URL = "https://sol-d2ga5fpq8bcf67f5a-1410845958.tcloudbaseapp.com/"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
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
    pg.wait_for_timeout(600)
    pg.screenshot(path="tests/.artifacts/misalign/chart-now.png", full_page=True)

    # four-pillar board: per-row cell x-centers must align across rows
    board = pg.evaluate("""() => {
      const rows = [...document.querySelectorAll('.pillars-board .board-row')]
      return rows.map(row => {
        const cells = [...row.children].slice(1)
        return {
          label: row.querySelector('.row-label')?.textContent,
          centers: cells.map(c => Math.round(c.getBoundingClientRect().x + c.getBoundingClientRect().width / 2)),
          widths: cells.map(c => Math.round(c.getBoundingClientRect().width)),
        }
      })
    }""")
    print("board rows:")
    for r in board:
        print(" ", r["label"], "centers:", r["centers"], "widths:", r["widths"])

    dayun = pg.evaluate("""() => [...document.querySelectorAll('.dayun-cell')].map(c => ({
      gz: c.querySelector('b')?.textContent, x: Math.round(c.getBoundingClientRect().x), w: Math.round(c.getBoundingClientRect().width)
    }))""")
    print("dayun cells:", dayun[:4])

    summary = pg.evaluate("""() => [...document.querySelectorAll('.result-summary .result-fact')].map(f => ({
      x: Math.round(f.getBoundingClientRect().x), w: Math.round(f.getBoundingClientRect().width)
    }))""")
    print("summary cards:", summary)

    # glass computed values
    glass = pg.evaluate("""() => {
      const pick = (sel) => {
        const el = document.querySelector(sel)
        if (!el) return null
        const cs = getComputedStyle(el)
        return { bg: cs.background.slice(0, 80), bf: cs.backdropFilter, shadow: cs.boxShadow.slice(0, 90), radius: cs.borderRadius }
      }
      return {
        chart: pick('.chart-result'),
        console: pick('.fortune-console') || null,
        shellBg: getComputedStyle(document.querySelector('.app-shell')).backgroundImage.slice(0, 120),
      }
    }""")
    print("glass:", glass)
    b.close()
print("done")
