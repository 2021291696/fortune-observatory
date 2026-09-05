# destiny（看运）— 项目约定

## 结构

- `apps/observatory`：React 前端（Vite，五套表情包主题，5173）
- `apps/api`：FastAPI 后端（排盘/运势/问事/解梦/AI 解读，8000；app.py 平级导入 security/lore/fortune_core；dreams/ 为解梦模块）
- `src/fortune_core`：排盘核心引擎（八字/紫微/七政四余/真太阳时）——网站排盘唯一计算源
- `skills/`：三端 CLI 命理 skill 实体（bazi、ziwei-doushu、dream-interpretation）
- `docs/` 整目录是 gitignore 的本地资产（审计报告/计划/交接），不进 git

## skills/ = 三端 skill 实体（source of truth）

- 实体在仓库内；`~/.agents/skills/<name>` 是指向仓库的 junction，`~/.claude/skills` 与 `~/.codex/skills` 再链 `~/.agents/skills`，ZCode 直读 `~/.agents/skills`
- 改 skill 一律改仓库内文件，禁止把 junction 当普通目录删改；建 junction 用 PowerShell `New-Item -ItemType Junction`（Git Bash 的 mklink 会被 MSYS 参数转换搅坏）
- `skills/ziwei-doushu` 首次使用先 `npm install`（node_modules 已 gitignore）；`references/*.md` 由 `scripts/dump_refs.ts` 生成，勿手改；上游源码在 `vendor/`（Renhuai123/ziwei-doushu@88194a4，MIT，iztro 2.5.8）

## 排盘口径

- skills/*/scripts 的排盘脚本是**第二实现**，只用于差分校验（`tests/differential/`），禁止接入线上计算路径
- 差分回归：`.venv/Scripts/python.exe -m pytest tests/differential`（八字 10 例 + iztro 2080 盘例，后者需 Node）

## AI 解读层

- `apps/api/lore.py` = 分体系解话语料（十四主星/四化论/十神旺衰/七政恩难仇用/运势断法），按 bundle_type 注入 system prompt；lore 只提供通识断语，禁止参与任何排盘计算
- 断语权威 = `skills/*/references` 原文整包（`lore.py: skill_canon()` 注入，含 SKILL.md 第三阶段分析框架）；SKILL.md 无 LICENSE，原样收录
- facts 上限 24 条 × 400 字符（2026-08-31 由 16×280 放宽，签名 token 上限同步 48K；组装侧一律 `text[:400]` 截断）；summary 上限 3600 字；安全正则（确定性断语/用药/投资指令）不许放松——已抽成 `ai_explainer.safety_violation()`，非流式 `_parse_answer` 与流式（reading/解梦）收尾全文校验共用同一口径，命中以 error+code=safety 收尾
- 流式解读引擎 = `apps/api/reading_agent.py`（skill 原典内联 + 流式 + `_ThinkFilter` 拆 think 链）；SSE 端点 `POST /v1/ai/reading` 与 `/v1/dreams/interpret/stream`。生成挂在服务端 StreamSession 注册表：断连不中止生成、同 stream_key 重连先回放再续播、预算只在全新生成时扣——改流式管道不得破坏这份续传契约
- 前端流式消费统一走 `apps/observatory/src/streamReading.ts`：打字机节奏器分 displayText（渲染层）与 text（真值层），缓存/持久化只能用 text；思考折叠条 = `ThinkingTrace`；问事聊天跨页签存活靠 DomainAnalysisConsole 的 chatTurns 模块级注册表
- AI 超时三层勿混用：provider 单次调用默认 40s、上限 55s（env `FORTUNE_AI_TIMEOUT_SECONDS`）；非流式端点被 RequestGuard 的 ai 门 62s 硬顶，explain/解梦的 provider 重试自带 56s 墙钟收手（改任何一层都要对齐另外两层）；流式路径（reading_agent.py）上游读超时 280s，另 SSE 心跳 20s/续传 ping 10s。AI 日预算按北京时间零点日切，429 的 Retry-After 动态算到零点
- 解梦口径 = `dreams/lore.py` 读 `skills/dream-interpretation/references`（方法论全文+心灵结构核心+象征词典）；自伤叙述（梦正文与追问回答都查）确定性转介不走 LLM；对照命盘（overlay）已下线，请求带 overlay/context_tokens 一律 422；`dreams/service.py` 非流式固定 ≥50s 长超时（在 RequestGuard 62s AI 门内）

## 生产部署

- 生产 = 新加坡轻量 43.160.211.207 的 `/opt/destiny`（systemd `destiny.service`，端口 8742；ssh 登录用户 `ubuntu`，root 未授权）；`scripts/deploy/deploy.sh` 每次部署会用仓库模板覆盖 nginx/systemd 配置、并由内置钩子重挂 certbot SSL——**改 nginx/服务配置一律改仓库模板再部署，禁止手改服务器文件了事**
- `.env`（FORTUNE_* 密钥）只在服务器 `/opt/destiny/.env`，不入 git；`FORTUNE_ALLOWED_HOSTS` 必须含 `destiny.solplum.com`，漏了会被 TrustedHostMiddleware 拒 400；模板覆盖前必须先 `chown` 应用目录给 `destiny` 用户（deploy.sh 已内置顺序，勿倒置）
- 打包白名单 = `apps/api src skills apps/observatory/dist scripts/deploy pyproject.toml uv.lock`（排除 `__pycache__`）；2026-09-03 起 dist 含 364 个霞鹜文楷 unicode-range woff2 分包（浏览器按需下载，首屏仅几百 KB），成品约 21MB；Windows 工作区 checkout 的 deploy.sh 带 CRLF，服务器端用 `tr -d "\r" < deploy.sh | sudo bash -s -- 包路径` 执行

## 本地跑

```bash
# 后端（必须 cd apps/api，PYTHONPATH 扁平导入）
cd apps/api && PYTHONPATH="../..;../../src" ../../.venv/Scripts/python.exe -m uvicorn app:app --port 8000
# 前端
cd apps/observatory && npm run dev
# 全量测试
.venv/Scripts/python.exe -m pytest tests/verified tests/differential
```

- E2E：`tests/e2e`（需本地 vite:5173 + api:8000 在跑；AI 端点用 page.route mock 保证确定性、不烧配额）。流式 UI 断言必须用 `expect(...).to_contain_text` 自动重试——打字机节奏器在 done 后还要排空尾部字符，立即读 inner_text 会间歇缺字（2026-09-03 实锤）
- 全流程测试（run-all）：`tests/fullflow/`——manifest.yaml（生产）/manifest.local.yaml（本地 serve:8765）/manifest.ui.yaml·manifest.local.ui.yaml（门2 纯 UI 链）。本地链 = `.venv/Scripts/python.exe tests/fullflow/mock_llm.py --port 9999` + serve.py 带 `FORTUNE_AI_ALLOW_LOCAL_PROVIDER=true FORTUNE_AI_ALLOWED_HOSTS=127.0.0.1`，零真实配额；executor 打私网目标要加 `FULLFLOW_ALLOW_PRIVATE_TARGET=1`（2026-09-05 实锤）
