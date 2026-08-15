import { ChatCircleDots, CheckCircle, Info, LockKey, SpinnerGap, WarningCircle } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import type { AiExplainResponse, AiExplainSource } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE ?? (import.meta.env.PROD
  ? 'https://sol-d2ga5fpq8bcf67f5a.service.tcloudbase.com/destiny'
  : 'http://127.0.0.1:8000')
const DEFAULT_QUESTION = '请把这段结果讲得更直白，并告诉我最值得先做的一件事。'
const AI_CACHE_KEY = 'fortune-ai-cache-v1'
const AI_CACHE_TTL_MS = 24 * 60 * 60 * 1000

type Availability = 'idle' | 'checking' | 'available' | 'unavailable' | 'error'

type CacheEntry = { answer: AiExplainResponse; createdAt: number }

function readCache(key: string): CacheEntry | null {
  try {
    const raw = window.localStorage.getItem(AI_CACHE_KEY)
    if (!raw || raw.length > 200_000) return null
    const parsed = JSON.parse(raw) as Record<string, unknown>
    const entry = parsed[key] as CacheEntry | undefined
    if (!entry || typeof entry.createdAt !== 'number' || Date.now() - entry.createdAt > AI_CACHE_TTL_MS) return null
    return entry.answer ? entry : null
  } catch {
    return null
  }
}

function writeCache(key: string, answer: AiExplainResponse) {
  try {
    const raw = window.localStorage.getItem(AI_CACHE_KEY)
    const parsed = raw ? JSON.parse(raw) as Record<string, CacheEntry> : {}
    parsed[key] = { answer, createdAt: Date.now() }
    const entries = Object.entries(parsed)
    entries.sort((a, b) => b[1].createdAt - a[1].createdAt)
    const trimmed = Object.fromEntries(entries.slice(0, 48))
    window.localStorage.setItem(AI_CACHE_KEY, JSON.stringify(trimmed))
  } catch {
    // Cache is best-effort; generation still works without it.
  }
}

function responseError(body: unknown, fallback: string) {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail?: unknown }).detail
    if (typeof detail === 'string') return detail.slice(0, 180)
  }
  return fallback
}

function isAnswer(value: unknown): value is AiExplainResponse {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<AiExplainResponse>
  const isClaim = (claim: unknown) => Boolean(
    claim && typeof claim === 'object'
    && typeof (claim as { text?: unknown }).text === 'string'
    && Array.isArray((claim as { fact_ids?: unknown }).fact_ids)
    && (claim as { fact_ids: unknown[] }).fact_ids.every((id) => typeof id === 'string'),
  )
  return isClaim(candidate.summary)
    && Array.isArray(candidate.actions) && candidate.actions.every(isClaim)
    && Array.isArray(candidate.caveats) && candidate.caveats.every(isClaim)
}

