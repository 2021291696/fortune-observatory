"""Diagnose mobile form element geometry (misalignment report)."""

import json

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:5173/"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 390, "height": 844}, locale="zh-CN", is_mobile=True, has_touch=True)
    pg.goto(URL, wait_until="networkidle")
    pg.route("**/v1/ai/status", lambda r: r.fulfill(status=200, content_type="application/json", body='{"available":false}'))
    pg.evaluate("() => localStorage.clear()")
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(600)
    pg.locator('.primary-nav a[href="#fortune"]').click()
    pg.wait_for_timeout(400)
    pg.screenshot(path="tests/.artifacts/misalign/m-form-empty.png", full_page=True)
    geo = pg.evaluate("""() => {
      const out = {}
      out.sexButtons = [...document.querySelectorAll('.sex-options span')].map(e => {
        const r = e.getBoundingClientRect()
        return {t: e.textContent.trim(), w: Math.round(r.width), h: Math.round(r.height)}
      })
      const pin = document.querySelector('.select-wrap > svg')
      const prov = document.querySelector('select[aria-label="省份"]')
      const wrap = document.querySelector('.select-wrap')
      if (pin && prov && wrap) {
        const pr = pin.getBoundingClientRect()
        const vr = prov.getBoundingClientRect()
        const wr = wrap.getBoundingClientRect()
        out.mapPin = {x: Math.round(pr.x), y: Math.round(pr.y), w: Math.round(pr.width), h: Math.round(pr.height)}
        out.provSelect = {x: Math.round(vr.x), y: Math.round(vr.y), w: Math.round(vr.width), h: Math.round(vr.height), padLeft: getComputedStyle(prov).paddingLeft}
        out.wrap = {x: Math.round(wr.x), y: Math.round(wr.y), w: Math.round(wr.width), h: Math.round(wr.height)}
        out.pinVCenter = Math.round(pr.y + pr.height / 2)
        out.provVCenter = Math.round(vr.y + vr.height / 2)
      }
      return out
    }""")
    print(json.dumps(geo, ensure_ascii=False, indent=1))
    # zoom on the birth-place row
    place = pg.locator(".place-field")
    if place.count():
        place.screenshot(path="tests/.artifacts/misalign/m-place-row.png")
        print("place-row shot saved")
    b.close()
print("done")
