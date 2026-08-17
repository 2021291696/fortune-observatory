"""线上探针：分段并行生成（分析篇+行动篇）实测总字数与墙钟时间。"""

import json
import time
from concurrent.futures import ThreadPoolExecutor

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

ANALYSIS_Q = (
    "请综合我的三张命盘（四柱日主、紫微疾厄宫及三方四正、七政昼夜盘与庙旺恩难）"
    "只做盘面分析、不用给建议，分四段写：①结论一句话加一个日常比喻；"
    "②我的体质与精力特点——结合日主五行与疾厄宫主星讲清为什么；"
    "③最该留意的身体信号与生活习惯诱因——结合对宫三合星曜与藏干；"
    "④七政线索——结合昼夜盘、命主与庙旺恩难星曜讲调节方向。"
    "每段都要引用具体盘面依据，每个命理术语第一次出现都立刻解释成白话。不涉及任何诊断或用药。"
)
ACTION_Q = (
    "请基于我的三张命盘（四柱日主、紫微疾厄宫及三方四正、七政昼夜盘与庙旺恩难）"
    "只输出行动方案：2-4条行动建议，每条分\"为什么（对应哪张盘的哪个依据）/怎么做"
    "（具体到本周能执行的动作）/怎么算做到了（可检查的信号）\"三层来写；"
    "最后补1-2条提醒，其中一条写成\"只需记住这一条\"式的单句规则。"
    "每个命理术语第一次出现都立刻解释成白话。不涉及任何诊断或用药。"
)

client = httpx.Client(timeout=60)
token = client.post(f"{BASE}/v1/charts", json=BIRTH).json()["ai_contexts"]["health"]["token"]


def ask(name: str, question: str):
    t0 = time.time()
    resp = client.post(f"{BASE}/v1/ai/explain", json={"question": question, "context_tokens": [token]})
    elapsed = time.time() - t0
    if resp.status_code != 200:
        return name, elapsed, 0, f"HTTP {resp.status_code} {resp.text[:120]}"
    answer = resp.json()
    length = (
        len(answer["summary"]["text"])
        + sum(len(a["text"]) for a in answer["actions"])
        + sum(len(c["text"]) for c in answer["caveats"])
    )
    return name, elapsed, length, answer["summary"]["text"][:120]


t0 = time.time()
with ThreadPoolExecutor(max_workers=2) as pool:
    results = list(pool.map(lambda pair: ask(*pair), [("分析篇", ANALYSIS_Q), ("行动篇", ACTION_Q)]))
wall = time.time() - t0

total = 0
for name, elapsed, length, preview in results:
    total += length
    print(f"{name}: {length}字 / 单独耗时 {elapsed:.1f}s — {preview}")
print(f"合计 {total} 字，墙钟 {wall:.1f}s（并行生效则 wall ≈ max(单独耗时)）")
