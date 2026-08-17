import { ChatCircleDots, CheckCircle, Info, LockKey, SpinnerGap, WarningCircle } from '@phosphor-icons/react'
import { useEffect, useRef, useState } from 'react'
import { API_BASE } from '../apiBase'
import type { AiExplainResponse, AiExplainSource } from '../types'

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

async function fetchExplanation(question: string, contextTokens: string[]): Promise<AiExplainResponse> {
  const response = await fetch(`${API_BASE}/v1/ai/explain`, {
    method: 'POST',
    headers: { accept: 'application/json', 'content-type': 'application/json' },
    body: JSON.stringify({ question, context_tokens: contextTokens }),
    credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer',
  })
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) throw new Error(responseError(body, 'AI 讲解这次没有生成。'))
  if (!isAnswer(body)) throw new Error('AI 讲解返回格式不完整，请稍后重试。')
  return body
}

// Background generations live outside component lifecycles: leaving the page
// never aborts them, results always land in the cache, and any panel mounted
// later on the same cacheKey joins the in-flight promise instead of re-asking.
// startedAt keeps the progress bar continuous across page switches.
type GenerationOutcome = AiExplainResponse | { __failed: true; message: string }
type InflightGeneration = { task: Promise<GenerationOutcome>; startedAt: number }
const inflightGenerations = new Map<string, InflightGeneration>()

function joinBackgroundGeneration(cacheKey: string, question: string, contextTokens: string[]): InflightGeneration {
  const existing = inflightGenerations.get(cacheKey)
  if (existing) return existing
  const attempt = () => fetchExplanation(question, contextTokens).then((answer) => {
    writeCache(cacheKey, answer)
    return answer
  })
  const entry: InflightGeneration = {
    // One silent retry after 2.5s absorbs the provider's occasional timeouts
    // that hover near the configured ceiling.
    task: attempt()
      .catch(() => new Promise<GenerationOutcome>((resolve) => {
        window.setTimeout(() => {
          attempt()
            .catch((reason: unknown) => ({
              __failed: true as const,
              message: reason instanceof Error ? reason.message : 'AI 讲解这次没有生成，请稍后重试。',
            }))
            .then(resolve)
        }, 2_500)
      }))
      .finally(() => {
        if (inflightGenerations.get(cacheKey) === entry) inflightGenerations.delete(cacheKey)
      }),
    startedAt: Date.now(),
  }
  inflightGenerations.set(cacheKey, entry)
  return entry
}

// Estimated progress eases toward 96% and only reaches 100% on completion.
export function estimatedProgress(elapsedMs: number): number {
  return Math.min(96, Math.round(100 * (1 - Math.exp(-elapsedMs / 7000))))
}

