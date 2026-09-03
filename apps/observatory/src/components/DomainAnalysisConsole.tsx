import { Briefcase, ChatCircleDots, Coins, FloppyDisk, Heart, Heartbeat, PaperPlaneRight, SpinnerGap, WarningCircle } from '@phosphor-icons/react'
import { useEffect, useRef, useState, useSyncExternalStore, type ComponentType, type FormEvent } from 'react'
import type { AnalysisDomain, ChartResponse, SaveDraft } from '../types'
import { analysisDomains } from '../types'
import type { ThemeConfig } from '../themes'
import { buildDomainNarrative, type NarrativeBlock } from '../readingNarrative'
import { readingSystemLabels, type ReadingSystem } from '../readingSystem'
import { AiExplainPanel, ReadingBody, ThinkingTrace } from './AiExplainPanel'
import { joinStream, streamKeyOf, type StreamHandle, type StreamSnapshot } from '../streamReading'
import { MemeCompanion } from './MemeCompanion'

type DomainResult = {
  title: string
  lead: string
  action: string
  evidence: string[]
  narrative: NarrativeBlock[]
  disclaimer?: string
}

const domainConfig: Record<AnalysisDomain, {
  palace: string
  label: string
  action: string
  icon: ComponentType<{ size?: number; weight?: 'bold' | 'fill' }>
  analysisQuestion: string
  actionQuestion: string
}> = {
  health: {
    palace: '疾厄', label: '健康', icon: Heartbeat,
    action: '把睡眠、饮食、活动量与不适记录成可复查的时间线；持续或明显不适请优先交给专业医生。',
    analysisQuestion: '请综合我的三张命盘（四柱日主、紫微疾厄宫及三方四正、七政昼夜盘庙旺恩难、当前人生阶段）写当前阶段的白话健康总论并给行动建议：①结论一句话加比喻；②当前阶段的体质与信号——先引具体盘面（如"天府（旺）在酉宫"）与当前大限行限再下结论；③2-4条行动建议，每条分为什么/怎么做/怎么算做到三层，加一条"只需记住这一条"规则。禁止泛泛人生建议，术语配白话，不涉及诊断或用药。不要写当前大限之后第 3 步及更远的运程。',
    actionQuestion: '请基于我的三张命盘（四柱日主、紫微疾厄宫及三方四正、七政昼夜盘庙旺恩难、当前人生阶段）只输出"当前阶段"的行动方案：2-4条行动建议，每条分"为什么（引用哪张盘哪个具体依据）/怎么做（本周能执行的具体动作）/怎么算做到了（可检查的信号）"三层写；最后1-2条提醒，其中一条写成"只需记住这一条"式单句规则。禁止泛泛的人生建议，每个术语第一次出现都解释成白话。不涉及任何诊断或用药。',
  },
  relationship: {
    palace: '夫妻', label: '姻缘', icon: Heart,
    action: '把沟通节奏、个人边界与冲突后的恢复方式分开观察，用真实互动校准命盘语言。',
    analysisQuestion: '请综合我的三张命盘（四柱日主、紫微夫妻宫及三方四正、七政昼夜盘庙旺恩难、当前人生阶段）写当前阶段的白话姻缘总论并给行动建议：①结论一句话加比喻；②当前阶段我在关系里的模式与卡点——先引具体盘面与当前大限行限再下结论；③2-4条行动建议，每条分为什么/怎么做/怎么算做到三层，加一条"只需记住这一条"规则。禁止泛泛人生建议，术语配白话。不要写当前大限之后第 3 步及更远的运程。',
    actionQuestion: '请基于我的三张命盘（四柱日主、紫微夫妻宫及三方四正、七政昼夜盘庙旺恩难、当前人生阶段）只输出"当前阶段"的行动方案：2-4条行动建议，每条分"为什么（引用哪张盘哪个具体依据）/怎么做（本周能执行的具体动作）/怎么算做到了（可检查的信号）"三层写；最后1-2条提醒，其中一条写成"只需记住这一条"式单句规则。禁止泛泛的人生建议，每个术语第一次出现都解释成白话。',
  },
  career: {
    palace: '官禄', label: '事业', icon: Briefcase,
    action: '把专业能力、责任边界与下一阶段作品拆开列出，先推进一个可以被验证的最小成果。',
    analysisQuestion: '请综合我的三张命盘（四柱日主、紫微官禄宫及三方四正、七政昼夜盘庙旺恩难、当前人生阶段）写当前阶段的白话事业总论并给行动建议：①结论一句话加比喻；②当前阶段的优势与坑——先引具体盘面与当前大限行限再下结论；③2-4条行动建议，每条分为什么/怎么做/怎么算做到三层，加一条"只需记住这一条"规则。禁止泛泛人生建议，术语配白话。不要写当前大限之后第 3 步及更远的运程。',
    actionQuestion: '请基于我的三张命盘（四柱日主、紫微官禄宫及三方四正、七政昼夜盘庙旺恩难、当前人生阶段）只输出"当前阶段"的行动方案：2-4条行动建议，每条分"为什么（引用哪张盘哪个具体依据）/怎么做（本周能执行的具体动作）/怎么算做到了（可检查的信号）"三层写；最后1-2条提醒，其中一条写成"只需记住这一条"式单句规则。禁止泛泛的人生建议，每个术语第一次出现都解释成白话。',
  },
  wealth: {
    palace: '财帛', label: '财运', icon: Coins,
    action: '先定义现金流、风险上限和不可承受损失，再讨论机会；命盘不能替代具体财务数据。',
    analysisQuestion: '请综合我的三张命盘（四柱日主、紫微财帛宫及三方四正、七政昼夜盘庙旺恩难、当前人生阶段）写当前阶段的白话财运总论并给行动建议：①结论一句话加比喻；②当前阶段的用钱赚钱习惯与漏财点——先引具体盘面与当前大限行限再下结论；③2-4条行动建议，每条分为什么/怎么做/怎么算做到三层，加一条"只需记住这一条"规则。命盘不替代财务数据，禁止泛泛人生建议，术语配白话。不要写当前大限之后第 3 步及更远的运程。',
    actionQuestion: '请基于我的三张命盘（四柱日主、紫微财帛宫及三方四正、七政昼夜盘庙旺恩难、当前人生阶段）只输出"当前阶段"的行动方案：2-4条行动建议，每条分"为什么（引用哪张盘哪个具体依据）/怎么做（本周能执行的具体动作）/怎么算做到了（可检查的信号）"三层写；最后1-2条提醒，其中一条写成"只需记住这一条"式单句规则。命盘不能替代具体财务数据，禁止泛泛的人生建议，每个术语第一次出现都解释成白话。',
  },
}

