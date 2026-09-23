# 门0 全量静态逻辑审查报告（destiny）

- 审查日期：2026-09-23
- 审查方式：run-all 门0 全库通读静态逻辑审查（只审不修，零代码改动、零测试执行）
- 审查范围：apps/api/、src/fortune_core/、apps/observatory/src/（全库，非 diff）
- 审查基线：f08263a（HEAD）

## 结论

**blocking 2 条 / warning 7 条 / suggestion 7 条**

---

## Blocking

### B1. 问事聊天历史可整体静默消失且不可逆（写无上限 + 读整包拒绝 + 配额异常吞掉）

- 文件：`apps/observatory/src/components/DomainAnalysisConsole.tsx:220-246`（loadChat 读门槛 ：223、persistChat 写无上限 ：237-246）
- 后果链：
  1. `persistChat` 每人保留最近 40 条消息，但**对总写入量没有任何字节上限**；一轮问事 AI 回答轻松 3000-8000 字，40 条长回答单用户即可把 `fortune-ai-chat-v1` 整包推过 120,000 字符。
  2. 下次打开问事页，`loadChat` 读到整包 `raw.length > 120_000`，**直接 `return []`**——所有用户的聊天区静默变空（与"读取失败"不可区分，无任何提示）。这就是用户实测的"聊天内容消失"。
  3. 更糟的是不可逆步：用户看到空聊天后随手发一条新消息，`persistChat` 用 `parsed[owner] = messages.slice(-40)` **整槽覆盖**——该用户原有的 40 条历史被 2 条新消息替换，永久丢失（其他 owner 的槽保留但同样读不出来）。
  4. 平行的丢失路径：`persistChat` 的 `catch {}` 把 QuotaExceededError（整包逼近 5MB 配额，含多 owner 累积）静默吞掉，最新消息不落盘，刷新后凭空消失。
  5. 多 owner 无清理：`parsed` 按 owner（userId，最多 8 人）累积，旧 owner 槽永不修剪，加速触达上述两条阈值。
- 修复建议：persistChat 按字节预算（如 ≤96KB）从最旧消息起裁剪并修剪废弃 owner 槽；loadChat 超限时降级读取可解析部分而非整包拒绝；quota 异常至少提示一次。

### B2. 前端在途流注册表在 HTTP 错误/重连耗尽路径不删除条目，稳定 cacheKey 的解读面板从此永久报错、重试按钮完全失效

- 文件：`apps/observatory/src/streamReading.ts:180-188`（`!response.ok` 提前 return，未 `inflight.delete`）、`:219-226`（重连 2 次耗尽提前 return，同样未删）、对照 `:124`/`:141`（仅 handleEvent 的 done/error 事件分支会删）
- 后果链：
  1. `/v1/ai/reading` 的非 200 响应（429 额度、429 单 IP 流帽、400 上下文失效、503 未配置）走 `!response.ok` 分支：置 snapshot 为 error 后 return，**注册表条目留存**；断线重连 2 次仍失败走 `:219-226`，同样留存。
  2. 问事领域卡、今日运势卡、日历单日卡的 `AiExplainPanel` cacheKey 都是**稳定键**（`ai-v11-{owner}-{domain|date}-{zw|bz}`，见 `DomainAnalysisConsole.tsx:191`、`FortuneConsole.tsx:174`、`FortuneConsole.tsx:286`），自动挂流与"重新生成讲解"按钮用同一个 key `joinStream`。
  3. 一旦上述任一错误发生，之后再次进入该面板：`joinStream` 命中注册表里的**死错误条目**，直接返回旧 handle——不发任何网络请求，UI 永远停在同一错误态。当天额度用尽（每日必现一次 429）后，所有领域卡/运势卡/日历卡在**页面不刷新的前提下永久坏死**，重试按钮点了没有任何反应；日历上快速点击多天（每张卡一个流，单 IP 流帽 2）会批量制造这种死条目。唯一恢复手段是整页刷新。
  4. 叠加项：错误事件分支虽会删条目，但 `AiExplainPanel` 从不渲染 `snapshot.error`（见 W1），错误原因对用户不可见。
- 修复建议：`!response.ok` 与重连耗尽两处收尾时同样执行 `inflight.delete(snapshotCacheKeyOf(entry))`，与 handleEvent 的终态清理对齐。

---

## Warning

### W1. AiExplainPanel 不展示流的错误详情，失败只有一颗无文字的重试按钮

