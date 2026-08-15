import { Briefcase, ChatCircleDots, Coins, FloppyDisk, Heart, Heartbeat, PaperPlaneRight, SpinnerGap, WarningCircle } from '@phosphor-icons/react'
import { useEffect, useRef, useState, type ComponentType, type FormEvent } from 'react'
import type { AnalysisDomain, AiExplainResponse, ChartResponse, SaveDraft } from '../types'
import { analysisDomains } from '../types'
import { AiExplainPanel } from './AiExplainPanel'

type DomainResult = {
  title: string
  lead: string
  action: string
  evidence: string[]
  disclaimer?: string
}

const domainConfig: Record<AnalysisDomain, {
  palace: string
  label: string
  action: string
  icon: ComponentType<{ size?: number; weight?: 'bold' | 'fill' }>
  question: string
}> = {
  health: {
    palace: '疾厄', label: '健康', icon: Heartbeat,
    action: '把睡眠、饮食、活动量与不适记录成可复查的时间线；持续或明显不适请优先交给专业医生。',
    question: '请基于我的疾厄宫星情，用白话讲讲我日常最该留意的身体信号和生活习惯（不涉及任何诊断或用药），并给一条今天就能做的小改变。',
  },
  relationship: {
    palace: '夫妻', label: '姻缘', icon: Heart,
    action: '把沟通节奏、个人边界与冲突后的恢复方式分开观察，用真实互动校准命盘语言。',
    question: '请基于我的夫妻宫星情，用白话讲讲我在亲密关系里的天然模式和最值得练习的一件事。',
  },
  career: {
    palace: '官禄', label: '事业', icon: Briefcase,
    action: '把专业能力、责任边界与下一阶段作品拆开列出，先推进一个可以被验证的最小成果。',
    question: '请基于我的官禄宫星情，用白话讲讲我的职业优势、容易踩的坑，以及下一步最值得先做的一件事。',
  },
  wealth: {
    palace: '财帛', label: '财运', icon: Coins,
    action: '先定义现金流、风险上限和不可承受损失，再讨论机会；命盘不能替代具体财务数据。',
    question: '请基于我的财帛宫星情，用白话讲讲我的财务性格（不涉及任何具体投资建议），并给一条管钱的小原则。',
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

  return {
    title: `${config.label} · ${config.palace}宫在${palace.branch}`,
    lead: `主星：${majorStars}；辅星：${minorStars}${mutagenCopy}。`,
    action: config.action,
    evidence: [
      `${config.palace}宫 · ${palace.branch}`, `大限 ${palace.decadal_range[0]} 至 ${palace.decadal_range[1]}`,
      `主星 ${majorStars}`, `辅星 ${minorStars}`, ...(mutagens.length ? [`四化 ${mutagens.join('、')}`] : []),
    ],
    ...(domain === 'health' ? { disclaimer: '命理分析不构成诊断、治疗或用药建议。' } : {}),
  }
}

export function DomainAnalysisConsole({ chart, aiOwner, onSave }: {
  chart: ChartResponse
  aiOwner: string
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
          <header><span>{activeConfig.label}</span><h3>{result.title}</h3></header>
          <AiExplainPanel
            auto
            cacheKey={`ai-${aiOwner}-${domainActive}`}
            source={{
              key: `${chart.trace_id}-${domainActive}`,
              kind: 'domain',
              title: result.title,
              summary: result.lead,
              facts: chart.ai_contexts[domainActive]?.facts
                ?? result.evidence.map((text, index) => ({ id: `domain-${index + 1}`, text })),
              contextTokens: chart.ai_contexts[domainActive] ? [chart.ai_contexts[domainActive].token] : [],
            }}
            defaultQuestion={activeConfig.question}
          />
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
  const [error, setError] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement | null>(null)
  const hasAnyToken = Object.values(chart.ai_contexts).some((bundle) => bundle.token)

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, isLoading])

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
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE ?? (import.meta.env.PROD ? 'https://sol-d2ga5fpq8bcf67f5a.service.tcloudbase.com/destiny' : 'http://127.0.0.1:8000')}/v1/ai/explain`, {
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
      {isLoading && <div className="chat-msg is-assistant is-typing" role="status"><SpinnerGap className="spin" size={18} /> AI 正在结合你的盘思考…</div>}
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