function buildResult(chart: ChartResponse, domain: AnalysisDomain): DomainResult {
  const config = domainConfig[domain]
  const palace = chart.ziwei.palaces.find((item) => item.name === config.palace)
  if (!palace) {
    return {
      title: `${config.label}分析暂不可用`,
      lead: `当前命盘没有返回${config.palace}宫，系统不会用其他宫位补写结论。`,
      action: '可以先展开完整命盘检查数据；若仍缺失，请重新排盘或稍后再试。',
      evidence: ['未找到对应宫位'],
      narrative: [{ label: '缺宫', text: `当前命盘没有返回${config.palace}宫，系统不会用其他宫位补写结论。` }],
    }
  }

  const majorStars = palace.major_star_brightness.length
    ? palace.major_star_brightness.map(([star, brightness]) => `${star}（${brightness}）`).join('、')
    : palace.major_stars.join('、') || '当前无主星数据'
  const minorStars = palace.minor_stars.join('、') || '当前无辅星数据'
  const palaceStars = new Set([...palace.major_stars, ...palace.minor_stars])
  const mutagens = chart.ziwei.birth_mutagens
    .filter((item) => palaceStars.has(item.star))
    .map((item) => `${item.star}化${item.mutagen}`)
  const mutagenCopy = mutagens.length ? `；同宫可追溯四化为${mutagens.join('、')}` : '；当前未检测到同宫生年四化'

  const life = chart.ziwei.palaces.find((item) => item.name === '命宫')
  const birthYear = Number(String(chart.bazi.calculation_datetime).slice(0, 4))
  const age = Number.isFinite(birthYear) ? new Date().getFullYear() - birthYear + 1 : null
  const stage = age === null ? undefined : chart.ziwei.palaces.find((item) => item.decadal_range[0] <= age && age <= item.decadal_range[1])
  const lead = [
    `日主${chart.bazi.pillars.day}，命宫在${life?.branch ?? '未知'}支。`,
    `${config.palace}宫落${palace.branch}，主星${majorStars}，辅星${minorStars}${mutagenCopy}。`,
    stage && age !== null
      ? `当前虚岁约${age}，大限行${stage.name}宫（${stage.decadal_range[0]}-${stage.decadal_range[1]}岁，${stage.branch}支）。`
      : '',
  ].filter(Boolean).join('')

  return {
    title: `${config.label} · ${config.palace}宫在${palace.branch}`,
    lead,
    action: config.action,
    narrative: buildDomainNarrative(chart, config.palace),
    evidence: [
      `${config.palace}宫 · ${palace.branch}`, `大限 ${palace.decadal_range[0]} 至 ${palace.decadal_range[1]}`,
      `主星 ${majorStars}`, `辅星 ${minorStars}`, ...(mutagens.length ? [`四化 ${mutagens.join('、')}`] : []),
    ],
    ...(domain === 'health' ? { disclaimer: '命理分析不构成诊断、治疗或用药建议。' } : {}),
  }
}

