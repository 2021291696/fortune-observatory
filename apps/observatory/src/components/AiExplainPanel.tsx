import { ChatCircleDots, CheckCircle, Info, LockKey, SpinnerGap, WarningCircle } from '@phosphor-icons/react'
import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { API_BASE } from '../apiBase'
import { joinStream, streamKeyOf, type StreamHandle, type StreamSnapshot } from '../streamReading'
import type { AiExplainSource } from '../types'

const DEFAULT_QUESTION = '结合命盘，把这段结果讲透：先给结论，再按语料框架分节展开，引原典，结尾给「可以先做」与「注意」。'
// v11 = 紫微/八字分体系双流缓存；v10 及更早的合参缓存语义不同，直接作废。
const AI_CACHE_KEY = 'fortune-ai-cache-v11'
const AI_CACHE_TTL_MS = 24 * 60 * 60 * 1000

type Availability = 'idle' | 'checking' | 'available' | 'unavailable' | 'error'
type CacheEntry = { text: string; createdAt: number }

export function readCache(key: string): CacheEntry | null {
  try {
    const raw = window.localStorage.getItem(AI_CACHE_KEY)
    if (!raw || raw.length > 400_000) return null
    const parsed = JSON.parse(raw) as Record<string, unknown>
    const entry = parsed[key] as CacheEntry | undefined
    if (!entry || typeof entry.createdAt !== 'number' || Date.now() - entry.createdAt > AI_CACHE_TTL_MS) return null
    return typeof entry.text === 'string' && entry.text ? entry : null
  } catch {
    return null
  }
}

export function writeCache(key: string, text: string) {
  try {
    const raw = window.localStorage.getItem(AI_CACHE_KEY)
    const parsed = raw ? JSON.parse(raw) as Record<string, CacheEntry> : {}
    parsed[key] = { text, createdAt: Date.now() }
    const entries = Object.entries(parsed)
    entries.sort((a, b) => b[1].createdAt - a[1].createdAt)
    const trimmed = Object.fromEntries(entries.slice(0, 48))
    window.localStorage.setItem(AI_CACHE_KEY, JSON.stringify(trimmed))
  } catch {
    // Cache is best-effort; generation still works without it.
  }
}

export function clearCache(key: string) {
  try {
    const raw = window.localStorage.getItem(AI_CACHE_KEY)
    if (!raw) return
    const parsed = JSON.parse(raw) as Record<string, CacheEntry>
    delete parsed[key]
    window.localStorage.setItem(AI_CACHE_KEY, JSON.stringify(parsed))
  } catch {
    // Cache is best-effort.
  }
}

function responseError(body: unknown, fallback: string) {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail?: unknown }).detail
    if (typeof detail === 'string') return detail.slice(0, 180)
  }
  return fallback
}

// Estimated progress eases toward 96% and only reaches 100% on completion.
// 仅供思考期使用：进入流式正文后进度条让位给逐字输出。
export function estimatedProgress(elapsedMs: number): number {
  return Math.min(96, Math.round(100 * (1 - Math.exp(-elapsedMs / 7000))))
}

// 思考期文案：进度未封顶时报百分比；封顶后（长思考）改报已用时——
// 百分比纹丝不动会让用户以为卡死，秒数在走才说明模型还在工作。
export function aiThinkingLabel(progress: number, elapsedMs: number): string {
  if (progress >= 96) return `AI 正在梳理命盘依据… 已用时 ${Math.max(1, Math.round(elapsedMs / 1000))} 秒`
  return `AI 正在结合你的盘思考… ${progress}%`
}

const noopSubscribe = () => () => {}
const emptySnapshot: StreamSnapshot = { text: '', displayText: '', thinkText: '', phase: 'idle', startedAt: 0 }

// 行内 **加粗** 转 strong（模型爱用 Markdown 加粗，正文直排时不能漏星号）。
// 流式尾部允许"加粗未闭合"：奇数个 ** 时最后一段直接按加粗渲染，
// 避免闭合前星号裸显、闭合瞬间又突变加粗的闪烁。
function InlineText({ text }: { text: string }) {
  const parts = text.split('**')
  if (parts.length === 1) return <>{text}</>
  const unclosedTail = parts.length % 2 === 0
  return <>
    {parts.map((part, index) => {
      const bold = index % 2 === 1 || (unclosedTail && index === parts.length - 1)
      return bold ? <strong key={index}>{part}</strong> : <span key={index}>{part}</span>
    })}
  </>
}

