import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Compass, Sparkle } from '@phosphor-icons/react'
import { estimatedProgress, ReadingBody, ThinkingTrace } from './AiExplainPanel'
import { joinStream, type StreamHandle, type StreamSnapshot } from '../streamReading'
import { API_BASE } from '../apiBase'
import type { QimenChartResponse, SaveDraft } from '../types'

const noopSubscribe = () => () => {}
const emptySnapshot: StreamSnapshot = { text: '', displayText: '', thinkText: '', phase: 'idle', startedAt: 0 }

// 事项分类与后端 QimenChartRequest.QUESTION_TYPES 一一对应
const QUESTION_TYPES = ['事业', '求财', '感情', '学业', '健康', '出行', '诉讼', '寻人寻物', '其他'] as const
// 感情类的对象关系（取用神需要）：值来自 skill 的 yongshen 口径
const ROMANCE_HINTS = ['男问女', '女问男', '同性关系'] as const

const QIMEN_EXAMPLES = ['下个月跳槽顺不顺', '这单生意能不能谈成', '最近该往哪个方向努力', '这次考试发挥如何']

export function QimenConsole({ onSave }: {
  onSave: (draft: SaveDraft) => void
}) {
  const [questionType, setQuestionType] = useState<string>('事业')
  const [romanceHint, setRomanceHint] = useState<string>('男问女')
  const [goal, setGoal] = useState('')
  const [timeMode, setTimeMode] = useState<'now' | 'custom'>('now')
  const [timeInput, setTimeInput] = useState('')
  const [city, setCity] = useState('')
  const [detailLevel, setDetailLevel] = useState<'brief' | 'detailed'>('brief')
  const [chart, setChart] = useState<QimenChartResponse | null>(null)
  const [chartBusy, setChartBusy] = useState(false)
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
  // essay 是完整文本（保存用）；渲染走打字机节奏层。
  const essay = snapshot?.text ?? ''
  const essayDisplay = snapshot?.displayText ?? ''
  const thinkText = snapshot?.thinkText ?? ''

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

  function composeGoal(): string {
    if (questionType === '感情') return `${goal.trim()}（${romanceHint}）`
    return goal.trim()
  }

  async function castChart() {
    const goalText = composeGoal()
    if (goalText.length < 2) {
      setError('先写一句最想判断什么，比如能不能成、什么时候动。')
      return
    }
    if (timeMode === 'custom' && !timeInput) {
      setError('选了自定义时间，就把日期和时辰补上。')
      return
    }
    setError(null)
    setChart(null)
    setStream(null) // 换盘即作废旧解读：一张盘配一篇
    setChartBusy(true)
    try {
      const response = await fetch(`${API_BASE}/v1/qimen/chart`, {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          question_type: questionType,
          question_goal: goalText,
          time_mode: timeMode,
          time_input: timeMode === 'custom' ? timeInput.replace('T', ' ') : null,
          city: city.trim() || null,
          detail_level: detailLevel,
        }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => null) as { detail?: string } | null
        throw new Error(payload?.detail ?? '这一局没排成，请稍后重试。')
      }
      setChart(await response.json() as QimenChartResponse)
    } catch (castError) {
      setError(castError instanceof Error ? castError.message : '这一局没排成，请稍后重试。')
    } finally {
      setChartBusy(false)
    }
  }

  function interpret() {
    if (!chart) return
    setError(null)
    const handle = joinStream(`qimen-${Date.now()}`, '/v1/qimen/interpret/stream', { chart })
    setStream(handle)
    startProgress(handle.getSnapshot().startedAt)
  }

  function summaryLine(data: QimenChartResponse): string {
    const c = data.chart
    return `${c.dun_type}${c.ju_number}局 · ${c.xunshou}旬（遁${c.hidden_yi}） · 值符${c.zhifu.star}落${palaceName(data, c.zhifu.palace)} · 值使${c.zhishi.door}落${palaceName(data, c.zhishi.palace)}`
  }

  function palaceName(data: QimenChartResponse, palace: number | null): string {
    if (palace === null) return '未知宫'
    const found = data.chart.palaces.find((item) => item.palace === palace)
    return found ? `${found.name}（${found.direction}）` : `${palace}宫`
  }

  // 时干落宫按天盘反查（引擎盘面 per-palace sky_stem 即天盘干）
  function timeStemPalace(data: QimenChartResponse): number | null {
    const found = data.chart.palaces.find((item) => item.sky_stem === data.chart.time_stem_visible)
    return found ? found.palace : null
  }

  function save() {
    if (!chart || !essay) return
    const patterns = chart.chart.detected_patterns
      .map((item) => `【格局】${item.name}（${item.detail}，${item.nature}）`)
    onSave({
      kind: 'qimen',
      title: `${chart.question_type} · ${chart.question_goal}`.slice(0, 40),
      summary: essay.slice(0, 600),
      details: [`【盘面】${summaryLine(chart)}`, ...patterns, ...chart.warnings.map((item) => `【提醒】${item}`)],
    })
  }

  return <section className="task-view qimen-view" id="qimen" aria-labelledby="qimen-title">
    <header className="task-heading">
      <h1 id="qimen-title">奇门</h1>
      <p>先起局，再读盘。盘是算出来的，不是编的。</p>
    </header>
    <div className="dream-console qimen-console">
      <div className="dream-composer">
        <div className="qimen-form-grid">
          <label>
            <span>看什么事</span>
            <select value={questionType} onChange={(event) => setQuestionType(event.target.value)} disabled={busy}>
              {QUESTION_TYPES.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          {questionType === '感情' && <label>
            <span>问谁</span>
            <select value={romanceHint} onChange={(event) => setRomanceHint(event.target.value)} disabled={busy}>
              {ROMANCE_HINTS.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>}
          <label>
            <span>起局时间</span>
            <span className="qimen-time-toggle">
              <button type="button" className={timeMode === 'now' ? 'is-active' : ''} disabled={busy} onClick={() => setTimeMode('now')}>就现在</button>
              <button type="button" className={timeMode === 'custom' ? 'is-active' : ''} disabled={busy} onClick={() => setTimeMode('custom')}>指定时间</button>
            </span>
          </label>
          {timeMode === 'custom' && <label>
            <span>日期与时辰</span>
            <input type="datetime-local" value={timeInput} onChange={(event) => setTimeInput(event.target.value)} disabled={busy} />
          </label>}
          <label>
            <span>你在哪个城市（可不填）</span>
            <input type="text" value={city} maxLength={40} onChange={(event) => setCity(event.target.value)} placeholder="如：成都；海外请写国家+城市" disabled={busy} />
          </label>
          <label>
            <span>讲法</span>
            <span className="qimen-time-toggle">
              <button type="button" className={detailLevel === 'brief' ? 'is-active' : ''} disabled={busy} onClick={() => setDetailLevel('brief')}>直接结论</button>
              <button type="button" className={detailLevel === 'detailed' ? 'is-active' : ''} disabled={busy} onClick={() => setDetailLevel('detailed')}>详细讲解</button>
            </span>
          </label>
        </div>
        <label>
          <span>最想判断什么</span>
          <textarea
            rows={2}
            maxLength={120}
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            placeholder="一句话就够：能不能成、什么时候动、选哪边、要避开什么。"
            disabled={busy}
          />
        </label>
        <div className="dream-examples">
          <span>试试：</span>
          {QIMEN_EXAMPLES.map((example) => (
            <button key={example} type="button" disabled={busy || chartBusy} onClick={() => setGoal(example)}>{example}</button>
          ))}
        </div>
        {progressVisible && phase !== 'thinking' && <div className="ai-progress" role="status" aria-live="polite">
          <span>{progress >= 100 ? '开始输出' : `AI 正在对照盘面思考… ${progress}%`}</span>
          <div className="ai-progress-line"><i style={{ width: `${progress}%` }} /></div>
        </div>}
        <button type="button" className="qimen-cast" onClick={() => void castChart()} disabled={chartBusy || busy}>
          {chartBusy ? '正在起局…' : chart ? '重新起局' : <><Sparkle size={16} /> 起局</>}
        </button>
      </div>
      {error && <p className="dream-error" role="alert">{error}</p>}
      {chart && <article className="qimen-chart-card" aria-label="奇门盘面">
        <header>
          <span>盘面摘要</span>
          <h2>{chart.chart.dun_type}{chart.chart.ju_number}局 · {chart.chart.yuan}</h2>
          <p>{chart.calendar_solar} · {chart.calendar_lunar.month_text}{chart.calendar_lunar.day_text}{chart.calendar_lunar.is_leap_month ? '（闰）' : ''} · {chart.jieqi.active_jie}节令</p>
        </header>
        <dl>
          <dt>四柱</dt><dd>{chart.ganzhi.year} {chart.ganzhi.month} {chart.ganzhi.day} {chart.ganzhi.time}</dd>
          <dt>旬首</dt><dd>{chart.chart.xunshou}（遁{chart.chart.hidden_yi}） · 旬空 {chart.chart.kongwang.join('、') || '无'}</dd>
          <dt>值符</dt><dd>{chart.chart.zhifu.star} 落{palaceName(chart, chart.chart.zhifu.palace)}</dd>
          <dt>值使</dt><dd>{chart.chart.zhishi.door} 落{palaceName(chart, chart.chart.zhishi.palace)}</dd>
          <dt>日干</dt><dd>{chart.chart.day_stem.stem} 落{palaceName(chart, chart.chart.day_stem.palace)}（求测人）{chart.chart.day_stem.note ? ` · ${chart.chart.day_stem.note}` : ''}</dd>
          <dt>时干</dt><dd>{chart.chart.time_stem_visible} 落{palaceName(chart, timeStemPalace(chart))}（所问之事）</dd>
          <dt>驿马</dt><dd>{chart.chart.yima.branch ? `${chart.chart.yima.branch} 落${palaceName(chart, chart.chart.yima.palace)}` : '无'}</dd>
          {chart.chart.detected_patterns.length > 0 && <dt>格局</dt>}
          {chart.chart.detected_patterns.length > 0 && <dd>
            {chart.chart.detected_patterns.map((item) => (
              <span key={`${item.name}-${item.palace}`} className={`qimen-pattern ${item.nature === '吉' ? 'is-ji' : 'is-xiong'}`}>{item.name}·{item.detail}</span>
            ))}
          </dd>}
        </dl>
        {chart.warnings.length > 0 && <ul className="qimen-warnings">
          {chart.warnings.map((item) => <li key={item}>{item}</li>)}
        </ul>}
      </article>}
      {chart && <div className="dream-composer qimen-interpret-bar">
        <button type="button" onClick={() => void interpret()} disabled={busy}>
          {busy ? '正在读盘…' : essay ? '再解一次' : <><Compass size={16} /> 读盘</>}
        </button>
      </div>}
      {(phase === 'thinking' || thinkText) && <div className="qimen-thinking"><ThinkingTrace text={thinkText} active={phase === 'thinking'} startedAt={snapshot?.startedAt ?? 0} /></div>}
      {snapshot?.phase === 'error' && <p className="dream-error" role="alert">{snapshot.error} <button type="button" onClick={() => void interpret()}>重试</button></p>}
      {essayDisplay && <article className="dream-result" aria-live="polite">
        <div className="dream-essay"><ReadingBody text={essayDisplay} /></div>
        {phase === 'done' && <button type="button" onClick={save}><Compass size={16} /> 保存到本机</button>}
      </article>}
    </div>
  </section>
}
