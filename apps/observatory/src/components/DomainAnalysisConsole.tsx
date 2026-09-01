import { Briefcase, ChatCircleDots, Coins, FloppyDisk, Heart, Heartbeat, PaperPlaneRight, SpinnerGap, WarningCircle } from '@phosphor-icons/react'
import { useEffect, useRef, useState, type ComponentType, type FormEvent } from 'react'
import type { AnalysisDomain, AiExplainResponse, ChartResponse, SaveDraft } from '../types'
import { analysisDomains } from '../types'
import { API_BASE } from '../apiBase'
import type { ThemeConfig } from '../themes'
import { buildDomainNarrative, type NarrativeBlock } from '../readingNarrative'
import { DomainEssay } from './DomainEssay'
import { MemeCompanion } from './MemeCompanion'
import { chartAge, pastQuestion, nowQuestion, upcomingQuestion } from '../lifePhase'

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

export function DomainAnalysisConsole({ chart, aiOwner, theme, onSave }: {
  chart: ChartResponse
  aiOwner: string
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
  const age = domainActive ? chartAge(chart.bazi.calculation_datetime) : null
  const palaces = chart.ziwei.palaces
  const pastQ = domainActive && age != null ? pastQuestion(palaces, age, domainActive) : null
  const nowQ = domainActive && age != null ? nowQuestion(palaces, age, domainActive) : null
  const nextQ = domainActive && age != null ? upcomingQuestion(palaces, age, domainActive) : null
  const domainSource = result && domainActive ? {
    kind: 'domain' as const,
    summary: result.lead,
    facts: chart.ai_contexts[domainActive]?.facts
      ?? result.evidence.map((text, index) => ({ id: `domain-${index + 1}`, text })),
    contextTokens: chart.ai_contexts[domainActive] ? [chart.ai_contexts[domainActive].token] : [],
  } : null

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
        {active === 'chat' && <AiChat chart={chart} aiOwner={aiOwner} />}
        {!result && active !== 'chat' && <div className="feature-empty"><span>选择一个领域看 AI 解读，或直接和 AI 聊你的盘。</span></div>}
        {result && activeConfig && domainActive && <article className="domain-reading">
          <MemeCompanion theme={theme} />
          <header><span>{activeConfig.label}</span><h3>{result.title}</h3></header>
          <p className="domain-lead">{result.lead}</p>
          {domainSource && nowQ && <DomainEssay
            source={{ ...domainSource, key: `${chart.trace_id}-${domainActive}` }}
            sections={[
              ...(pastQ ? [{
                id: 'past' as const,
                heading: '已走过大限',
                question: pastQ,
                cacheKey: `ai-${aiOwner}-${domainActive}-past-${chart.trace_id}`,
              }] : []),
              {
                id: 'now',
                heading: '当前大限',
                question: nowQ,
                cacheKey: `ai-${aiOwner}-${domainActive}-now-${chart.trace_id}`,
              },
              ...(nextQ ? [{
                id: 'next' as const,
                heading: '接下来两限',
                question: nextQ,
                cacheKey: `ai-${aiOwner}-${domainActive}-next-${chart.trace_id}`,
              }] : []),
            ]}
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

function pickTokens(question: string, contexts: ChartResponse['ai_contexts']): string[] {
  const hits = domainKeywords.filter(([, pattern]) => pattern.test(question)).map(([domain]) => domain)
  const chosen: AnalysisDomain[] = hits.length > 0 && hits.length <= 2 ? hits : ['career', 'relationship']
  return chosen.map((domain) => contexts[domain]?.token).filter((token): token is string => Boolean(token))
}

function AiChat({ chart, aiOwner }: { chart: ChartResponse; aiOwner: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadChat(aiOwner))
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement | null>(null)
  const progressTimer = useRef<number | null>(null)
  const hasAnyToken = Object.values(chart.ai_contexts).some((bundle) => bundle.token)

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, isLoading])

  useEffect(() => () => {
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
  }, [])

  function startChatProgress() {
    setProgress(0)
    const startedAt = Date.now()
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
    progressTimer.current = window.setInterval(() => {
      setProgress(Math.min(96, Math.round(100 * (1 - Math.exp(-(Date.now() - startedAt) / 7000)))))
    }, 150)
  }

  function finishChatProgress() {
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
    progressTimer.current = null
    setProgress(100)
  }

  async function send(question: string) {
    const clean = question.trim().slice(0, 300)
    const tokens = pickTokens(clean, chart.ai_contexts)
    if (!clean || isLoading || !tokens.length) return
    setError(null)
    setInput('')
    const userMessage: ChatMessage = { role: 'user', text: clean, ts: Date.now() }
    const history = [...messages, userMessage].slice(-12).map((item) => ({ role: item.role, text: item.text.slice(0, 600) }))
    setMessages((current) => [...current, userMessage])
    setIsLoading(true)
    startChatProgress()
    try {
      const response = await fetch(`${API_BASE}/v1/ai/explain`, {
        method: 'POST',
        headers: { accept: 'application/json', 'content-type': 'application/json' },
        body: JSON.stringify({ question: clean, context_tokens: tokens, history }),
        credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer',
      })
      const body: unknown = await response.json().catch(() => null)
      if (!response.ok) {
        const detail = body && typeof body === 'object' && 'detail' in body
          ? String((body as { detail?: unknown }).detail).slice(0, 180)
          : 'AI 这次没有回复。'
        throw new Error(detail)
      }
      const answer = body as AiExplainResponse
      if (!answer?.summary?.text) throw new Error('AI 回复格式不完整，请重试。')
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        text: answer.summary.text,
        actions: answer.actions.map((item) => item.text).slice(0, 4),
        ts: Date.now(),
      }
      const next = [...messages, userMessage, assistantMessage]
      setMessages(next)
      persistChat(aiOwner, next)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'AI 这次没有回复。')
      setMessages((current) => current.filter((item) => item.ts !== userMessage.ts))
    } finally {
      finishChatProgress()
      setIsLoading(false)
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void send(input)
  }

  if (!hasAnyToken) {
    return <div className="feature-empty"><span>当前命盘还没有可用的核验上下文，重新排盘后再来聊。</span></div>
  }

  return <div className="ai-chat">
    <div className="chat-list" ref={listRef} aria-label="与 AI 的对话">
      {messages.length === 0 && <div className="chat-empty">
        <ChatCircleDots size={34} weight="bold" />
        <div><strong>和 AI 聊聊你的盘</strong><p>每轮回答都基于你命盘的核验事实；对话记录只存在这台设备上。</p></div>
        <div className="chat-quick">{quickQuestions.map((item) => <button key={item} type="button" onClick={() => void send(item)}>{item}</button>)}</div>
      </div>}
      {messages.map((message) => message.role === 'user'
        ? <div className="chat-msg is-user" key={message.ts}><p>{message.text}</p></div>
        : <div className="chat-msg is-assistant" key={message.ts}>
            <p>{message.text}</p>
            {message.actions && message.actions.length > 0 && <ul>{message.actions.map((action) => <li key={action}>{action}</li>)}</ul>}
          </div>)}
      {isLoading && <div className="chat-msg is-assistant is-typing" role="status" aria-label={`AI 正在思考，进度 ${progress}%`}>
        <SpinnerGap className="spin" size={18} />
        <span>AI 正在结合你的盘思考… {progress}%</span>
        <div className="ai-progress-line"><i style={{ width: `${progress}%` }} /></div>
      </div>}
      {error && <p className="ai-answer-error" role="alert"><WarningCircle size={18} weight="bold" />{error}</p>}
    </div>
    <form className="chat-input" onSubmit={submit}>
      <textarea
        value={input}
        rows={2}
        maxLength={300}
        placeholder="问点什么，比如：我换工作的时机怎么看？"
        disabled={isLoading}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void send(input) } }}
      />
      <button type="submit" disabled={isLoading || !input.trim()} aria-label="发送">
        {isLoading ? <SpinnerGap className="spin" size={19} /> : <PaperPlaneRight size={19} weight="fill" />}
      </button>
    </form>
  </div>
}