// Markdown-lite 流式渲染：空行分段；## 标题行转小节（可以先做/注意复用
// 既有卡片样式）；--- 分隔线忽略；其余整段照排（含行内加粗）。末块允许
// 不完整，随流增长。
export function ReadingBody({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/)
  return <>
    {blocks.map((block, index) => {
      if (/^---+\s*$/.test(block.trim())) return null
      const lines = block.split('\n').map((line) => line.trim()).filter(Boolean)
      if (!lines.length) return null
      if (lines[0].startsWith('#')) {
        const title = lines[0].replace(/^#+\s*/, '')
        const items = lines.slice(1)
          .map((line) => line.replace(/^[-•*\d]+[.、)）]?\s*/, '').trim())
          .filter(Boolean)
        if (title.startsWith('可以先做') && items.length) {
          return <div key={index}><strong>可以先做</strong><ul>{items.map((item, itemIndex) => <li key={itemIndex}><InlineText text={item} /></li>)}</ul></div>
        }
        if (title.startsWith('注意') && items.length) {
          return <div key={index} className="ai-caveats"><strong>注意</strong><ul>{items.map((item, itemIndex) => <li key={itemIndex}><InlineText text={item} /></li>)}</ul></div>
        }
        return <p key={index}><strong><InlineText text={title} /></strong>{items.length ? `：${items.join('；')}` : ''}</p>
      }
      const isList = lines.length > 1 && lines.every((line) => /^[-•*\d]/.test(line))
      if (isList) {
        const items = lines.map((line) => line.replace(/^[-•*\d]+[.、)）]?\s*/, '').trim()).filter(Boolean)
        return <ul key={index}>{items.map((item, itemIndex) => <li key={itemIndex}><InlineText text={item} /></li>)}</ul>
      }
      return <p key={index}><InlineText text={block} /></p>
    })}
  </>
}

// 思考过程折叠条：思考中自动展开、流式显示推理链（秒数心跳由组件自驱），
// 正文开始自动收起，留一行可随时点开回看。非思考模型 thinkText 恒空，自然不渲染。
export function ThinkingTrace({ text, active, startedAt }: { text: string; active: boolean; startedAt: number }) {
  const [open, setOpen] = useState(active)
  const [, setTick] = useState(0)
  const bodyRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    setOpen(active)
    if (!active) return
    const timer = window.setInterval(() => setTick((tick) => tick + 1), 150)
    return () => window.clearInterval(timer)
  }, [active])

  // 展开时跟随新推理内容贴底。
  useEffect(() => {
    const el = bodyRef.current
    if (open && el) el.scrollTop = el.scrollHeight
  }, [text, open])

  const seconds = active && startedAt ? Math.max(1, Math.round((Date.now() - startedAt) / 1000)) : null

  return <div className="think-trace">
    <button type="button" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
      <span>{active ? <>思考中…{seconds !== null && ` 已用时 ${seconds} 秒`}</> : '已深度推演 · 点击查看思路'}</span>
      <span aria-hidden="true">{open ? '▾' : '▸'}</span>
    </button>
    {open && <div className="think-body" ref={bodyRef}>{text || '（正在展开推演…）'}</div>}
  </div>
}

