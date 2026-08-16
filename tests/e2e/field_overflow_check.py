"""Verify field-text fixed-width + ellipsis at 390px: birth-form selects, user chip, session pill, saved-card title.

Usage: uv run --project apps/observatory python tests/e2e/field_overflow_check.py [url]
Default url = local dev server (http://127.0.0.1:5173/).
"""

import json
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5173/"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 390, "height": 844}, locale="zh-CN", is_mobile=True, has_touch=True)

    # --- Part 1: fresh visitor -> birth form with the longest cascade names ---
    pg.goto(URL + "#fortune", wait_until="networkidle")
    pg.wait_for_timeout(600)
    pg.select_option('select[aria-label="省份"]', label="新疆维吾尔自治区")
    pg.select_option('select[aria-label="城市或辖区"]', label="克孜勒苏柯尔克孜自治州")
    district = pg.locator('select[aria-label="区县"]')
    district.select_option(index=0)
    chosen_district = district.locator("option").nth(0).inner_text()
    pg.wait_for_timeout(200)
    pg.locator(".birth-form").screenshot(path="tests/.artifacts/field-form-xinjiang.png")

    form_geo = pg.evaluate("""() => {
      const out = { selects: [], overflow: [] }
      for (const s of document.querySelectorAll('.place-field select')) {
        const r = s.getBoundingClientRect()
        out.selects.push({
          label: s.getAttribute('aria-label'),
          text: (s.selectedOptions[0] || {}).textContent,
          w: Math.round(r.width), h: Math.round(r.height),
          textOverflow: getComputedStyle(s).textOverflow,
          clientWidth: s.clientWidth, scrollWidth: s.scrollWidth,
        })
      }
      const vw = document.documentElement.clientWidth
      for (const el of document.querySelectorAll('body *')) {
        const r = el.getBoundingClientRect()
        if (r.width === 0 || r.height === 0) continue
        if (r.right > vw + 2 && r.width < vw) { out.overflow.push(el.tagName + '.' + (el.className || '').toString().split(' ')[0]); if (out.overflow.length > 8) break }
      }
      return out
    }""")
    print("== birth form (city = 克孜勒苏柯尔克孜自治州, district = " + chosen_district + ") ==")
    print(json.dumps(form_geo, ensure_ascii=False, indent=2))

    # --- Part 2: seeded users + long saved reading -> header pill / chip / saved card ---
    pg.evaluate("""() => {
      localStorage.setItem('fortune-current-user-v1', 'u-long-0001')
      localStorage.setItem('fortune-users-v1', JSON.stringify([
        {id:'u-long-0001', name:'一二三四五六七八九十十一十二', createdAt:'2026-08-16T00:00:00+08:00',
         birth:{civil_datetime:'1990-05-04T08:30', timezone_id:'Asia/Shanghai', longitude:116.4, latitude:39.9, sex_for_rule:'male', use_apparent_solar_time:true}},
        {id:'u-long-0002', name:'甲乙丙丁戊己庚辛壬癸子丑', createdAt:'2026-08-16T00:00:00+08:00',
         birth:{civil_datetime:'1992-11-20T22:05', timezone_id:'Asia/Shanghai', longitude:121.5, latitude:31.2, sex_for_rule:'female', use_apparent_solar_time:true}},
      ]))
      localStorage.setItem('fortune-saved-readings-v1', JSON.stringify([{
        id:'sr-long-0001', kind:'domain',
        title:'超长标题验证'.repeat(12),
        summary:'摘要', details:[],
        userName:'一二三四五六七八九十十一十二', savedAt:'2026-08-16T09:00:00+08:00',
      }]))
    }""")
    pg.goto(URL + "#profile", wait_until="networkidle")
    pg.reload(wait_until="networkidle")
    pg.wait_for_timeout(800)

    seed_geo = pg.evaluate("""() => {
      const out = {}
      const pill = document.querySelector('.session-state .session-copy')
      if (pill) {
        out.sessionPill = {text: pill.textContent, clientWidth: pill.clientWidth, scrollWidth: pill.scrollWidth,
          textOverflow: getComputedStyle(pill).textOverflow,
          parentMaxWidth: getComputedStyle(document.querySelector('.session-state')).maxWidth}
      }
      const name = document.querySelector('.user-pick .user-name')
      if (name) {
        out.userChipName = {text: name.textContent, clientWidth: name.clientWidth, scrollWidth: name.scrollWidth,
          textOverflow: getComputedStyle(name).textOverflow}
      }
      const h3 = document.querySelector('.saved-grid h3')
      if (h3) {
        out.savedTitle = {text: (h3.textContent || '').slice(0, 14) + '…', clientWidth: h3.clientWidth, scrollWidth: h3.scrollWidth,
          textOverflow: getComputedStyle(h3).textOverflow, whiteSpace: getComputedStyle(h3).whiteSpace}
      }
      const kind = document.querySelector('.saved-kind')
      if (kind) {
        out.savedKind = {textOverflow: getComputedStyle(kind).textOverflow, display: getComputedStyle(kind).display}
      }
      const vw = document.documentElement.clientWidth
      out.overflow = []
      for (const el of document.querySelectorAll('body *')) {
        const r = el.getBoundingClientRect()
        if (r.width === 0 || r.height === 0) continue
        if (r.right > vw + 2 && r.width < vw) { out.overflow.push(el.tagName + '.' + (el.className || '').toString().split(' ')[0]); if (out.overflow.length > 8) break }
      }
      return out
    }""")
    print("\n== seeded header + profile ==")
    print(json.dumps(seed_geo, ensure_ascii=False, indent=2))
    pg.screenshot(path="tests/.artifacts/field-profile-seeded.png", full_page=False)

    b.close()
    print("\nscreenshots: tests/.artifacts/field-form-xinjiang.png, tests/.artifacts/field-profile-seeded.png")