export function DomainAnalysisConsole({ chart, aiOwner, readingSystem, theme, onSave }: {
  chart: ChartResponse
  aiOwner: string
  readingSystem: ReadingSystem
  theme: ThemeConfig
  onSave: (draft: SaveDraft) => void
}) {
  const [active, setActive] = useState<AnalysisDomain | 'chat' | null>(null)
  const [results, setResults] = useState<Partial<Record<AnalysisDomain, DomainResult>>>({})

  useEffect(() => {
    setActive(null)
    setResults({})
  }, [chart?.trace_id])

  function request(domain: AnalysisDomain) {
    if (!chart) return
    setResults((current) => current[domain] ? current : { ...current, [domain]: buildResult(chart, domain) })
    setActive(domain)
  }

  const domainActive = active !== null && active !== 'chat' ? active : null
  const result = domainActive ? results[domainActive] : null
  const activeConfig = domainActive ? domainConfig[domainActive] : null
  // 紫微/八字分开解读：同一个领域点击即发两条并行流（紫微节 / 八字节）。
  const ziweiSource = result && domainActive && activeConfig ? {
    kind: 'domain' as const,
    key: `${chart.trace_id}-${domainActive}-zw`,
    title: `${activeConfig.label} · 紫微`,
    summary: result.lead,
    facts: chart.ai_contexts[domainActive]?.facts
      ?? [...(chart.ai_contexts.ziwei?.facts ?? [])],
    contextTokens: [
      chart.ai_contexts[domainActive]?.token,
      chart.ai_contexts.ziwei?.token,
    ].filter((token): token is string => Boolean(token)),
  } : null
  const baziSource = result && domainActive && activeConfig ? {
    kind: 'domain' as const,
    key: `${chart.trace_id}-${domainActive}-bz`,
    title: `${activeConfig.label} · 八字`,
    summary: result.lead,
    facts: [...(chart.ai_contexts.bazi?.facts ?? [])],
    contextTokens: [
      chart.ai_contexts.bazi?.token,
    ].filter((token): token is string => Boolean(token)),
  } : null
  // 全局解读体系偏好：点击领域只渲染选定体系的一张批解卡；
  // 缓存键仍按体系分开（-zw/-bz），切回来可秒读已生成的那份。
  const activeSource = readingSystem === 'ziwei' ? ziweiSource : baziSource
  const activeSuffix = readingSystem === 'ziwei' ? 'zw' : 'bz'

  return <section className="analysis-section" id="analysis">
    <div className="domain-console is-ready">
      <div className="domain-choices" role="group" aria-label="选择专项分析">
        {analysisDomains.map(([domain, label]) => {
          const Icon = domainConfig[domain].icon
          return <button
            key={domain}
            type="button"
            className={active === domain ? 'is-active' : ''}
            aria-pressed={active === domain}
            onClick={() => request(domain)}
          >
            <Icon size={20} weight={active === domain ? 'fill' : 'bold'} />
            <span>{label}</span>
          </button>
        })}
        <button
          type="button"
          className={active === 'chat' ? 'is-active is-chat' : 'is-chat'}
          aria-pressed={active === 'chat'}
          onClick={() => setActive('chat')}
        >
          <ChatCircleDots size={20} weight={active === 'chat' ? 'fill' : 'bold'} />
          <span>问 AI</span>
        </button>
      </div>

      <div className="domain-output" aria-live="polite">
        {active === 'chat' && <AiChat chart={chart} aiOwner={aiOwner} readingSystem={readingSystem} />}
        {!result && active !== 'chat' && <div className="feature-empty"><span>选择一个领域看 AI 解读，或直接和 AI 聊你的盘。</span></div>}
        {result && activeConfig && domainActive && <article className="domain-reading">
          <MemeCompanion theme={theme} />
          <header><span>{activeConfig.label}</span><h3>{result.title}</h3></header>
          <p className="domain-lead">{result.lead}</p>
          {activeSource && activeConfig && <AiExplainPanel
            auto
            cacheKey={`ai-v11-${aiOwner ?? 'anon'}-${domainActive}-${chart.trace_id}-${activeSuffix}`}
            heading={`${activeConfig.label} · ${readingSystemLabels[readingSystem]}批解`}
            source={activeSource}
            defaultQuestion={readingSystem === 'ziwei'
              ? `结合紫微斗数命盘，详细批解我的${activeConfig.label}：先给总纲，再按宫、星、四化分节深入，引原典，结尾给「可以先做」与「注意」。`
              : `结合子平八字命盘，详细批解我的${activeConfig.label}：先给总纲，再按四柱、十神、大运分节深入，引原典，结尾给「可以先做」与「注意」。`}
          />}
          <details className="fact-details"><summary>查看命盘依据与规则建议</summary>
            <p>{result.lead}</p>
            <blockquote>{result.action}</blockquote>
            {result.disclaimer && <p className="domain-disclaimer">{result.disclaimer}</p>}
            <div className="evidence-list" aria-label="分析依据">{result.evidence.map((item) => <span key={item}>{item}</span>)}</div>
          </details>
          <footer>
            <button type="button" onClick={() => onSave({
              kind: 'domain', title: result.title, summary: result.lead,
              details: [result.action, ...result.evidence],
            })}><FloppyDisk size={18} weight="bold" /> 保存这项分析</button>
          </footer>
        </article>}
      </div>
    </div>
  </section>
}