export function AiExplainPanel({
  source,
  defaultQuestion = DEFAULT_QUESTION,
  auto = false,
  cacheKey,
  heading = 'AI 解读',
  lists = true,
}: {
  source: AiExplainSource
  defaultQuestion?: string
  auto?: boolean
  cacheKey?: string
  heading?: string
  lists?: boolean
}) {
  const [expanded, setExpanded] = useState(auto)
  const [availability, setAvailability] = useState<Availability>(auto ? 'checking' : 'idle')
  const [question, setQuestion] = useState(defaultQuestion)
  const [stream, setStream] = useState<StreamHandle | null>(null)
  const [followUp, setFollowUp] = useState(false)
  const [followUpText, setFollowUpText] = useState('')
  const [cachedText, setCachedText] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const [thinkingMs, setThinkingMs] = useState(0)
  // 进度条可见性：思考期常显；正文首字到达时冲到 100%，短暂停留后让位给流式正文。
  const [progressVisible, setProgressVisible] = useState(false)
  const request = useRef<AbortController | null>(null)
  const progressTimer = useRef<number | null>(null)
  const generationId = useRef(0)
  const answerRef = useRef<HTMLElement | null>(null)

  const snapshot: StreamSnapshot | null = useSyncExternalStore(
    stream ? stream.subscribe : noopSubscribe,
    stream ? stream.getSnapshot : () => emptySnapshot,
  )
  const streamText = snapshot && snapshot.text ? snapshot.text : null
  // 渲染走打字机节奏层；完整 text 只用于缓存与收尾判定。
  const streamDisplayText = snapshot && snapshot.displayText ? snapshot.displayText : null
  const phase = snapshot?.phase ?? null

  function startProgress(fromTimestamp?: number) {
    const startedAt = fromTimestamp ?? Date.now()
    setProgress(estimatedProgress(Date.now() - startedAt))
    setThinkingMs(Date.now() - startedAt)
    setProgressVisible(true)
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
    progressTimer.current = window.setInterval(() => {
      const elapsedMs = Date.now() - startedAt
      setProgress(estimatedProgress(elapsedMs))
      setThinkingMs(elapsedMs)
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
    setStream(null)
    setCachedText(null)
    setError(null)
    setProgress(0)
    setThinkingMs(0)
    setProgressVisible(false)
    setFollowUp(false)
    setFollowUpText('')
  }, [source.key, defaultQuestion, auto])

  useEffect(() => () => {
    request.current?.abort('unmount')
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
  }, [])

  // 进度条生命周期：思考期缓升；首个正文块到达即冲 100%，短暂停留后让位给流式正文；收尾归零。
  useEffect(() => {
    if (phase === 'streaming') {
      finishProgress()
      setProgressVisible(true)
      const hide = window.setTimeout(() => setProgressVisible(false), 600)
      return () => window.clearTimeout(hide)
    }
    if (phase === 'done' || phase === 'error') {
      finishProgress()
      setProgressVisible(false)
      setProgress(0)
      setThinkingMs(0)
    }
  }, [phase])

  // auto 模式：缓存命中即显示；否则挂上（或加入）在途流。
  useEffect(() => {
    if (!auto) return
    generationId.current += 1
    const run = generationId.current
    const cached = cacheKey ? readCache(cacheKey) : null
    if (cached) {
      setCachedText(cached.text)
      setStream(null)
      setAvailability('available')
      setError(null)
      return
    }
    setCachedText(null)
    if (source.contextTokens.length === 0) {
      setAvailability('unavailable')
      return
    }
    setAvailability('available')
    setError(null)
    const handle = joinStream(cacheKey ?? source.key, '/v1/ai/reading', {
      question: defaultQuestion,
      context_tokens: source.contextTokens,
      stream_key: streamKeyOf('auto', cacheKey ?? source.key),
    })
    setStream(handle)
    startProgress(handle.getSnapshot().startedAt)
    void run
  }, [auto, cacheKey, source.key, defaultQuestion])

  // 收尾写入本机缓存（追问不写）：守卫看 followUp 模式标志而非输入框文本——
  // 追问发起时 followUpText 已被清空，看它会让追问答案污染主缓存键。
  useEffect(() => {
    if (phase !== 'done' || !streamText || !cacheKey || followUp) return
    writeCache(cacheKey, streamText)
  }, [phase, streamText, cacheKey, followUp])

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

  function generateFollowUp() {
    const cleanQuestion = followUpText.trim() || question.trim()
    if (!cleanQuestion || availability !== 'available') return
    setError(null)
    const handle = joinStream(`follow-${Date.now()}`, '/v1/ai/reading', {
      question: cleanQuestion,
      context_tokens: source.contextTokens,
      stream_key: streamKeyOf('follow', source.key, cleanQuestion),
    })
    setStream(handle)
    setFollowUpText('')
    startProgress(handle.getSnapshot().startedAt)
  }

  function generateManual() {
    if (availability !== 'available') return
    setError(null)
    const handle = joinStream(cacheKey ?? source.key, '/v1/ai/reading', {
      question: question.trim() || defaultQuestion,
      context_tokens: source.contextTokens,
      stream_key: streamKeyOf('manual', cacheKey ?? source.key, question.trim() || defaultQuestion),
    })
    setStream(handle)
    startProgress(handle.getSnapshot().startedAt)
  }

  function openPanel() {
    const next = !expanded
    setExpanded(next)
    if (next && availability === 'idle') void checkAvailability()
  }

  const isThinking = Boolean(stream) && phase === 'thinking'
  const isStreaming = Boolean(stream) && (phase === 'streaming' || isThinking)
  const hasText = Boolean(streamText || cachedText)
  const bodyText = streamDisplayText ?? cachedText ?? ''
  const thinkText = snapshot?.thinkText ?? ''
  // 思考折叠条：思考期常驻（哪怕还没吐出第一个 think 字），之后有思考记录才留痕。
  const showTrace = Boolean(stream) && (isThinking || Boolean(thinkText))

  // 流式滚动跟随：正文底缘刚滑出视口下沿时把页面轻轻下推，保证"字在往外
  // 蹦"始终可见；用户向上回读后底缘远离视口，就不再打扰。
  useEffect(() => {
    if (!isStreaming || !streamDisplayText) return
    const el = answerRef.current
    if (!el) return
    const overflow = el.getBoundingClientRect().bottom - window.innerHeight
    if (overflow > 0 && overflow < 140) {
      window.scrollBy({ top: overflow + 24, behavior: 'auto' })
    }
  }, [streamDisplayText, isStreaming])

  return <section className="ai-explain-panel" aria-label={auto ? heading : '可选 AI 讲解'}>
    {!auto && <div className="ai-explain-intro">
      <div>
        <span><ChatCircleDots size={18} weight="fill" /> AI 讲解（可选）</span>
      </div>
      <button type="button" aria-expanded={expanded} aria-controls={panelId(source.key)} onClick={openPanel}>
        {expanded ? '收起' : 'AI 帮我讲人话'}
      </button>
    </div>}

    {expanded && <div className="ai-explain-body" id={panelId(source.key)}>
      {auto && <div className="ai-auto-head"><span><ChatCircleDots size={18} weight="fill" /> {heading}</span>{cacheKey && phase === 'done' && !followUpText && <small>本机缓存 · 24 小时内不重复调用</small>}</div>}
      {!auto && <p className="ai-privacy"><LockKey size={17} weight="bold" /> 点击「生成讲解」才会调用模型。讲解只发送盘面事实和你的问题，不发送出生时间或坐标。</p>}

      {availability === 'checking' && <div className="ai-status-skeleton" role="status" aria-label="正在检查 AI 讲解状态"><span /><span /><span /></div>}
      {availability === 'unavailable' && <div className="ai-unavailable"><Info size={20} weight="bold" /><div><strong>{source.contextTokens.length ? 'AI 讲解暂未配置' : '这份结果还没有核验上下文'}</strong><p>{source.contextTokens.length ? '规则排盘、专项分析和时间运势不受影响。' : '重新排盘即可准备；当前规则结果仍可正常使用。'}</p></div></div>}
      {availability === 'error' && <div className="ai-inline-error" role="alert"><WarningCircle size={20} weight="bold" /><div><strong>暂时无法检查状态</strong><p>{error}</p><button type="button" onClick={() => void checkAvailability()}>重试</button></div></div>}

      {availability === 'available' && <>
        {followUp && <label className="ai-question">
          <span>你想追问什么？ <small>{followUpText.length}/300</small></span>
          <textarea value={followUpText} maxLength={300} rows={3} disabled={isStreaming} onChange={(event) => setFollowUpText(event.target.value)} />
        </label>}
        {followUp && <button className="ai-generate" type="button" disabled={!followUpText.trim() || isStreaming} onClick={generateFollowUp}>
          {isStreaming ? <><SpinnerGap className="spin" size={19} /> 正在根据事实整理</> : '按新问题重新生成'}
        </button>}
        {!followUp && !hasText && !isStreaming && !error && availability === 'available' && !auto && <button className="ai-generate" type="button" onClick={generateManual}>生成讲解</button>}
        {!followUp && !isStreaming && phase === 'done' && <button type="button" className="ai-followup-toggle" onClick={() => { setFollowUp(true); setFollowUpText(''); setQuestion(defaultQuestion) }}>换个问题追问 AI</button>}
        {!followUp && !isStreaming && phase === 'error' && <button type="button" className="ai-followup-toggle" onClick={() => { setStream(null); generateManual() }}>重新生成讲解</button>}

        {/* 思考期只显示思考折叠条（已用时反馈在其中）；进度条仅在正文开始的瞬间闪一下「开始输出」。 */}
        {progressVisible && !isThinking && <div className="ai-progress" role="status" aria-label={aiThinkingLabel(progress, thinkingMs)}>
          <div className="ai-progress-line"><i style={{ width: `${progress}%` }} /></div>
          <span>{progress >= 100 ? '开始输出' : aiThinkingLabel(progress, thinkingMs)}</span>
        </div>}

        {showTrace && <ThinkingTrace text={thinkText} active={isThinking} startedAt={snapshot?.startedAt ?? 0} />}

        {error && !isStreaming && <p className="ai-answer-error" role="alert"><WarningCircle size={18} weight="bold" />{error}</p>}
        {bodyText && <article className="ai-answer" ref={answerRef}>
          {/* auto 场景标题已在 ai-auto-head 出现过，这里只留核验信号，避免同一行字出现两遍 */}
          <header><CheckCircle size={21} weight="fill" /><div><strong>{auto ? '已核验 · 结合盘面事实' : heading}</strong></div>{isStreaming && <SpinnerGap className="spin" size={16} />}</header>
          {lists
            ? <ReadingBody text={bodyText} />
            : bodyText.split(/\n{2,}/).map((paragraph, index) => <p key={index}>{paragraph}</p>)}
          <details><summary>查看 AI 使用的 {source.facts.length} 条盘面事实</summary><ul>{source.facts.map((fact, index) => <li key={fact.id}><b>依据 {index + 1}</b>{fact.text}</li>)}</ul></details>
        </article>}
      </>}
    </div>}
  </section>
}

function panelId(key: string) {
  return `ai-explain-${key.replace(/[^a-zA-Z0-9_-]/g, '-').slice(0, 80)}`
}
