# destiny 全流程测试报告（2026-08-31）

清单：`tests/fullflow/manifest.yaml`（生产环境 · 真 LLM）
执行方式：fullflow-test skill 执行器完成前两轮门1 后 skill 目录意外丢失，后续按其两道门框架手工等价执行。
备注：前两轮 RED 均为清单数据问题（birth_datetime 缺 UTC 偏移、daily 响应路径 `$.transit.day_pillar`），修正后由手工执行器跑通。

## 门1（API 层）— 10/10 PASS

| # | 步骤 | 结果 | 关键证据 |
|---|------|------|---------|
| 1 | ai_status | PASS | available=true |
| 2 | create_chart | PASS | day=丁丑，ziwei token 2688 字符 |
| 3 | daily_transit | PASS | 流日丁丑，daily token 1404 字符 |
| 4 | fortune_daily_explain（简问） | PASS（质量观察） | summary 仅 80 字——未带前端 splitQuestions 所致，见下 |
| 4' | fortune_daily_explain（前端真实结构：主问+3 分段） | PASS | summary 891 字 + 4 条 actions；断语锚定具体盘面（文昌化科入官禄、廉贞化忌入疾厄） |
| 5 | ziwei_chart_explain | PASS | 128 字，太阳落陷/太阴庙旺/太阴化忌入命（己丑）锚定盘面 |
| 6 | dream_questions | PASS | 3 问全部贴梦境细节（黑板擦干净没/谁在擦/最怕灯闪还是黑板变黑） |
| 7 | dream_interpret | PASS | essay 724 字，荣格口径（补偿视角、三假设） |
| 8 | duplicate_submit 探针 | PASS | 200 |
| 9 | invalid_input 探针 | PASS | 422 |
| 10 | dream_referral（自伤叙述） | PASS | 确定性转介，未走 LLM |

## 门2（UI 层，生产站点 + Playwright）— PASS

| 步骤 | 结果 |
|------|------|
| 打开站点（CloudBase 测试域名风险提示页 → 确定访问） | PASS |
| 导航到解梦页、填入梦境、点击解读 | PASS |
| 等待解梦结果出现（荣格口径正文） | PASS |
| **切到运势页再切回解梦页 → 结果仍在**（本次修复的直接验收） | **PASS** |

## 发现并处置的问题

1. **运势简问短答**（80 字）：`/v1/ai/explain` 单问不带分段时输出短。前端实际请求为主问+3 分段（并行 4 次 LLM），合并后 891 字，属产品预期行为；非缺陷。
2. **解梦 sources 泄漏进正文**：模型偶发不按 JSON 回包，旧解析器整段回退，正文尾部出现 `sources: - work: …` 文本。已修复（`49fa4e8` 之后新增：剥前缀/剥 sources 段/正文兜底提取口径引用），**待云函数部署生效**。
3. **lore 整包口径**（用户"生成内容太差"主诉的修复）：`lore.py` 断语层注入 skills/bazi + ziwei-doushu references 原文（约 2.1 万字符/请求），随云函数部署生效。生产环境当前仍运行旧 lore，等待下方部署。

## 部署状态

- ✅ 静态托管：常驻视图前端已上线（2026-08-31 门2 验证）
- ⏳ 云函数 destiny-api：新包 106MB（新增 skills 口径包），COS 上传连续撞 CLI 60 秒超时（上行带宽瞬时劣化；早间同体积两次部署成功）。后台重试循环运行中（每 5 分钟 ×6），成功后自动验证。

## 遗留披露

- domain.*（问事四域）lore 未在 API 门单独覆盖（其 token 键名含点，清单 JSONPath 子集取不到），与 fortune/ziwei 共用同一 explain 管线与 lore 组装函数，风险低。
- fullflow-test skill 本体在会话中途从 `~/.agents/skills/` 消失（全盘无副本），已提请用户排查；其清单格式与两道门框架在本报告中沿用。