type ChatMessage = { role: 'user' | 'assistant'; text: string; actions?: string[]; ts: number }
const CHAT_KEY = 'fortune-ai-chat-v1'
const quickQuestions = ['我最近事业上该注意什么？', '我的姻缘模式是什么样的？', '帮我看看适合我的攒钱习惯']

function loadChat(owner: string): ChatMessage[] {
  try {
    const raw = window.localStorage.getItem(CHAT_KEY)
    if (!raw || raw.length > 120_000) return []
    const parsed = JSON.parse(raw) as Record<string, unknown>
    const list = parsed[owner]
    if (!Array.isArray(list)) return []
    return list.filter((item): item is ChatMessage => Boolean(
      item && typeof item === 'object'
      && (item.role === 'user' || item.role === 'assistant')
      && typeof item.text === 'string',
    )).slice(-40)
  } catch {
    return []
  }
}

function persistChat(owner: string, messages: ChatMessage[]) {
  try {
    const raw = window.localStorage.getItem(CHAT_KEY)
    const parsed = raw ? JSON.parse(raw) as Record<string, ChatMessage[]> : {}
    parsed[owner] = messages.slice(-40)
    window.localStorage.setItem(CHAT_KEY, JSON.stringify(parsed))
  } catch {
    // Chat history is best-effort; the conversation continues in memory.
  }
}

