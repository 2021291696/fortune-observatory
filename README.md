# 看运（destiny）

用最不正经的互联网外壳，承载认真运行的排盘与运势能力。产品定位见 [PRODUCT.md](PRODUCT.md)，设计原则见 [DESIGN.md](DESIGN.md)，AI 协作约定见 [AGENTS.md](AGENTS.md)。

## 功能

- 三盘排盘：四柱八字 / 紫微斗数（十二宫）/ 七政四余（JPL 星历）
- 运势：今日/明日/周/月，真太阳时口径
- 问事：四板块（事业/感情/健康/财富）深度解读，AI 事实锚定 + 典籍语料（`apps/api/lore.py`），SSE 流式输出（思考链可折叠）
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

E2E 与全流程测试（run-all 三门：静态审查 + API + UI）见 [AGENTS.md](AGENTS.md)「本地跑」；`tests/fullflow/` 提供生产/本地双清单，本地链用 mock LLM 零配额。

AI 解读需要环境变量：`FORTUNE_AI_API_KEY` / `FORTUNE_AI_MODEL` / `FORTUNE_AI_CONTEXT_SECRET`（≥32 字节）/ `FORTUNE_AI_BASE_URL`，未配置时 AI 功能自动降级关闭。

## 部署（新加坡轻量服务器）

- 生产：**https://destiny.solplum.com**（43.160.211.207，`/opt/destiny`，systemd `destiny.service` 端口 8742，`apps/api/serve.py` 单进程同源发 SPA+API）
- 发布：本地构建前端（`.env.production.local` 已固化 `VITE_API_BASE=/api`）→ `tar` 打包上传 → 服务器 `sudo bash scripts/deploy/deploy.sh /tmp/destiny.tar.gz`（脚本内含 uv sync、systemd/nginx 安装、certbot SSL 重挂钩子）
- 密钥：`/opt/destiny/.env` 只在服务器（`FORTUNE_ALLOWED_HOSTS` 必须含 destiny.solplum.com）；HTTPS 由 certbot 自动续期，云防火墙 443 已放行
- 旧线（CloudBase 静态托管 + HTTP 云函数 `destiny-api`）：已被取代、待下线；`scripts/package_function.py` 打包流程仅为回退保留

## 目录

| 路径 | 内容 |
|---|---|
| `apps/observatory` | React 前端（五套表情包主题） |
| `apps/api` | FastAPI 后端（含 `lore.py` 解话语料、`reading_agent.py` 流式解读引擎、`dreams/` 解梦模块） |
| `src/fortune_core` | 排盘引擎（`docs/` 下有差分审计与口径 ADR，本地资产不入 git） |
| `skills/` | 三端 CLI skill 实体（bazi、ziwei-doushu） |