- 文件：`apps/observatory/src/components/AiExplainPanel.tsx:412`（只渲染本地 `error` state，流错误写入的是 `snapshot.error`，全文件无任何 `snapshot.error` 渲染点）
- 后果链：服务端 `{"type":"error","detail":…}`（安全红线、生成失败、空正文）到达后 phase='error'，面板既无错误文案也无失败原因，只在正文位置消失后剩"重新生成讲解"按钮；用户无法区分额度用完、内容被拦还是服务故障。解梦/奇门/中医三个 Console 均渲染了 `snapshot.error`，仅问事/运势面板漏。
- 修复建议：在错误态渲染 `snapshot.error`（沿用 DreamConsole 的 `dream-error` 样式）。

### W2. 切换用户的窗口期内发送聊天：按旧盘作答、旧用户消息串写进新用户槽

- 文件：`apps/observatory/src/components/DomainAnalysisConsole.tsx:284-359`（AiChat 的 `messages` 只在挂载时初始化，:302-304 的 aiOwner effect 只重接 turn 不重载 messages；`send()` 用当前 `chart.ai_contexts`）+ `apps/observatory/src/App.tsx:427-436`（switchUser 先换 currentUserId，新 chart 异步到达前旧 chart 仍是 prop）
- 后果链：在"问 AI"标签下切换用户 → aiOwner 立即变为新用户而 chart 仍是旧用户的 → AiChat 不重挂（组件未卸载）、messages 仍是旧用户的历史、`busy=false` 可输入 → 发出的问题携带**旧用户的 context_tokens**（按旧盘作答），收尾落定后 `persistChat(新owner, 旧用户历史+新问答)` 把旧用户的完整聊天**写入新用户的存储槽**——跨用户数据污染。
- 修复建议：aiOwner 变化时同步重载 messages 并在 chart.trace_id 与 owner 不匹配期间禁用发送。

### W3. 解梦/奇门/中医流式端点无会话注册表：前端断线重连=从零重生成，预算双倍/三倍烧且正文被另一篇替换

- 文件：`apps/observatory/src/streamReading.ts:161-230`（resetForReplay + 重发同一 body）+ `apps/api/app.py:812-867/1059-1118/1150-1205`（三个 stream 端点每次请求都重跑 `stream_*_events`，无 stream_key/回放）+ `apps/api/dreams/service.py:279`、`apps/api/qimen/service.py:110`、`apps/api/tcm/service.py:251`（每次重发都再次 `reserve_daily_budget`）
- 后果链：弱网下一次解读最多发 3 次 POST（1+2 重连）；每次都是真实新生成并各自扣日预算，且重连后 `resetForReplay` 清空本地文本、服务端新文章从零流出——用户看着已读一半的文章被换成一篇不同的文章。问事 `/v1/ai/reading` 有会话注册表（回放+续播、不重复计费），三个域端点没有，口径不一致。
- 修复建议：给三个域流式端点接入与 reading 相同的 StreamSession（或最低限度：重连仅重连不重扣）。

### W4. 流式请求先扣 AI 限流额度、后被单 IP 流帽拒绝：被拒请求白烧 6/min 配额

- 文件：`apps/api/security.py:118`（`_allow_ai_request` 在读 body 后即扣额度）→ `:168-172`（流帽检查在槽位获取后才做，被拒即 429，已扣不退）
- 后果链：单 IP 已有 2 条在途流时，第 3 条请求先消耗 1 个（split 时最多 5 个）AI 分钟配额，然后才被流帽 429。叠加前端多卡并行（W3/日历连点）与自动重连（每轮最多 3 次 POST 各扣一次），真实用户一轮弱网会话可烧掉 6-15 个/min 配额，后续请求被"AI 请求太频繁"误伤。
- 修复建议：把流帽检查提到 `_allow_ai_request` 扣费之前（按请求头/路径先判定），或被流帽拒绝时回滚本次扣减。

### W5. 输出红线子串匹配过宽，命中后整篇已生成（已计费）内容全量丢弃

- 文件：`apps/ai_explainer.py:451-471`（`注定|必然|百分之百|保证你|一定会`、`股票|基金|债券|期货|期权` 等裸子串）+ `apps/api/reading_agent.py:499-506`、`apps/api/dreams/service.py:312-317`、`apps/api/qimen/service.py:137-141`（流式收尾对全文+think 全量校验）
- 后果链：解读/聊天的正文是几千字自由文本，出现"并非必然""不必然"、"别急着买基金"这类否定/泛指用法，或引经据典带出"必然"二字，都会命中子串；此时正文已完整流给用户并已计费，收尾才判违规 → 前端按 code=safety 清空整屏只留"请换个问法"。长文命中概率不低，且用户已读到的内容被凭空抹掉。
- 修复建议：确定性断语类改为带边界/否定排除的正则（如排除"并非|不是|未必"前导），或降级为"该句隐藏"而非全文丢弃。

### W6. 起运日期落在 2 月 29 日时 `replace(year=…)` 抛 ValueError，该出生数据的排盘/运势永久 422

