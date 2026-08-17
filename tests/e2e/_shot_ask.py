"""线上 #ask 实况截图：看双面板布局乱象 + 实际答案深度。"""

import time

from playwright.sync_api import sync_playwright

URL = "https://sol-d2ga5fpq8bcf67f5a-1410845958.tcloudbaseapp.com/"

USER = {
    "id": "demo-1995",
    "name": "演示",
    "createdAt": "2026-08-16T10:00:00.000Z",
    "placeAdcode": "110105",
    "birth": {
        "civil_datetime": "1995-08-16T12:00:00+08:00",
        "timezone_id": "Asia/Shanghai",
        "longitude": 116.4074,
        "latitude": 39.9042,
        "sex_for_rule": "male",
        "use_apparent_solar_time": True,
    },
}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="zh-CN")
    page.goto(URL, wait_until="networkidle")
    page.evaluate(
        "(user) => { localStorage.setItem('fortune-users-v1', JSON.stringify([user]));"
        " localStorage.setItem('fortune-current-user-v1', JSON.stringify(user));"
        " localStorage.removeItem('fortune-ai-cache-v1'); }",
        USER,
    )
    page.on("request", lambda r: print("REQ", r.url.split("/")[-1], (("SPLIT" if (r.post_data or "").find("split_question") >= 0 else "NOSPLIT") + " len=" + str(len(r.post_data or "")))) if "/v1/ai/explain" in r.url else None)
    page.goto(URL + "?bust=" + str(int(time.time())) + "#ask", wait_until="networkidle")
    page.reload(wait_until="networkidle")
    page.locator(".domain-choices button", has_text="健康").first.click()
    # 等真实 AI 生成完（最多 40s）
    for _ in range(40):
        time.sleep(1)
        if page.locator("#analysis .ai-answer").count() >= 1:
            break
    time.sleep(1)
    print("ai-progress:", page.locator("#analysis .ai-progress").count())
    print("ai-answer:", page.locator("#analysis .ai-answer").count())
    print("追问按钮:", page.locator("#analysis .ai-followup-toggle").count())
    print("AI解读头:", page.locator("#analysis .ai-answer header").count())
    output = page.locator(".domain-reading")
    output.screenshot(path="tests/.artifacts/audit/ask_live_mess.png")
    total = page.evaluate("() => Array.from(document.querySelectorAll('#analysis .ai-answer')).map(a => a.innerText.length).join(',')")
    print("两篇字数:", total)
    browser.close()
