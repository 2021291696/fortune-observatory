"""DOM geometry audit: find elements overflowing their card / viewport."""

import json
from playwright.sync_api import sync_playwright

URL = "https://sol-d2ga5fpq8bcf67f5a-1410845958.tcloudbaseapp.com/"

AUDIT_JS = """() => {
  const issues = []
  const vw = document.documentElement.clientWidth
  const cards = document.querySelectorAll('.fortune-console, .domain-console, .chart-result, .day-card, .launch-section, .birth-form')
  for (const card of cards) {
    const cr = card.getBoundingClientRect()
    const label = (card.querySelector('h1,h2,h3,summary')?.textContent || card.className).trim().slice(0, 30)
    if (cr.right > vw + 1 || cr.left < -1) issues.push(`card ${card.className.split(' ')[0]}(${label}) spans viewport: L${Math.round(cr.left)} R${Math.round(cr.right)} vw${vw}`)
    // children escaping card horizontally (beyond 2px tolerance)
    for (const child of card.querySelectorAll('*')) {
      const r = child.getBoundingClientRect()
      if (r.width === 0 || r.height === 0) continue
      if (r.right > cr.right + 3 && r.width < vw) {
        issues.push(`overflow-right in ${card.className.split(' ')[0]}: <${child.tagName.toLowerCase()} ${child.className && typeof child.className === 'string' ? child.className.split(' ')[0] : ''}> "${(child.textContent||'').trim().slice(0,18)}" childR${Math.round(r.right)} > cardR${Math.round(cr.right)}`)
        if (issues.length > 40) return issues
      }
      if (r.left < cr.left - 3 && r.width < vw) {
        issues.push(`overflow-left in ${card.className.split(' ')[0]}: <${child.tagName.toLowerCase()}> "${(child.textContent||'').trim().slice(0,18)}" childL${Math.round(r.left)} < cardL${Math.round(cr.left)}`)
        if (issues.length > 40) return issues
      }
    }
  }
  // horizontal page overflow
  if (document.documentElement.scrollWidth > vw + 1) issues.push(`page h-scroll: ${document.documentElement.scrollWidth} > ${vw}`)
  // fortune side-by-side columns top alignment
  const res = document.querySelector('.today-results')
  const side = document.querySelector('.today-view.is-ready .launch-section')
  if (res && side) {
    const rr = res.getBoundingClientRect(), sr = side.getBoundingClientRect()
    issues.push(`columns: resultsTop=${Math.round(rr.top)} sideTop=${Math.round(sr.top)} resultsH=${Math.round(rr.height)} sideH=${Math.round(sr.height)} sideL=${Math.round(sr.left)} sideR=${Math.round(sr.right)}`)
  }
  // LiquidGlass form bounds vs container
  const lg = side ? side.querySelector('.launch-copy') : null
  if (lg) {
    const lr = lg.getBoundingClientRect()
    issues.push(`launch-copy: L${Math.round(lr.left)} R${Math.round(lr.right)} T${Math.round(lr.top)} H${Math.round(lr.height)} | section L${Math.round(side.getBoundingClientRect().left)} R${Math.round(side.getBoundingClientRect().right)}`)
  }
  return issues
}"""


def run(pg, width, height, tag):
    pg.set_viewport_size({"width": width, "height": height})
    # Fresh visitors land on the chart view (no saved users) — the birth form lives on #fortune.
    pg.goto(URL + "#fortune", wait_until="networkidle")
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
    print(f"--- {tag} chart ---")
    for line in pg.evaluate(AUDIT_JS):
        print(" ", line)
    pg.locator('.primary-nav a[href="#fortune"]').click()
    pg.locator("#fortune .fortune-reading").wait_for(timeout=30000)
    pg.wait_for_timeout(400)
    print(f"--- {tag} fortune ---")
    for line in pg.evaluate(AUDIT_JS):
        print(" ", line)
    pg.locator('.primary-nav a[href="#ask"]').click()
    pg.wait_for_timeout(400)
    print(f"--- {tag} ask ---")
    for line in pg.evaluate(AUDIT_JS):
        print(" ", line)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    run(pg, 1440, 1000, "desktop1440")
    run(pg, 390, 844, "mobile390")
    b.close()
print("GEOM AUDIT DONE")
