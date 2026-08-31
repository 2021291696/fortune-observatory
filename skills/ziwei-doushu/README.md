# ziwei-doushu skill

紫微斗数排盘与解读 skill（倪海厦《天纪》三合派口径），destiny 项目三端 CLI skill 之一。

## 来源与许可

- 上游：https://github.com/Renhuai123/ziwei-doushu （MIT License）
- 上游 commit：`88194a404242bfe5c6d5cc512e4117e3e245cdd5`（2026-06-24）
- 底层排盘：[iztro](https://github.com/SylarLong/iztro) 2.5.8（MIT）
- 本目录 `vendor/` 与上游逐字一致（仅行尾符差异），上游功能未做任何修改

## 目录结构

```
SKILL.md            # skill 入口（触发词/流程/CLI 用法）
README.md           # 本文件
package.json        # 运行依赖：iztro、lunar-javascript；开发依赖：tsx
vendor/             # 上游引擎源码（algorithm/constants/types/patterns/sihua + classics 古籍数据）
scripts/pai_pan.ts  # 排盘 CLI（十二宫/大限/四化/格局/流年）
scripts/dump_refs.ts# references 生成器（从 vendor 数据再生成，勿手改产物）
references/         # classics.md / patterns.md / sihua-tables.md（生成产物）
```

## 安装与使用

```bash
cd skills/ziwei-doushu
npm install                      # 首次
npx tsx scripts/pai_pan.ts --solar 1990-05-15 --shichen 午 --sex 男
```

## 三端部署（junction 反挂）

实体在本仓库（单一数据源），三端经 `~/.agents/skills` junction 链接入：

```
~/.agents/skills/ziwei-doushu  → D:\MyAIWorkspace\project\destiny\skills\ziwei-doushu   (junction)
~/.claude/skills/ziwei-doushu  → ~/.agents/skills/ziwei-doushu                          (junction)
~/.codex/skills/ziwei-doushu   → ~/.agents/skills/ziwei-doushu                          (junction)
ZCode 直读 ~/.agents/skills/
```

创建 junction（PowerShell，Git Bash 的 mklink 会被 MSYS 参数转换搅坏）：

```powershell
New-Item -ItemType Junction -Path "$env:USERPROFILE\.agents\skills\ziwei-doushu" -Value "D:\MyAIWorkspace\project\destiny\skills\ziwei-doushu"
```

## 更新 references

vendor/ 数据变更后重新生成（产物勿手改）：

```bash
npx tsx scripts/dump_refs.ts
```
