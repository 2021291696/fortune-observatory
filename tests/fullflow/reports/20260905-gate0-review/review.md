# destiny 门0 静态审查报告（run-all 2026-09-05）

- 审查口径：logic-review `--full`，scope = 整个 destiny 代码库，重点区间 `9045b26..HEAD`（本会话 7 个 WIP 收录提交 + 4 个修复提交）
- 执行方式：主模型逐维对照 code-checklist（10 维）；辅助证据 = 本会话双 Explore agent 深扫报告 + verified/differential 127 passed
- 审查对象状态：工作区干净（全部已提交本地 main，未推远端）

## 维度结论

### 1. 功能正确性 — PASS
- 修复点逐一验证：预算 429（app.py reading 端点 try 包裹 + 死 except 移除）、转介含 answers（dreams/service.py is_referral/compose_query）、fact 截断（6 处 `text[:400]`）、北京口径（预算日切/虚岁/大限/缓存键/日历今天共 5 处）、超时墙钟（_complete_once 按剩余时间收缩单次超时 + dreams 重试墙钟保险）、追问缓存守卫（AiExplainPanel 看 followUp 标志）。
- 边界：StreamSession.finish 原子化后晚到 attach 回放见终态（test_finish_is_atomic_for_late_attacher）；1901 年最早可提交出生日排盘 200（test_chart_facts_truncated_for_oldest_births）。
- 证据：`pytest tests/verified tests/differential` → **127 passed**（含 iztro 2080 盘例差分）。

### 2. 安全红线 — PASS
- 无硬编码密钥：`git diff 9045b26..HEAD` 密钥模式扫描零命中；`.env.example` 全为空值模板。
- 输入边界校验：BirthInput（offset↔IANA 一致性 + DST 空缺/重叠拒绝）实测生效——1849/1900 的 `+08:00` 被 LMT 校验正确 422。
- 自伤转介漏洞（追问绕过）已修并有路由级回归（test_dreams_interpret_rejects_unclean_answers_via_route：转介命中且零扣预算）。
- 流式内容安全双标已消除：reading/解梦收尾全文跑 `safety_violation()`，命中 error+code=safety（4 项回归钉住）。
- 日志不打印敏感字段：500 日志只记 type+trace_id（本轮补了 exc_info 堆栈，堆栈只进日志不进响应）。

### 3. 性能 — PASS
- 会话注册表加 128 上限，创建时逐出最旧终态会话（堵"只在新请求时清理"的慢泄漏）。
- explain/解梦 provider 重试加 56s 墙钟收手，不再被中间件门砍成 504 白烧预算。
- 前端构建 701ms，主 chunk 555KB（gzip 后约 200KB，nginx 已配）——既有状况，非本轮引入。

### 4. 代码质量 — PASS
- 死代码已清：lifePhase.ts 整文件、readingNarrative 三个死函数、streamReading 不可达尾码（run 的 key 参数随之移除）、`void run`、`_parse_interpret` 死参数、app.py 死 except（预算 429 修复时一并处理）。
- compose_query 由死代码转为 is_referral 的实现路径。
- 未用导入复核：`tzone`/`dtime` 在 app.py:736 仍有使用，保留正确。

### 5. 可维护性 — PASS
- 超时三层/provider 重试/墙钟/日切口径均有注释写明约束与理由；AGENTS.md 同步为"三层勿混用"口径。

### 6. 架构对齐 — PASS
- 改动全部落在既有分层：AI 语境/预算在 ai_explainer，流式会话在 reading_agent，解梦在 dreams/，前端流式消费在 streamReading.ts；未引入新依赖（ZoneInfo/time 均标准库）。
- 断线续传契约未破坏：复用不计费语义保持（429 只在新会话扣减时抛出），测试覆盖。

### 7. 变更风险 — PASS（带披露）
- SSE error 事件新增 `code` 字段：向后兼容（多余字段，旧消费方忽略）。
- ai_timeout 28s→62s：代码内显式参数，无部署侧 .env 变更需求；AGENTS.md 已同步。
- 非 AI 端点错误文案中文化：无消费方断言旧英文文案（500 断言已同步更新）；CLI skill 不走这些 HTTP 端点。

### 8. 需求对齐 — PASS
- 用户四项决策全部落地：WIP 分主题 commit（7 个）✓、run-all 本地全链 ✓、日历自动生成本轮不改 ✓、流式内容安全补齐 ✓。
- 范围蔓延：无（改动全部在批准的计划内；ENGINE 边角问题仅记录未动）。

### 9. 测试覆盖 — PASS
- 新逻辑 9 项回归（test_safety_alignment 5 + test_review_fixes_202609 4）；修过的 bug 全部有对应回归测试。
- 既有 113 项 verified 全绿 + differential（2080 盘例）零回归。

### 10. 技术选型 — N/A
- 本轮无新技术选型 plan。

## 内容审查（--full 的 content 侧）

- ① 文档一致性：AGENTS.md/DESIGN.md 与实现对齐（超时三层、safety_violation、日切口径、主题遥控器位置）— PASS
- ⑤ 一致性：错误文案全站中文（security.py 9 处 + 500 + 422 带原因）；流式 error 提示语与触发条件一致 — PASS
- ③ 视觉质量：本轮无视觉样式改动（仅交互逻辑），视觉验收转入门2 UI（Playwright 走查解梦链）
- ⑥ 残留物：`grep void run`/死注释零残留 — PASS

## 已知残留（记录在案，非本轮 FAIL）

1. **reading 路径 history 注入为真实对话消息**（审查 M4）：自注入为主、风险有限，与 explain 的"不可信数据块"隔离策略不一致——改动会影响生成行为，需单独评估，本轮不动。
2. **引擎边角两处**（2/29 起运模板、童限 nominal_age≤0 索引）：数据可达范围外，概率极低，未动。
3. **日历逐日 auto 生成**：用户拍板保持现状。

## 结论

✅ **APPROVE** — 无 blocking，可进入门1。
- 代码审查：0 FAIL / 关键 PASS 证据如上
- 内容审查：0 FAIL
- 自动修复：0（本轮无白名单残留项）
