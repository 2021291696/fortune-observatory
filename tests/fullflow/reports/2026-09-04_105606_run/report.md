# 全流程测试报告 — destiny-解梦常驻视图切换UI回归

- 门：**ui**　起止：2026-09-04T10:56:27+08:00 → 2026-09-04T10:56:27+08:00
- 结果：❌ RED×1　（共 1 条 run，合计 20.9s）
- 清单：`D:\MyAIWorkspace\project\destiny\tests\fullflow\manifest.ui.yaml`

## Run 矩阵

| run | 类型 | 状态 | 耗时 | 失败点 | 说明 |
|---|---|---|---|---|---|
| base | normal | ❌ RED | 20945ms | ui_open_site | 步骤 ui_open_site: UI 动作 goto 异常: TimeoutError: Page.goto: Timeout 20000ms exceeded.
Call log:
  - navigating to "https:// |

## 失败明细

### base

- ❌ `ui_open_site`（20020ms）UI 动作 goto 异常: TimeoutError: Page.goto: Timeout 20000ms exceeded.
Call log:
  - navigating to "https://destiny.solplum.com/", waiting until "load"

- 变量：`{"dream_text": "梦见深夜回到小学教室，桌椅都变得特别小，黑板上写满了我看不懂的公式，我想擦掉它们，越擦黑板越黑，最后一盏日光灯开始一闪一闪"}`

## 根因分析

（AI 在此补：综合 diag.md 线索 + 失败明细，给根因假设与修复建议，用人话写）
