import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { MoonStars } from '@phosphor-icons/react'
import { estimatedProgress, ReadingBody } from './AiExplainPanel'
import { joinStream, type StreamHandle, type StreamSnapshot } from '../streamReading'
import type { SaveDraft } from '../types'

const noopSubscribe = () => () => {}
const emptySnapshot: StreamSnapshot = { text: '', phase: 'idle', startedAt: 0 }

export function DreamConsole({ onSave }: {
  onSave: (draft: SaveDraft) => void
}) {
  const [dream, setDream] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [stream, setStream] = useState<StreamHandle | null>(null)
  const [progress, setProgress] = useState(0)
  const progressTimer = useRef<number | null>(null)

  const snapshot: StreamSnapshot | null = useSyncExternalStore(
    stream ? stream.subscribe : noopSubscribe,
    stream ? stream.getSnapshot : () => emptySnapshot,
  )
  const phase = snapshot?.phase ?? null
  const busy = Boolean(stream) && (phase === 'thinking' || phase === 'streaming')
  const essay = snapshot?.text ?? ''
  const sources = snapshot?.sources ?? []

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
    if (phase === 'done' || phase === 'error') finishProgress()
  }, [phase])

  useEffect(() => () => {
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
  }, [])

  function interpret() {
    const text = dream.trim()
    if (text.length < 4) {
      setError('先写这场梦，至少几个字。')
      return
    }
    setError(null)
    const handle = joinStream(`dream-${Date.now()}`, '/v1/dreams/interpret/stream', { dream: text })
    setStream(handle)
    startProgress(handle.getSnapshot().startedAt)
  }

  function save() {
    if (!essay) return
    onSave({
      kind: 'dream',
      title: dream.trim().slice(0, 40) || '一场梦',
      summary: essay.slice(0, 600),
      details: sources.map((item) => `【${item.channel}】${item.work}：${item.quote}`),
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
        {phase === 'thinking' && <div className="ai-progress" role="status" aria-live="polite">
          <span>AI 正在结合梦书思考… {progress}%</span>
          <div className="ai-progress-line"><i style={{ width: `${progress}%` }} /></div>
        </div>}
        <button type="button" onClick={() => void interpret()} disabled={busy}>
          {busy ? '正在解读…' : essay ? '再解一次' : '解读'}
        </button>
      </div>
      {error && <p className="dream-error" role="alert">{error} <button type="button" onClick={() => void interpret()}>重试</button></p>}
      {snapshot?.phase === 'error' && <p className="dream-error" role="alert">{snapshot.error} <button type="button" onClick={() => void interpret()}>重试</button></p>}
      {essay && <article className="dream-result" aria-live="polite">
        <div className="dream-essay"><ReadingBody text={essay} /></div>
        {sources.length > 0 && <section>
          <h2>本次匹配到的资料</h2>
          <ul>{sources.map((item) => <li key={`${item.channel}-${item.work}-${item.quote}`}>
            【{item.channel}】{item.work}：{item.quote}
          </li>)}</ul>
        </section>}
        {phase === 'done' && <button type="button" onClick={save}><MoonStars size={16} /> 保存到本机</button>}
      </article>}
    </div>
  </section>
}
