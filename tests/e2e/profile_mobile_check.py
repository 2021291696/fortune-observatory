"""Verify profile page mobile layout on the deployed site: theme buttons 5-col row + motion-toggle pill."""

import json

from playwright.sync_api import sync_playwright

URL = "https://sol-d2ga5fpq8bcf67f5a-1410845958.tcloudbaseapp.com/#profile"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 390, "height": 844}, locale="zh-CN", is_mobile=True, has_touch=True)
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(800)
    pg.screenshot(path="tests/.artifacts/profile-mobile-live.png", full_page=False)

    geo = pg.evaluate("""() => {
      const out = {}
      const btns = [...document.querySelectorAll('.remote-options button')]
      out.themeButtons = btns.map(e => {
        const r = e.getBoundingClientRect()
        return {label: (e.textContent || '').trim().slice(0, 12), x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}
      })
      out.themeCount = btns.length
      const mt = document.querySelector('.motion-toggle')
      if (mt) {
        const r = mt.getBoundingClientRect()
        const cs = getComputedStyle(mt)
        out.motionToggle = {text: mt.textContent.trim(), w: Math.round(r.width), h: Math.round(r.height), radius: cs.borderRadius}
      }
      const smallTargets = [...document.querySelectorAll('.remote-options button, .motion-toggle')]
        .map(e => e.getBoundingClientRect())
        .filter(r => r.width > 0 && (r.width < 44 || r.height < 44))
      out.touchTargetsUnder44 = smallTargets.length
      const vw = document.documentElement.clientWidth
      out.viewport = vw
      out.overflow = (() => {
        const bad = []
        for (const el of document.querySelectorAll('body *')) {
          const r = el.getBoundingClientRect()
          if (r.width === 0 || r.height === 0) continue
          if (r.right > vw + 2 && r.width < vw) { bad.push(el.tagName + '.' + (el.className || '').toString().split(' ')[0]); if (bad.length > 8) break }
        }
        return bad
      })()
      return out
    }""")
    print(json.dumps(geo, ensure_ascii=False, indent=2))

    # 5 distinct rows? check y positions
    ys = sorted(set(g["y"] for g in geo["themeButtons"]))
    print(f"\ntheme button rows (y positions): {ys}")
    print(f"distinct rows: {len(ys)}")
    if geo["themeButtons"]:
        widths = sorted(set(g["w"] for g in geo["themeButtons"]))
        print(f"widths: {widths}")
    b.close()
