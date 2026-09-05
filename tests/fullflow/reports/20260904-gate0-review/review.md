# destiny 门 0 静态审查报告（logic-review --full 全项目口径）

- 日期：2026-09-04
- scope：整库（src/fortune_core + apps/api + apps/observatory + tests + 部署配置）
- 触发时机：提交/全流程测试前（安全=blocking）
- 前置引用：本会话同日完成的深度安全审查（Mimosa 深扫 + API 全链路人工审查 + 部署配置审查），其 7 项发现（M1/M2/L1-L4/B1）已全部修复并验证

## 代码审查（10 维）

| # | 维度 | 判定 | 关键证据 |
|---|------|------|---------|
| 1 | 功能正确性 | PASS | BirthInput 时区交叉验证+年份域 1849-2150（models.py:27-55）；解梦流式元组回归 B1 本会话已修（service.py async for kind, text 解构，mock 端到端验证 PASS） |
| 2 | 安全红线 | PASS | 密钥零硬编码（全仓 grep 0 命中）；边界校验完备；provider URL 白名单 SSRF 防护；日志不泄敏；伪造 XFF 绕限流（M1）已修 |
| 3 | 性能 | PASS | 语料 lru_cache/_corpus_cache（lore.py:110, reading_agent.py:45）；限流桶 2048 淘汰（security.py:254）；chartMemoryCache（App.tsx:206） |
| 4 | 代码质量 | PASS | 零 TODO/FIXME/console.log/死代码（全仓 grep 0 命中） |
| 5 | 可维护性 | PASS | 分层清晰：fortune_core 纯算法 / api 防护中间件 / 前端视图组件；魔法数字均命名常量 |
| 6 | 架构对齐 | PASS | serve.py 挂载分层（/api + SPA）；pyproject 依赖最小集（6 运行时依赖） |
| 7 | 变更风险 | WARNING | apiBase.ts:2 PROD fallback 仍为 CloudBase 旧址——实际构建链由 .env.production 兜住（dist 实测编入 "/api"，bundle grep 证实），无当前影响，属迁移残留，建议改 "/api" |
| 8 | 需求对齐 | PASS | 本会话改动范围与用户指令一致，无蔓延 |
| 9 | 测试覆盖 | PASS | pytest verified+golden+differential 118/118 全过（141s）；本会话修复各有 mock 验证；建议为解梦流式补真协议回归测试（现 e2e mock 了该路由） |
| 10 | 技术选型 | N/A | 无新技术选型 plan |

## 内容审查（6 维）

| # | 维度 | 判定 | 关键证据 |
|---|------|------|---------|
| 1 | 设计合理性 | PASS | 签名事实上下文 + 不可信数据隔离 + 输出黑名单三层设计合理，无过度设计 |
| 2 | 可运行性 | PASS | npm run build 802ms 成功；py_compile 全过；pytest 118 过 |
| 3 | 视觉质量 | PASS | 霞鹜文楷阅读字体（非 Inter/Roboto）；task-layout.css 375px 移动断点；aria-live/role=status 无障碍标注（DreamConsole.tsx:113,123） |
| 4 | 需求完整性 | PASS | 错误态/空态/加载态（ai-progress）均有处理 |
| 5 | 一致性 | WARNING | 同代码维度 7：apiBase fallback 旧址 vs 实际部署 topology（destiny.solplum.com，nginx /api 反代） |
| 6 | 残留物 | PASS | 零占位符/TODO/console.log/mock 残留（grep 0 命中） |

## 建议项（不自动修）

1. apiBase.ts:2 PROD fallback 改 "/api"（一行，不改变当前产物行为，消除迁移残留）→ 回复 --fix 执行
2. 解梦流式补一条不经 mock 的协议回归测试
3. bundle 555KB 超过 500KB 警戒线，可选 code-split

## 结论

✅ APPROVE — 2 WARNING（同一问题，无 blocking）。门 0 通过，可进入环境与门 1。
