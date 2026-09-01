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
- facts 上限 24 条 × 400 字符（2026-08-31 由 16×280 放宽，签名 token 上限同步 48K）；summary 上限 3600 字；`_parse_answer` 的安全正则（确定性断语/用药/投资指令）不许放松
- AI 超时：默认 40s、硬顶 55s（env `FORTUNE_AI_TIMEOUT_SECONDS` 可覆盖）；解梦 prompt 含全量口径，`dreams/service.py` 固定 50s
- 解梦口径 = `dreams/lore.py` 读 `skills/dream-interpretation/references`（方法论全文+心灵结构核心+象征词典）；自伤叙述确定性转介不走 LLM；对照命盘（overlay）已下线，请求带 overlay/context_tokens 一律 422

## 生产部署

- 生产 = 新加坡轻量 43.160.211.207 的 `/opt/destiny`（systemd `destiny.service`，端口 8742；ssh 登录用户 `ubuntu`，root 未授权）；`scripts/deploy/deploy.sh` 每次部署会用仓库模板覆盖 nginx/systemd 配置、并由内置钩子重挂 certbot SSL——**改 nginx/服务配置一律改仓库模板再部署，禁止手改服务器文件了事**
- `.env`（FORTUNE_* 密钥）只在服务器 `/opt/destiny/.env`，不入 git；`FORTUNE_ALLOWED_HOSTS` 必须含 `destiny.solplum.com`，漏了会被 TrustedHostMiddleware 拒 400；模板覆盖前必须先 `chown` 应用目录给 `destiny` 用户（deploy.sh 已内置顺序，勿倒置）

## 本地跑

```bash
# 后端（必须 cd apps/api，PYTHONPATH 扁平导入）
cd apps/api && PYTHONPATH="../..;../../src" ../../.venv/Scripts/python.exe -m uvicorn app:app --port 8000
# 前端
cd apps/observatory && npm run dev
# 全量测试
.venv/Scripts/python.exe -m pytest tests/verified tests/differential
```
