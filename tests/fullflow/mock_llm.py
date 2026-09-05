"""本地全流程测试用的 OpenAI 兼容 mock LLM（协议真、输出固定）。

用途：destiny 本地门 1/门 2 —— 不依赖真实 provider key，但让 AI 链路
（explain / dreams questions / interpret / 流式 SSE）按真实协议端到端跑通。
启动：uv run python tests/fullflow/mock_llm.py --port 9999
对接：FORTUNE_AI_BASE_URL=http://127.0.0.1:9999/v1
      FORTUNE_AI_ALLOW_LOCAL_PROVIDER=true  FORTUNE_AI_ALLOWED_HOSTS=127.0.0.1
"""

from __future__ import annotations

import argparse
import asyncio
import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()

_EXPLAIN_JSON = json.dumps({
    "summary": {"text": "按盘面事实，近期节奏偏稳，宜按部就班推进眼前的事。", "fact_ids": []},
    "actions": [{"text": "把今天最重要的三件事写下来再开始。", "fact_ids": []}],
    "caveats": [{"text": "运势只是参照，决定仍在你自己。", "fact_ids": []}],
}, ensure_ascii=False)

_QUESTIONS_JSON = json.dumps({
    "questions": [
        {"id": "finished", "label": "梦到最后是完成了还是被打断？"},
        {"id": "agency", "label": "走进那个场面时，你是自愿的还是被带着走的？"},
        {"id": "fear_of", "label": "整场梦里最让你发紧的是哪一幕？"},
    ]
}, ensure_ascii=False)

_INTERPRET_JSON = json.dumps({
    "essay": "这场梦把熟悉的场景变得陌生又失控，常见于现实里事情开始超出掌控的阶段。"
             "黑板擦不干净，往往对应「越努力收拾越觉得没收拾好」的紧绷感。"
             "按荣格的补偿视角，梦在提醒你：允许一些事暂时留在没做完的状态。",
    "sources": [
        {"work": "荣格解梦方法论", "quote": "梦是意识的补偿，先于判断地呈现另一侧"},
        {"work": "荣格象征词典", "quote": "教室与考试常见于被评判焦虑的梦境素材"},
    ],
}, ensure_ascii=False)

_ESSAY_STREAM = (
    "这场梦里，小学教室的桌椅变小、黑板越擦越黑，像是在重演一种「怎么努力都不对」的无力感。"
    "《梦的解析》里说：「梦是通往潜意识的无声小径」，它常常把白天没说出口的紧绷换成画面。"
    "荣格的补偿视角会问：醒着的你是不是把太多事都攥在自己手里了？\n\n"
    "## 可以先做\n\n- 把最挂心的那件事写下来，只写一句。\n"
    "- 给明天留一段 15 分钟的空档，什么都不安排。\n\n## 注意\n\n梦不预言现实，只反映节奏。"
)


def _pick_response(body: dict) -> str:
    system = ""
    messages = body.get("messages") or []
    if messages and isinstance(messages[0], dict):
        system = str(messages[0].get("content") or "")
    if "解释层" in system:
        return _EXPLAIN_JSON
    if "问正好 3 个短问题" in system:
        return _QUESTIONS_JSON
    return _INTERPRET_JSON


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    if body.get("stream"):
        async def sse():
            chunks = [("<think>mock 思考：组织解梦口径。", ), ("</think>",)]
            text = _ESSAY_STREAM
            step = 24
            for index in range(0, len(text), step):
                chunks.append((text[index:index + step],))
            for (piece,) in chunks:
                payload = {"choices": [{"delta": {"content": piece}, "finish_reason": None}]}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)
            yield "data: " + json.dumps({"choices": [{"delta": {}, "finish_reason": "stop"}]}, ensure_ascii=False) + "\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(sse(), media_type="text/event-stream")
    content = _pick_response(body)
    return JSONResponse({
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"completion_tokens": 128, "total_tokens": 256},
    })


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9999)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