- 文件：`src/fortune_core/bazi/service.py:35-60`（`start_template.replace(year=decade.getStartYear())` 对非闰年目标年直接 `ValueError: day is out of range for month`）
- 后果链：若 `yun.getStartSolar()`（由出生时刻推出）恰为 2 月 29 日，则每个十年大运的 start/end 都要 `replace(year=X)`；平年抛 ValueError → `/v1/charts`、`/v1/transits/*` 全部 422"计算输入超出支持范围"，该用户永远无法排盘（错误信息还指向错误原因）。边界日期覆盖面里最尖锐的一个。
- 修复建议：replace 前对 2/29 做 clamp（落到 2/28）或改用 `datetime(year, 3, 1)` 回退规则。

### W7. 超远期流年静默落"童限"错宫：`_locate_decadal` 无年龄上限分支

- 文件：`src/fortune_core/ziwei/limits.py:95-121`（十二宫大限都查不到时兜底进童年限分支，`:111` 对 nominal_age 取 `min(age,6)-1` 钳位）+ `src/fortune_core/models.py:386-395`（TransitRequest 无"不早于生日"守卫，仅 DailyTransitRequest 有）
- 后果链：紫微大限最大覆盖约至 122-125 岁；`/v1/transits/daily` 允许 transit_date 年份到 2150，1850 年前后出生 + 查 2150 年 → nominal_age≈300，十二宫全不匹配 → 兜底当作"童限"，返回 start_age=1 的官禄/财帛宫限——静默错误数据（该接口守卫只挡了"早于生日"一侧，"超过寿限"一侧无守卫）。`/v1/transits`（TransitRequest）连"早于生日"守卫也没有，所幸该路径组件不产错数据、只是缺一致性。
- 修复建议：nominal_age 超出十二宫覆盖时显式 raise ValueError（422），与"早于生日"守卫对偶。

---

## Suggestion

### S1. AI 本机缓存写无字节上限，超过 400KB 后 readCache 整包拒绝，缓存功能整体自残

- 文件：`apps/observatory/src/components/AiExplainPanel.tsx:15-40`（readCache `raw.length > 400_000` 整包拒；writeCache 只按条数裁 48，无字节预算）
- 后果链：48 条长解读可轻松超 400KB → 之后所有缓存永远 miss，同盘同日反复重新计费生成。与 B1 同构但损失较轻（只多花钱不减数据）。
- 修复建议：writeCache 按 createdAt 序裁剪到字节预算（如 ≤320KB）。

### S2. 中医流式路径缺 3600 字正文裁剪，与非流式口径分叉

- 文件：`apps/api/tcm/service.py:242-287`（stream 无 `_fit_essay` 等价物；非流式 ：150-159 有 `_ESSAY_CAP=3600` 强裁+免责框收尾）
- 后果链：流式正文上限实际是 max_tokens 32000，可输出远超 3600 字；保存/展示口径与非流式不一致（免责框两态都有，长度只有非流式有）。
- 修复建议：流式收尾按非流式同预算裁剪（或明确放开非流式的 cap 使两态一致）。

### S3. "清空重填"不清出生日期/时间（受控下拉不受 form.reset 影响）

- 文件：`apps/observatory/src/components/BirthForm.tsx:92-100`
- 后果链：点"清空重填"后省市区/经纬度被重置，但年/月/日/时/分是受控 state，保留原值——"清空"语义不完整。
- 修复建议：clearForm 中一并 setBirthYear/Month/Day/Hour/Minute 到默认值。

### S4. 422 校验错误（detail 为数组）在流式错误提示里渲染成 "[object Object]"

- 文件：`apps/observatory/src/streamReading.ts:181-184`（`String(payload.detail)`）+ `apps/api/app.py:770-780`（validation handler 返回 detail 列表）
- 后果链：请求体校验失败（如 history 超长被 FastAPI 422）时，聊天/面板错误提示显示"[object Object]"。
- 修复建议：detail 非字符串时取 `detail[0].msg` 或回退默认文案。

### S5. RequestGuard 位于 CORS 内层之外，守卫 4xx 响应不带 CORS 头

- 文件：`apps/api/app.py:132-158`（add_middleware 顺序：TrustedHost → CORS → RequestGuard，RequestGuard 最外层）+ `apps/api/security.py:90-198`（各拒绝路径直接 `_send_json`）
- 后果链：本地 dev 跨域（5173→8000）下，429/413/503 响应被浏览器 CORS 拦截，前端只能拿到 TypeError → 显示"无法连接排盘服务"等兜底文案，掩盖真实限流原因。生产同域（/api 反代）不受影响。
- 修复建议：给 `_send_json` 的响应补 Access-Control-Allow-Origin（从配置取），或把 CORS 提到守卫外层。