// Route the question to the relevant domain tokens: a full 4-domain prompt
// overflows the provider budget, so pick by keyword and default to two.
const domainKeywords: Array<[AnalysisDomain, RegExp]> = [
  ['health', /健康|身体|病|睡眠|作息|压力/],
  ['relationship', /姻缘|感情|婚|恋|伴侣|爱|另一半/],
  ['career', /事业|工作|职业|跳槽|升职|上班/],
  ['wealth', /财|钱|投资|攒|赚|消费/],
]

function pickTokens(question: string, contexts: ChartResponse['ai_contexts'], system: ReadingSystem): string[] {
  const hits = domainKeywords.filter(([, pattern]) => pattern.test(question)).map(([domain]) => domain)
  const chosen: AnalysisDomain[] = hits.length > 0 && hits.length <= 2 ? hits : ['career', 'relationship']
  // 按解读体系偏好路由：紫微带领域宫+紫微全盘；八字只带四柱大运——
  // 领域宫事实是紫微宫位口径，八字语境混入会造成术语串门。
  if (system === 'bazi') {
    return [contexts.bazi?.token].filter((token): token is string => Boolean(token))
  }
  return [
    ...chosen.map((domain) => contexts[domain]?.token),
    contexts.ziwei?.token,
  ].filter((token): token is string => Boolean(token))
}

// 在途聊天轮次：模块级注册表（key=aiOwner）。切走标签页组件卸载后生成继续
// （fetch 活在共享注册表里，连接不断、后端照常出字），切回来无缝重接——
// 问题气泡、真实进度、流式正文都在。done 后等打字机放完才落定写入消息列表。
type ChatTurn = {
  question: string
  userTs: number
  handle: StreamHandle
  settled: boolean
}
const chatTurns = new Map<string, ChatTurn>()
const noopSubscribe = () => () => {}
const chatEmptySnapshot: StreamSnapshot = { text: '', displayText: '', thinkText: '', phase: 'idle', startedAt: 0 }

