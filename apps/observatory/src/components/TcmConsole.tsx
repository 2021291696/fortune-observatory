import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Leaf } from '@phosphor-icons/react'
import { estimatedProgress, ReadingBody, ThinkingTrace } from './AiExplainPanel'
import { joinStream, type StreamHandle, type StreamSnapshot } from '../streamReading'
import type { SaveDraft } from '../types'

const noopSubscribe = () => () => {}
const emptySnapshot: StreamSnapshot = { text: '', displayText: '', thinkText: '', phase: 'idle', startedAt: 0 }

// 空态引导：一键填入的示例问诊，降低"不知道问什么"的起步门槛。
const TCM_EXAMPLES = ['长期失眠多梦怎么办', '一吃凉的就腹泻', '手脚冰凉特别怕冷', '感冒刚起，怕冷无汗']

export function TcmConsole({ onSave }: {
  onSave: (draft: SaveDraft) => void
}) {
  const [question, setQuestion] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [stream, setStream] = useState<StreamHandle | null>(null)
  const [progress, setProgress] = useState(0)
  const [progressVisible, setProgressVisible] = useState(false)
  const progressTimer = useRef<number | null>(null)

  const snapshot: StreamSnapshot | null = useSyncExternalStore(
    stream ? stream.subscribe : noopSubscribe,
    stream ? stream.getSnapshot : () => emptySnapshot,
  )
  const phase = snapshot?.phase ?? null
  const busy = Boolean(stream) && (phase === 'thinking' || phase === 'streaming')
  const essay = snapshot?.text ?? ''
  const essayDisplay = snapshot?.displayText ?? ''
  const sources = snapshot?.sources ?? []
  const thinkText = snapshot?.thinkText ?? ''
  const showTrace = Boolean(stream) && (phase === 'thinking' || Boolean(thinkText))

  function startProgress(fromTimestamp?: number) {
    const startedAt = fromTimestamp ?? Date.now()
    setProgress(estimatedProgress(Date.now() - startedAt))
    setProgressVisible(true)
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
    }
  }, [phase])

  useEffect(() => () => {
    if (progressTimer.current !== null) window.clearInterval(progressTimer.current)
  }, [])

  function consult() {
    const text = question.trim()
    if (text.length < 4) {
      setError('先写想问的情况，至少几个字。')
      return
    }
    setError(null)
    const handle = joinStream(`tcm-${Date.now()}`, '/v1/tcm/consult/stream', { question: text })
    setStream(handle)
    startProgress(handle.getSnapshot().startedAt)
  }

  function save() {
    if (!essay) return
    onSave({
      kind: 'tcm',
      title: question.trim().slice(0, 40) || '一次问诊',
      summary: essay.slice(0, 600),
      details: sources.map((item) => `${item.work}：${item.quote}`),
    })
  }

  return <section className="task-view tcm-view" id="tcm" aria-labelledby="tcm-title">
    <header className="task-heading">
      <h1 id="tcm-title">中医</h1>
      <p>经方视角聊身体。仅供学习，不适请就医。</p>
    </header>
    <div className="dream-console">
      <div className="dream-composer">
        <label>
          <span>想问的情况</span>
          <textarea
            rows={6}
            maxLength={2000}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="身体什么情况、持续多久、冷热汗便饮食睡眠，说得越具体越对路。"
          />
        </label>
        <div className="dream-examples">
          <span>试试：</span>
          {TCM_EXAMPLES.map((example) => (
            <button key={example} type="button" disabled={busy} onClick={() => setQuestion(example)}>{example}</button>
          ))}
        </div>
        {progressVisible && phase !== 'thinking' && <div className="ai-progress" role="status" aria-live="polite">
          <span>{progress >= 100 ? '开始输出' : `AI 正在结合经方口径思考… ${progress}%`}</span>
          <div className="ai-progress-line"><i style={{ width: `${progress}%` }} /></div>
        </div>}
        {showTrace && <ThinkingTrace text={thinkText} active={phase === 'thinking'} startedAt={snapshot?.startedAt ?? 0} />}
        <button type="button" onClick={() => void consult()} disabled={busy}>
          {busy ? '正在问诊…' : essay ? '再问一次' : '开始问诊'}
        </button>
      </div>
      {error && <p className="dream-error" role="alert">{error} <button type="button" onClick={() => void consult()}>重试</button></p>}
      {snapshot?.phase === 'error' && <p className="dream-error" role="alert">{snapshot.error} <button type="button" onClick={() => void consult()}>重试</button></p>}
      {essayDisplay && <article className="dream-result" aria-live="polite">
        <div className="dream-essay"><ReadingBody text={essayDisplay} /></div>
        {sources.length > 0 && <section>
          <h2>本次引用的口径</h2>
          <ul>{sources.map((item) => <li key={`${item.work}-${item.quote}`}>
            {item.work}：{item.quote}
          </li>)}</ul>
        </section>}
        {phase === 'done' && <button type="button" onClick={save}><Leaf size={16} /> 保存到本机</button>}
      </article>}
    </div>
  </section>
}
