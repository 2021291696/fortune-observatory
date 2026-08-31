import { useEffect, useRef, useState } from 'react'
import { MoonStars } from '@phosphor-icons/react'
import { API_BASE } from '../apiBase'
import { estimatedProgress } from './AiExplainPanel'
import type { DreamInterpretResponse, SaveDraft } from '../types'

export function DreamConsole({ onSave }: {
  onSave: (draft: SaveDraft) => void
}) {
  const [dream, setDream] = useState('')
  const [result, setResult] = useState<DreamInterpretResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const progressTimer = useRef<number | null>(null)

  function startProgress() {
    const startedAt = Date.now()
    setProgress(estimatedProgress(0))
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

  useEffect(() => () => {
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
  }, [])

  async function interpret() {
    const text = dream.trim()
    if (text.length < 4) {
      setError('先写这场梦，至少几个字。')
      return
    }
    setBusy(true)
    setError(null)
    setResult(null)
    startProgress()
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort('timeout'), 45_000)
    try {
      const response = await fetch(`${API_BASE}/v1/dreams/interpret`, {
        method: 'POST',
        headers: { accept: 'application/json', 'content-type': 'application/json' },
        body: JSON.stringify({ dream: text }),
        signal: controller.signal,
        credentials: 'omit',
        cache: 'no-store',
        referrerPolicy: 'no-referrer',
      })
      const body: unknown = await response.json().catch(() => null)
      if (!response.ok) {
        const detail = body && typeof body === 'object' && 'detail' in body ? String((body as { detail: unknown }).detail) : ''
        throw new Error(detail || '这一梦没写成')
      }
      setResult(body as DreamInterpretResponse)
    } catch (reason) {
      setResult(null)
      setError(reason instanceof Error && reason.name === 'AbortError' ? '解梦超时，请重试。' : '这一梦没写成，请重试。')
    } finally {
      window.clearTimeout(timer)
      finishProgress()
      setBusy(false)
    }
  }

  function save() {
    if (!result) return
    onSave({
      kind: 'dream',
      title: dream.trim().slice(0, 40) || '一场梦',
      summary: result.essay.slice(0, 600),
      details: result.sources.map((item) => `【${item.channel}】${item.work}：${item.quote}`),
    })
  }

  return <section className="task-view dream-view" id="dream" aria-labelledby="dream-title">
    <header className="task-heading">
      <h1 id="dream-title">解梦</h1>
      <p>先靠梦书。资料不落服务器。</p>
    </header>
    <div className="dream-console">
      <div className="dream-composer">
        <label>
          <span>这场梦</span>
          <textarea
            rows={6}
            maxLength={2000}
            value={dream}
            onChange={(event) => setDream(event.target.value)}
            placeholder="发生了什么、中间怎么转、有没有做完。"
          />
        </label>
        {busy && <div className="ai-progress" role="status" aria-live="polite">
          <span>在解 {progress}%</span>
          <div className="ai-progress-line"><i style={{ width: `${progress}%` }} /></div>
        </div>}
        <button type="button" onClick={() => void interpret()} disabled={busy}>
          {busy ? `在解 ${progress}%` : '解读'}
        </button>
      </div>
      {error && <p className="dream-error" role="alert">{error} <button type="button" onClick={() => void interpret()}>重试</button></p>}
      {result && <article className="dream-result" aria-live="polite">
        {result.referral && <p className="dream-referral">{result.referral}</p>}
        {result.essay && <div className="dream-essay" style={{ whiteSpace: 'pre-wrap' }}>{result.essay}</div>}
        {result.sources.length > 0 && <section>
          <h2>本次匹配到的资料</h2>
          <ul>{result.sources.map((item) => <li key={`${item.channel}-${item.work}-${item.quote}`}>
            【{item.channel}】{item.work}：{item.quote}
          </li>)}</ul>
        </section>}
        <button type="button" onClick={save}><MoonStars size={16} /> 保存到本机</button>
      </article>}
    </div>
  </section>
}