function AiChat({ chart, aiOwner, readingSystem }: { chart: ChartResponse; aiOwner: string; readingSystem: ReadingSystem }) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadChat(aiOwner))
  const [input, setInput] = useState('')
  const [turn, setTurn] = useState<ChatTurn | null>(() => chatTurns.get(aiOwner) ?? null)
  const [error, setError] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement | null>(null)
  // 用户上滚回读时暂停吸底，滚回底部附近自动恢复。
  const stickBottomRef = useRef(true)
  const hasAnyToken = Object.values(chart.ai_contexts).some((bundle) => bundle.token)

  const snapshot = useSyncExternalStore(
    turn ? turn.handle.subscribe : noopSubscribe,
    turn ? turn.handle.getSnapshot : () => chatEmptySnapshot,
  )
  const phase = snapshot.phase
  const busy = turn !== null

  // 重挂/换用户重接在途轮次。
  useEffect(() => {
    setTurn(chatTurns.get(aiOwner) ?? null)
  }, [aiOwner])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  // 流式期间吸底跟随：用瞬时滚动（smooth 动画跟不上逐字速度）。
  useEffect(() => {
    if (!turn || !stickBottomRef.current) return
    const el = listRef.current
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'auto' })
  }, [turn, snapshot.displayText])

  // 收尾落定：done 后等打字机把 displayText 放完才写入消息列表并持久化；
  // error（含 HTTP 非 200、内容安全、连接中断）立即落定只报错。
  useEffect(() => {
    if (!turn || turn.settled) return
    if (phase !== 'done' && phase !== 'error') return
    if (phase === 'done' && snapshot.displayText.length < snapshot.text.length) return
    turn.settled = true
    chatTurns.delete(aiOwner)
    setTurn(null)
    if (phase === 'done' && snapshot.text.trim()) {
      const userMessage: ChatMessage = { role: 'user', text: turn.question, ts: turn.userTs }
      const assistantMessage: ChatMessage = { role: 'assistant', text: snapshot.text, ts: Date.now() }
      const next = [...messages, userMessage, assistantMessage]
      setMessages(next)
      persistChat(aiOwner, next)
    } else if (phase === 'error') {
      setError(snapshot.error || 'AI 这次没有回复。')
    } else {
      setError('AI 回复为空，请重试。')
    }
  }, [turn, phase, snapshot, messages, aiOwner])

  function send(question: string) {
    const clean = question.trim().slice(0, 300)
    const tokens = pickTokens(clean, chart.ai_contexts, readingSystem)
    if (!clean || busy || !tokens.length) return
    setError(null)
    setInput('')
    stickBottomRef.current = true
    const userTs = Date.now()
    const history = [...messages, { role: 'user' as const, text: clean }]
      .slice(-12)
      .map((item) => ({ role: item.role, text: item.text.slice(0, 600) }))
    const handle = joinStream(`chat-${aiOwner}-${userTs}`, '/v1/ai/reading', {
      question: clean,
      context_tokens: tokens,
      history,
      stream_key: streamKeyOf('chat', aiOwner, String(userTs)),
    })
    const next: ChatTurn = { question: clean, userTs, handle, settled: false }
    chatTurns.set(aiOwner, next)
    setTurn(next)
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void send(input)
  }

  if (!hasAnyToken) {
    return <div className="feature-empty"><span>当前命盘还没有可用的核验上下文，重新排盘后再来聊。</span></div>
  }

  const thinking = turn && phase === 'thinking'

  return <div className="ai-chat">
    <div
      className="chat-list" ref={listRef}
      aria-label="与 AI 的对话"
      onScroll={() => {
        const el = listRef.current
        if (el) stickBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48
      }}
    >
      {messages.length === 0 && !turn && <div className="chat-empty">
        <ChatCircleDots size={34} weight="bold" />
        <div><strong>和 AI 聊聊你的盘</strong><p>每轮回答都基于你命盘的核验事实；对话记录只存在这台设备上。</p></div>
        <div className="chat-quick">{quickQuestions.map((item) => <button key={item} type="button" onClick={() => void send(item)}>{item}</button>)}</div>
      </div>}
      {messages.map((message) => message.role === 'user'
        ? <div className="chat-msg is-user" key={message.ts}><p>{message.text}</p></div>
        : <div className="chat-msg is-assistant is-doc" key={message.ts}>
            <ReadingBody text={message.text} />
            {message.actions && message.actions.length > 0 && <ul>{message.actions.map((action) => <li key={action}>{action}</li>)}</ul>}
          </div>)}
      {turn && <div className="chat-msg is-user"><p>{turn.question}</p></div>}
      {turn && thinking && <div className="chat-msg is-assistant is-thinking">
        <ThinkingTrace text={snapshot.thinkText} active startedAt={snapshot.startedAt} />
      </div>}
      {turn && phase === 'streaming' && <div className="chat-msg is-assistant is-doc is-streaming">
        <ReadingBody text={snapshot.displayText} />
        <p className="chat-writing" aria-live="polite" role="status"><SpinnerGap className="spin" size={14} /> 生成中…</p>
      </div>}
      {turn && phase === 'done' && <div className="chat-msg is-assistant is-doc is-streaming">
        <ReadingBody text={snapshot.displayText} />
      </div>}
      {error && !busy && <p className="ai-answer-error" role="alert"><WarningCircle size={18} weight="bold" />{error}</p>}
    </div>
    <form className="chat-input" onSubmit={submit}>
      <textarea
        value={input}
        rows={2}
        maxLength={300}
        placeholder="问点什么，比如：我换工作的时机怎么看？"
        disabled={busy}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send(input) } }}
      />
      <button type="submit" disabled={busy || !input.trim()} aria-label="发送">
        {busy ? <SpinnerGap className="spin" size={19} /> : <PaperPlaneRight size={19} weight="fill" />}
      </button>
    </form>
  </div>
}