export function AiExplainPanel({ source, defaultQuestion = DEFAULT_QUESTION, auto = false, cacheKey, hideProgress = false, onBusyChange }: {
  source: AiExplainSource
  defaultQuestion?: string
  auto?: boolean
  cacheKey?: string
  hideProgress?: boolean
  onBusyChange?: (busy: boolean) => void
}) {
  const [expanded, setExpanded] = useState(auto)
  const [availability, setAvailability] = useState<Availability>(auto ? 'checking' : 'idle')
  const [question, setQuestion] = useState(defaultQuestion)
  const [answer, setAnswer] = useState<AiExplainResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [followUp, setFollowUp] = useState(false)
  const request = useRef<AbortController | null>(null)
  const progressTimer = useRef<number | null>(null)
  const generationId = useRef(0)

  useEffect(() => {
    onBusyChange?.(isLoading)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoading])

  function startProgress(fromTimestamp?: number) {
    const startedAt = fromTimestamp ?? Date.now()
    setProgress(estimatedProgress(Date.now() - startedAt))
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
    progressTimer.current = window.setInterval(() => {
      setProgress(estimatedProgress(Date.now() - startedAt))
    }, 150)
  }

  function finishProgress() {
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
    progressTimer.current = null
    setProgress(100)
  }

  useEffect(() => {
    request.current?.abort('source-changed')
    request.current = null
    setExpanded(auto)
    setAvailability(auto ? 'checking' : 'idle')
    setQuestion(defaultQuestion)
    setAnswer(null)
    setError(null)
    setIsLoading(false)
    setProgress(0)
    setFollowUp(false)
  }, [source.key, defaultQuestion, auto])

  useEffect(() => () => {
    request.current?.abort('unmount')
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
  }, [])

  // auto mode: cache hit shows instantly, an in-flight background generation is
  // joined, otherwise one starts. The generation keeps running after unmount.
  useEffect(() => {
    if (!auto) return
    runAutoGeneration()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auto, cacheKey, source.key])

  function runAutoGeneration() {
    generationId.current += 1
    const run = generationId.current
    const cached = cacheKey ? readCache(cacheKey) : null
    if (cached) {
      setAnswer(cached.answer)
      setAvailability('available')
      setIsLoading(false)
      return
    }
    if (source.contextTokens.length === 0) {
      setAvailability('unavailable')
      return
    }
    setAvailability('available')
    setError(null)
    setAnswer(null)
    setIsLoading(true)
    const generation = joinBackgroundGeneration(cacheKey ?? source.key, defaultQuestion, source.contextTokens)
    startProgress(generation.startedAt)
    void generation.task
      .then((result) => {
        if (generationId.current !== run) return
        finishProgress()
        setIsLoading(false)
        if (result && !('__failed' in result)) setAnswer(result)
        else setError('__failed' in result ? result.message : 'AI 讲解这次没有生成，请稍后重试。')
      })
  }

  async function checkAvailability() {
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

  async function generate() {
    const cleanQuestion = question.trim()
    if (!cleanQuestion || isLoading || availability !== 'available') return
    request.current?.abort('superseded')
    const controller = new AbortController()
    request.current = controller
    setIsLoading(true)
    setError(null)
    setAnswer(null)
    startProgress()
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
      finishProgress()
      setAnswer(body)
      if (cacheKey && !followUp) writeCache(cacheKey, body)
    } catch (reason) {
      if (controller.signal.aborted && controller.signal.reason !== 'timeout') return
      finishProgress()
      setError(controller.signal.reason === 'timeout'
        ? 'AI 讲解超过 28 秒，规则结果仍可正常使用。'
        : reason instanceof Error ? reason.message.slice(0, 180) : 'AI 讲解这次没有生成。')
    } finally {
      window.clearTimeout(timeout)
      if (request.current === controller) request.current = null
      setIsLoading(false)
    }
  }

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
      <button type="button" aria-expanded={expanded} aria-controls={panelId(source.key)} onClick={openPanel}>
        {expanded ? '收起' : 'AI 帮我讲人话'}
      </button>
    </div>}

    {expanded && <div className="ai-explain-body" id={panelId(source.key)}>
      {auto && <div className="ai-auto-head"><span><ChatCircleDots size={18} weight="fill" /> AI 解读</span>{cacheKey && answer && !isLoading && <small>本机缓存 · 24 小时内不重复调用</small>}</div>}
      {!auto && <p className="ai-privacy"><LockKey size={17} weight="bold" /> 点击“生成讲解”才会调用模型；系统不会自动附带出生资料。</p>}

      {availability === 'checking' && <div className="ai-status-skeleton" role="status" aria-label="正在检查 AI 讲解状态"><span /><span /><span /></div>}
      {availability === 'unavailable' && <div className="ai-unavailable"><Info size={20} weight="bold" /><div><strong>{source.contextTokens.length ? 'AI 讲解暂未配置' : '这份结果还没有核验上下文'}</strong><p>{source.contextTokens.length ? '规则排盘、专项分析和时间运势不受影响。' : '重新排盘即可准备；当前规则结果仍可正常使用。'}</p></div></div>}
      {availability === 'error' && <div className="ai-inline-error" role="alert"><WarningCircle size={20} weight="bold" /><div><strong>暂时无法检查状态</strong><p>{error}</p><button type="button" onClick={() => void checkAvailability()}>重试</button></div></div>}

      {availability === 'available' && <>
        {followUp && <label className="ai-question">
          <span>你想追问什么？ <small>{question.length}/300</small></span>
          <textarea value={question} maxLength={300} rows={3} disabled={isLoading} onChange={(event) => setQuestion(event.target.value)} />
        </label>}
        {followUp && <button className="ai-generate" type="button" disabled={!question.trim() || isLoading} onClick={() => void generate()}>
          {isLoading ? <><SpinnerGap className="spin" size={19} /> 正在根据事实整理</> : answer ? '按新问题重新生成' : '生成讲解'}
        </button>}
        {!followUp && !isLoading && !error && answer && <button type="button" className="ai-followup-toggle" onClick={() => { setFollowUp(true); setQuestion('') }}>换个问题追问 AI</button>}
        {!followUp && !isLoading && !answer && error && cacheKey && <button type="button" className="ai-followup-toggle" onClick={runAutoGeneration}>重新生成 AI 解读</button>}

        {isLoading && !hideProgress && <div className="ai-progress" role="status" aria-label={`AI 正在思考，进度 ${progress}%`}>
          <div className="ai-progress-line"><i style={{ width: `${progress}%` }} /></div>
          <span>AI 正在结合你的盘思考… {progress}%</span>
        </div>}
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

function panelId(key: string) {
  return `ai-explain-${key.replace(/[^a-zA-Z0-9_-]/g, '-').slice(0, 80)}`
}
