# dream-interpretation — 荣格取向解梦 skill（destiny 实体）

看运项目的解梦能力口径源。以 [FreedomIntelligence/OpenClaw-Medical-Skills](https://github.com/FreedomIntelligence/OpenClaw-Medical-Skills)（2977★，2026-08 快照）的 `jungian-psychologist` skill 为原版，做中文化改造后收入本仓库。

## 与原版的差异

- SKILL.md 全文中文重写：解梦为核心场景，阴影工作/积极想象/视觉映射为延伸探索
- 收束流程（解梦后两道选择 → 梦档/知识库/笔记写入）与安全分流沿用本项目早期解梦实践的成熟约定
- 核心参考已中文化：`references/dream-interpretation.md`（解梦方法）、`references/psyche-structure.md`（心灵结构）、`references/symbol-dictionary.md`（象征词典，101 条）、`examples/dream-interpretation-session.md`
- 外围参考保留英文原样：clinical-frameworks、active-imagination、addiction-recovery、visual-mapping、skill-integrations
- 上游仓库未声明 LICENSE，内容原样收录；本仓库内文件随 destiny 主仓库分发

## 历史

- 2026-08-31：收录并中文化；同日移除 `apps/api/dreams` 服务端解梦链路（模块/端点/语料/向量库/测试/前端解梦视图），解梦能力由本 skill 承担
