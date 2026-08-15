"""Probe MiniMax directly to compare max_tokens 800 vs 1150 raw responses.

Outbound requests are locked to a single hardcoded HTTPS host; anything else
is rejected before any socket is opened.
"""

import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error

ALLOWED_HOST = "api.minimaxi.com"
URL = "https://api.minimaxi.com/v1/text/chatcompletion_v2"

parsed = urllib.parse.urlsplit(URL)
assert parsed.scheme == "https", "probe must use https"
assert parsed.hostname == ALLOWED_HOST, f"probe host locked to {ALLOWED_HOST}, got {parsed.hostname}"
assert parsed.hostname not in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
assert not parsed.hostname.startswith(("10.", "192.168.", "172."))

KEY = os.environ.get("MINIMAX_KEY", "")
if not KEY:
    raise SystemExit("MINIMAX_KEY env not set")

SYS = '你是命理产品中的解释层。只返回符合约定结构的 JSON：{"summary":{"text":"...","fact_ids":["f1"]},"actions":[],"caveats":[]}'
FACTS = json.dumps({
    "question": "请用白话讲讲我财帛宫星情反映的用钱习惯，并给一条管钱小原则。",
    "facts": [
        {"id": "domain-1", "text": "财帛宫位于辰"},
        {"id": "domain-2", "text": "该宫主星为天机（利）、天梁（庙）"},
    ],
}, ensure_ascii=False)

for mt in (800, 1150):
    payload = {
        "model": "MiniMax-Text-01",
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": "USER_DATA_JSON\n" + FACTS},
        ],
        "temperature": 0.2,
        "max_tokens": mt,
    }
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers={
        "content-type": "application/json", "authorization": f"Bearer {KEY}",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            body = json.loads(r.read())
            content = body["choices"][0]["message"].get("content", "")
            finish = body["choices"][0].get("finish_reason", "?")
            usage = body.get("usage", {})
            print(f"max_tokens={mt}: 200 {time.time()-t0:.1f}s finish={finish} "
                  f"total={usage.get('total_tokens')} completion={usage.get('completion_tokens')} "
                  f"content-head={content[:80]!r}")
    except urllib.error.HTTPError as e:
        print(f"max_tokens={mt}: {e.code} {time.time()-t0:.1f}s {e.read()[:200]}")
    time.sleep(1)
