"""Production smoke: real MiniMax calls through the live API for the unlocked AI policy.

Usage: uv run --project apps/observatory python tests/e2e/ai_smoke_live.py
"""

import json
import sys

import httpx

BASE = "https://sol-d2ga5fpq8bcf67f5a.service.tcloudbase.com/destiny"
assert BASE.startswith("https://sol-d2ga5fpq8bcf67f5a.service.tcloudbase.com/"), "host allowlist"

BIRTH = {
    "civil_datetime": "1995-06-15T08:30:00+08:00",
    "timezone_id": "Asia/Shanghai",
    "longitude": 116.4074,
    "latitude": 39.9042,
    "sex_for_rule": "male",
    "use_apparent_solar_time": True,
}


def main() -> None:
    client = httpx.Client(timeout=60)
    status = client.get(f"{BASE}/v1/ai/status").json()
    print("ai status:", status)
    if not status.get("available"):
        sys.exit("AI provider unavailable")

    chart = client.post(f"{BASE}/v1/charts", json=BIRTH)
    chart.raise_for_status()
    body = chart.json()
    contexts = body.get("ai_contexts", {})
    print("context keys:", sorted(contexts.keys()))
    ziwei = contexts.get("ziwei")
    if ziwei:
        print(f"ziwei facts: {len(ziwei['facts'])} 条")
        print("  样例:", ziwei["facts"][0]["text"], "…")
        print("  样例:", ziwei["facts"][1]["text"], "…")

    samples = []

    if ziwei:
        samples.append((
            "紫微整盘",
            "请用白话解读我的紫微命盘整体格局：先一句话结论加一个比喻；再讲命宫和身宫的星曜组合各意味着什么（每个术语都配一句白话）；最后给我2到4条今天就能做的具体行动建议。",
            [ziwei["token"]],
        ))

    daily = client.post(
        f"{BASE}/v1/transits/daily",
        json={"birth": BIRTH, "transit_date": "2026-08-16"},
    )
    daily.raise_for_status()
    daily_context = daily.json().get("ai_context")
    if daily_context:
        print("\ndaily facts:")
        for fact in daily_context["facts"]:
            print("  -", fact["text"])
        samples.append((
            "今日运势",
            "请把我的今日运势讲成一段直白的白话解读：先一句话结论加一个比喻，再说今天最值得注意的一件事和一件适合先做的小事（术语都配白话）。",
            [daily_context["token"]],
        ))

    for title, question, tokens in samples:
        print(f"\n========== {title} ==========")
        response = client.post(
            f"{BASE}/v1/ai/explain",
            json={"question": question, "context_tokens": tokens},
        )
        if response.status_code != 200:
            print(f"HTTP {response.status_code}: {response.text[:200]}")
            continue
        answer = response.json()
        print("【结论】", answer["summary"]["text"])
        print("  引用:", answer["summary"].get("fact_ids"))
        for i, action in enumerate(answer.get("actions", []), 1):
            print(f"【行动{i}】", action["text"])
        for i, caveat in enumerate(answer.get("caveats", []), 1):
            print(f"【提醒{i}】", caveat["text"])


if __name__ == "__main__":
    main()