### S6. 前端虚岁用浏览器本地年份、后端用北京年份，跨年附近两边大限/阶段表述可能差一岁

- 文件：`apps/observatory/src/components/DomainAnalysisConsole.tsx:79-81`、`apps/observatory/src/readingNarrative.ts:42-45`（`new Date().getFullYear()`）vs `apps/api/app.py:208-214`（`datetime.now(_BEIJING).year`）
- 后果链：海外设备在 12 月 31 日/1 月 1 日前后打开，前端 lead 文案"当前虚岁约 N，大限行 X 宫"可能与 AI facts（服务端算的当前大限）相差一岁/一宫，同一张卡两处口径打架。
- 修复建议：前端统一改用 `beijingCalendarDate()` 取年。

### S7. 重连成功后进度条在正文中间再次闪现 600ms"开始输出"

- 文件：`apps/observatory/src/components/DreamConsole.tsx:52-64`、`TcmConsole.tsx:51-63`、`QimenConsole.tsx:47-59`（phase 回到 'streaming' 即 finishProgress+setProgressVisible(true)+600ms 后隐藏）+ `apps/observatory/src/streamReading.ts:165-168`（resetForReplay 把 phase 打回 'thinking' 再回 'streaming'）
- 后果链：每次断线重连都会重放一次"进度条闪现"动画，用户已读到一半的文章上方突然弹出"开始输出"，观感像重新生成（实际上弱网重连并不罕见）。f08263a 将进度条收窄为"正文首字让位"后，这条重放路径成了该交互的残留毛边。
- 修复建议：streamReading 给 entry 记一个 hasStreamedOnce 标记，重连回到 streaming 时不再触发进度条。

---

## 已知非问题（按任务要求不重复报）

- tests/differential/test_iztro_palace_parity.py 两处非加密随机数（Mimosa 已报 low）
- chunk >500kB 构建警告

## 审查覆盖清单（实际通读文件）

**apps/api/（FastAPI 后端，17 文件全读）**
- app.py、security.py、reading_agent.py、ai_explainer.py、serve.py、main.py、chart_api.py、stable_chart_api.py
- dreams/：service.py、models.py、prompts.py、lore.py
- qimen/：service.py、models.py、prompts.py、lore.py
- tcm/：service.py、models.py、prompts.py、lore.py
- lore.py

**src/fortune_core/（排盘引擎，21 文件全读）**
- models.py、__init__.py
- bazi/：service.py、__init__.py、verified_service.py、stable_service.py
- ziwei/：palaces.py（核心段精读+全文件扫描）、limits.py、transit.py、__init__.py
- qimen/：engine.py（全 784 行）、__init__.py
- qizheng/：physical.py、traditional.py、dignities.py、four_remainders.py、houses.py、limits.py、mansions.py、__init__.py
- signals/：engine.py、__init__.py
- time_location/：apparent_solar.py、zoneinfo_adapter.py、trace.py、__init__.py
- transit/：bazi_daily.py、__init__.py

**apps/observatory/src/（React 前端，24 文件全读）**
- App.tsx、streamReading.ts、types.ts、dates.ts、terminology.ts、readingNarrative.ts、readingSystem.ts、apiBase.ts、themes.ts、main.tsx（入口转发）
- components/：DomainAnalysisConsole.tsx、AiExplainPanel.tsx、FortuneConsole.tsx、QimenConsole.tsx、TcmConsole.tsx、DreamConsole.tsx、Chart.tsx、BirthForm.tsx、ProfileView.tsx、SavedReadings.tsx、AppNavigation.tsx、ThemeRemote.tsx、MemeMedia.tsx、MemeStage.tsx、MemeCompanion.tsx

**附注**
- birthPlaces.ts（3667 行）为静态行政区划数据表，按数据表抽查（findArea 引用点）未逐行通读；vite-env.d.ts 为类型声明占位。
- f08263a 逐 hunk 审查：进度条条件收窄 + ThinkingTrace 接入三个 Console，行为自洽；引入的问题仅 S7（重连后进度条重放，属该交互与重连机制的组合残留，非该提交逻辑错误）。
- security.py 三层口径结论：并发槽/限流/超时的超时链（56s 墙钟 < 62s ai 门；流式 provider 读超时 280s < 600s 硬帽）自洽；流帽拒绝路径的槽位所有权修复（run-3）复核无泄漏；遗留口径问题见 W4、S5。

## 纪律声明

以上每条发现的 文件:行号 均为本次实际读到的代码位置；不确定之处已随条目注明（W7 的 lunar_python 年域下界行为未实测，W5 的命中率为定性推断）。本次审查未修改任何项目文件、未执行任何测试。