export function AiExplainPanel({ source, defaultQuestion = DEFAULT_QUESTION, auto = false, cacheKey }: {
  source: AiExplainSource
  defaultQuestion?: string
  auto?: boolean
  cacheKey?: string
}) {
  const [expanded, setExpanded] = useState(auto)
  const [availability, setAvailability] = useState<Availability>(auto ? 'checking' : 'idle')
  const [question, setQuestion] = useState(defaultQuestion)
  const [answer, setAnswer] = useState<AiExplainResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [followUp, setFollowUp] = useState(false)
  const request = useRef<AbortController | null>(null)
  const autoStarted = useRef(false)
  const autoRetried = useRef(false)
  const panelId = `ai-explain-${source.key.replace(/[^a-zA-Z0-9_-]/g, '-').slice(0, 80)}`

  useEffect(() => {
    request.current?.abort('source-changed')
    request.current = null
    autoStarted.current = false
    autoRetried.current = false
    setExpanded(auto)
    setAvailability(auto ? 'checking' : 'idle')
    setQuestion(defaultQuestion)
    setAnswer(null)
    setError(null)
    setIsLoading(false)
    setFollowUp(false)
  }, [source.key, defaultQuestion, auto])

  useEffect(() => () => request.current?.abort('unmount'), [])

  async function generate(withQuestion?: string, fromAuto = false) {
    const cleanQuestion = (withQuestion ?? question).trim()
    if (!cleanQuestion || isLoading) return
    request.current?.abort('superseded')
    const controller = new AbortController()
    request.current = controller
    setIsLoading(true)
    setError(null)
    setAnswer(null)
    const timeout = window.setTimeout(() => controller.abort('timeout'), 28_000)
    try {
      const response = await fetch(`${API_BASE}/v1/ai/explain`, {
        method: 'POST',
        headers: { accept: 'application/json', 'content-type': 'application/json' },
        body: JSON.stringify({
          question: cleanQuestion,
          context_tokens: source.contextTokens,
        }),
        signal: controller.signal,
        credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer',
      })
      const body: unknown = await response.json().catch(() => null)
      if (!response.ok) throw new Error(responseError(body, 'AI 讲解这次没有生成。'))
      if (!isAnswer(body)) throw new Error('AI 讲解返回格式不完整，请稍后重试。')
      setAnswer(body)
      if (cacheKey && (fromAuto || withQuestion === undefined)) writeCache(cacheKey, body)
    } catch (reason) {
      if (controller.signal.aborted && controller.signal.reason !== 'timeout') return
      const message = controller.signal.reason === 'timeout'
        ? 'AI 讲解超过 20 秒，规则结果仍可正常使用。'
        : reason instanceof Error ? reason.message.slice(0, 180) : 'AI 讲解这次没有生成。'
      setError(message)
      // Provider latency hovers near the timeout; one silent retry keeps the
      // auto reading usable without the user noticing the occasional hiccup.
      if (fromAuto && !autoRetried.current) {
        autoRetried.current = true
        window.setTimeout(() => { void generate(withQuestion, true) }, 1500)
        return
      }
    } finally {
      window.clearTimeout(timeout)
      if (request.current === controller) request.current = null
      setIsLoading(false)
    }
  }

  async function checkAvailability(thenGenerate = false) {
    request.current?.abort('superseded')
    const controller = new AbortController()
    request.current = controller
    setAvailability('checking')
    setError(null)
    const timeout = window.setTimeout(() => controller.abort('timeout'), 6_000)
    try {
      const response = await fetch(`${API_BASE}/v1/ai/status`, {
        signal: controller.signal,
        credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer',
      })
      const body: unknown = await response.json().catch(() => null)
      if (!response.ok) throw new Error(responseError(body, '无法检查 AI 讲解状态。'))
      const available = Boolean(
        source.contextTokens.length > 0
        && body && typeof body === 'object' && 'available' in body
        && (body as { available: unknown }).available === true,
      )
      setAvailability(available ? 'available' : 'unavailable')
      if (available && thenGenerate) void generate(defaultQuestion, true)
    } catch (reason) {
      if (controller.signal.aborted && controller.signal.reason !== 'timeout') return
      setAvailability('error')
      setError(controller.signal.reason === 'timeout'
        ? '状态检查超过 6 秒，请稍后重试。'
        : reason instanceof Error ? reason.message.slice(0, 180) : '无法检查 AI 讲解状态。')
    } finally {
      window.clearTimeout(timeout)
      if (request.current === controller) request.current = null
    }
  }

  // auto mode: cached answer shows instantly, otherwise generate on arrival.
  useEffect(() => {
    if (!auto || autoStarted.current) return
    autoStarted.current = true
    const cached = cacheKey ? readCache(cacheKey) : null
    if (cached) {
      setAnswer(cached.answer)
      setAvailability('available')
      return
    }
    if (source.contextTokens.length === 0) {
      setAvailability('unavailable')
      return
    }
    void checkAvailability(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auto, cacheKey, source.key])

  function openPanel() {
    const next = !expanded
    setExpanded(next)
    if (next && availability === 'idle') void checkAvailability()
  }

  const citedIds = answer
    ? [...answer.summary.fact_ids, ...answer.actions.flatMap((item) => item.fact_ids), ...answer.caveats.flatMap((item) => item.fact_ids)]
      .filter((id, index, all) => all.indexOf(id) === index)
    : []
  const citedFacts = citedIds
    .map((id) => source.facts.find((fact) => fact.id === id))
    .filter((fact): fact is NonNullable<typeof fact> => Boolean(fact)) ?? []

  return <section className="ai-explain-panel" aria-label={auto ? 'AI 解读' : '可选 AI 讲解'}>
    {!auto && <div className="ai-explain-intro">
      <div>
        <span><ChatCircleDots size={18} weight="fill" /> AI 讲解（可选）</span>
      </div>
      <button type="button" aria-expanded={expanded} aria-controls={panelId} onClick={openPanel}>
        {expanded ? '收起' : 'AI 帮我讲人话'}
      </button>
    </div>}

    {expanded && <div className="ai-explain-body" id={panelId}>
      {auto && <div className="ai-auto-head"><span><ChatCircleDots size={18} weight="fill" /> AI 解读</span>{cacheKey && answer && !isLoading && <small>本机缓存 · 24 小时内不重复调用</small>}</div>}
      {!auto && <p className="ai-privacy"><LockKey size={17} weight="bold" /> 点击“生成讲解”才会调用模型；系统不会自动附带出生资料。</p>}

      {availability === 'checking' && <div className="ai-status-skeleton" role="status" aria-label="正在检查 AI 讲解状态"><span /><span /><span /></div>}
      {availability === 'unavailable' && <div className="ai-unavailable"><Info size={20} weight="bold" /><div><strong>{source.contextTokens.length ? 'AI 讲解暂未配置' : '这份结果还没有核验上下文'}</strong><p>{source.contextTokens.length ? '规则排盘、专项分析和时间运势不受影响。' : '重新排盘即可准备；当前规则结果仍可正常使用。'}</p></div></div>}
      {availability === 'error' && <div className="ai-inline-error" role="alert"><WarningCircle size={20} weight="bold" /><div><strong>暂时无法检查状态</strong><p>{error}</p><button type="button" onClick={() => void checkAvailability(auto && !answer)}>重试</button></div></div>}

      {availability === 'available' && <>
        {followUp && <label className="ai-question">
          <span>你想追问什么？ <small>{question.length}/300</small></span>
          <textarea value={question} maxLength={300} rows={3} disabled={isLoading} onChange={(event) => setQuestion(event.target.value)} />
        </label>}
        {followUp && <button className="ai-generate" type="button" disabled={!question.trim() || isLoading} onClick={() => void generate()}>
          {isLoading ? <><SpinnerGap className="spin" size={19} /> 正在根据事实整理</> : answer ? '按新问题重新生成' : '生成讲解'}
        </button>}
        {!followUp && !isLoading && !error && <button type="button" className="ai-followup-toggle" onClick={() => { setFollowUp(true); setQuestion('') }}>换个问题追问 AI</button>}

        {isLoading && <div className="ai-answer-skeleton" role="status"><span /><span /><span /></div>}
        {error && !isLoading && <p className="ai-answer-error" role="alert"><WarningCircle size={18} weight="bold" />{error}</p>}
        {answer && !isLoading && <article className="ai-answer">
          <header><CheckCircle size={21} weight="fill" /><div><strong>AI 解读</strong></div></header>
          <p>{answer.summary.text}</p>
          {answer.actions.length > 0 && <div><strong>可以先做</strong><ul>{answer.actions.map((item) => <li key={`${item.text}-${item.fact_ids.join('-')}`}>{item.text}</li>)}</ul></div>}
          {answer.caveats.length > 0 && <div className="ai-caveats"><strong>注意</strong><ul>{answer.caveats.map((item) => <li key={`${item.text}-${item.fact_ids.join('-')}`}>{item.text}</li>)}</ul></div>}
          <details><summary>查看 AI 使用的 {citedFacts.length} 条依据</summary><ul>{citedFacts.map((fact, index) => <li key={fact.id}><b>依据 {index + 1}</b>{fact.text}</li>)}</ul></details>
        </article>}
      </>}
    </div>}
  </section>
}
