"""线上探针：实测问事(健康域)答案长度与延迟，量化"太简短"。"""

import json
import time

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

QUESTION = (
    "请综合我的三张命盘（四柱日主、紫微疾厄宫及三方四正、七政昼夜盘与庙旺恩难）"
    "写一篇深度白话健康分析，全文分五部分："
    "①结论一句话加一个日常比喻；"
    "②我的体质与精力特点——结合日主五行与疾厄宫主星，讲清为什么（约150字）；"
    "③最该留意的身体信号与生活习惯诱因——结合对宫三合与藏干（约150字）；"
    "④七政线索——结合昼夜盘、命主与庙旺恩难星曜，给出调节方向（约150字）；"
    "⑤2-4条行动建议，每条约70字，说清为什么、怎么做、怎么算做到了。"
    "每个命理术语第一次出现都立刻解释成白话。不涉及任何诊断或用药。"
)

client = httpx.Client(timeout=60)
chart = client.post(f"{BASE}/v1/charts", json=BIRTH)
chart.raise_for_status()
contexts = chart.json()["ai_contexts"]
health = contexts.get("health")
print("health facts 数:", len(health["facts"]) if health else 0)
for fact in (health["facts"] if health else [])[:8]:
    print("  -", fact["text"][:80])

t0 = time.time()
resp = client.post(
    f"{BASE}/v1/ai/explain",
    json={"question": QUESTION, "context_tokens": [health["token"]]},
)
elapsed = time.time() - t0
print(f"\nexplain HTTP {resp.status_code}  {elapsed:.1f}s")
if resp.status_code == 200:
    answer = resp.json()
    summary = answer["summary"]["text"]
    actions = [a["text"] for a in answer["actions"]]
    caveats = [c["text"] for c in answer["caveats"]]
    print(f"summary {len(summary)} 字: {summary[:200]}")
    print(f"actions {len(actions)} 条，均长 {sum(len(a) for a in actions)//max(len(actions),1)} 字")
    print(f"caveats {len(caveats)} 条，均长 {sum(len(c) for c in caveats)//max(len(caveats),1)} 字")
    print(f"总字数: {len(summary) + sum(len(a) for a in actions) + sum(len(c) for c in caveats)}")
else:
    print(resp.text[:300])
