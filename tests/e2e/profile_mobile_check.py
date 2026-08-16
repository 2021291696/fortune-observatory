"""Verify profile page mobile layout on the deployed site: theme 2x2 preview cards + shuffle wide strip + motion-toggle pill.

Usage: uv run --project apps/observatory python tests/e2e/profile_mobile_check.py [url]
Default url = deployed site.
"""

import json
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://sol-d2ga5fpq8bcf67f5a-1410845958.tcloudbaseapp.com/#profile"

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
        const hero = e.querySelector('.theme-card-hero')
        const stickers = [...e.querySelectorAll('.theme-card-sticker')].map(s => Math.round(s.getBoundingClientRect().width))
        return {
          label: (e.textContent || '').trim().slice(0, 12),
          palette: e.getAttribute('data-palette'),
          isShuffle: e.className.includes('theme-card-shuffle'),
          x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
          heroVisible: hero ? Math.round(hero.getBoundingClientRect().height) : null,
          stickerWidths: stickers,
        }
      })
      out.themeCount = btns.length
      out.activeCard = (() => {
        const el = document.querySelector('.remote-options button.is-active')
        if (!el) return null
        const r = el.getBoundingClientRect()
        const cs = getComputedStyle(el)
        return {label: (el.textContent || '').trim().slice(0, 12), borderColor: cs.borderColor, boxShadow: cs.boxShadow.slice(0, 60), h: Math.round(r.height)}
      })()
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

    cards = [t for t in geo["themeButtons"] if not t["isShuffle"]]
    shuffle = [t for t in geo["themeButtons"] if t["isShuffle"]]
    ys = sorted(set(t["y"] for t in cards))
    print(f"\npreview cards: {len(cards)}, rows (y): {ys} (expect 2 rows of 2)")
    if cards:
        widths = sorted(set(t["w"] for t in cards))
        print(f"card widths: {widths} (expect single width)")
        print(f"hero visible heights: {[t['heroVisible'] for t in cards]} (expect > 40)")
        print(f"sticker widths per card: {[t['stickerWidths'] for t in cards]} (expect 2 each, ~34px)")
        print(f"palettes: {[t['palette'] for t in cards]} (expect 4 distinct)")
    if shuffle:
        s = shuffle[0]
        print(f"shuffle strip: w={s['w']} h={s['h']} y={s['y']} (expect full row width, below card rows)")
    print(f"touch targets <44px: {geo['touchTargetsUnder44']} (expect 0)")
    print(f"overflow: {geo['overflow']} (expect [])")
    b.close()
