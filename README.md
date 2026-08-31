# 看运（destiny）

用最不正经的互联网外壳，承载认真运行的排盘与运势能力。产品定位见 [PRODUCT.md](PRODUCT.md)，设计原则见 [DESIGN.md](DESIGN.md)，AI 协作约定见 [AGENTS.md](AGENTS.md)。

## 功能

- 三盘排盘：四柱八字 / 紫微斗数（十二宫）/ 七政四余（JPL 星历）
- 运势：今日/明日/周/月，真太阳时口径
- 问事：四板块（事业/感情/健康/财富）深度解读，AI 事实锚定 + 典籍语料（`apps/api/lore.py`）
- 解梦：RAG 语料 + AI 散文输出
- 三端 CLI 算命 skill：`skills/`（实体在本仓库，junction 挂载 Claude Code / Codex / ZCode）

## 本地开发

```bash
# 后端（Python 3.12+，uv 管依赖）
cd apps/api && PYTHONPATH="../..;../../src" ../../.venv/Scripts/python.exe -m uvicorn app:app --port 8000
# 前端
cd apps/observatory && npm install && npm run dev   # 5173
# 测试（全量约 4 分钟，含 2080 盘例差分，需 Node）
.venv/Scripts/python.exe -m pytest tests/verified tests/differential
```

AI 解读需要环境变量：`FORTUNE_AI_API_KEY` / `FORTUNE_AI_MODEL` / `FORTUNE_AI_CONTEXT_SECRET`（≥32 字节）/ `FORTUNE_AI_BASE_URL`，未配置时 AI 功能自动降级关闭。

## 部署（CloudBase）

- API：`.venv/Scripts/python.exe scripts/package_function.py` 打包到 `.deploy-stage/` → HTTP 云函数 `destiny-api`（Python 3.10）
- 前端：`cd apps/observatory && npm run build` → 静态托管上传 `dist`

## 目录

| 路径 | 内容 |
|---|---|
| `apps/observatory` | React 前端（五套表情包主题） |
| `apps/api` | FastAPI 后端（含 `lore.py` 解话语料、`dreams/` 解梦模块） |
| `src/fortune_core` | 排盘引擎（`docs/` 下有差分审计与口径 ADR，本地资产不入 git） |
| `skills/` | 三端 CLI skill 实体（bazi、ziwei-doushu） |
