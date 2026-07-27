import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { CheckCircle, WarningCircle } from '@phosphor-icons/react'
import { BirthForm } from './components/BirthForm'
import { Chart } from './components/Chart'
import { DomainAnalysisConsole } from './components/DomainAnalysisConsole'
import { FortuneConsole } from './components/FortuneConsole'
import { MemeMedia } from './components/MemeMedia'
import { MemeStage } from './components/MemeStage'
import { SavedReadings } from './components/SavedReadings'
import { ThemeRemote } from './components/ThemeRemote'
import { dateKey, fortuneWindow } from './dates'
import { resolveTheme, type ThemeId } from './themes'
import type { ChartResponse, DailyTransitResponse, FortuneScope, SavedReading, SaveDraft, TransitResponse, TransitWindowResponse } from './types'

const API_BASE = import.meta.env.PROD ? '/api' : (import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000')
const REQUEST_TIMEOUT_MS = 15_000
const validThemes: ThemeId[] = ['phoebe', 'ggbond', 'nailong', 'kawaii', 'shuffle']
const SAVED_READINGS_KEY = 'fortune-saved-readings-v1'

type BirthPayload = {
  civil_datetime: string
  timezone_id: 'Asia/Shanghai'
  longitude: number
  latitude: number
  sex_for_rule: string
  use_apparent_solar_time: true
  apparent_solar_datetime?: string
}

function initialTheme(): ThemeId {
  const saved = localStorage.getItem('fortune-theme') as ThemeId | null
  return saved && validThemes.includes(saved) ? saved : 'nailong'
}

function initialSeed() {
  const saved = Number(localStorage.getItem('fortune-shuffle-seed'))
  return Number.isFinite(saved) && saved > 0 ? saved : Math.floor(Math.random() * 1_000_000_000)
}

function initialSavedReadings(): SavedReading[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(SAVED_READINGS_KEY) ?? '[]')
    if (!Array.isArray(parsed)) return []
    const sanitized = parsed.filter((item): item is SavedReading => Boolean(
      item && typeof item === 'object'
      && typeof item.id === 'string' && typeof item.savedAt === 'string'
      && (item.kind === 'domain' || item.kind === 'fortune')
      && typeof item.title === 'string' && typeof item.summary === 'string'
      && Array.isArray(item.details) && item.details.every((detail: unknown) => typeof detail === 'string'),
    )).slice(0, 24).map((item) => ({
      id: item.id, savedAt: item.savedAt, kind: item.kind,
      title: item.title.slice(0, 120), summary: item.summary.slice(0, 600),
      details: item.details.slice(0, 12).map((detail) => detail.slice(0, 500)),
    }))
    try {
      localStorage.setItem(SAVED_READINGS_KEY, JSON.stringify(sanitized))
    } catch {
      // Existing results remain readable in memory even if storage is read-only.
    }
    return sanitized
  } catch {
    return []
  }
}

function responseError(body: unknown, fallback: string) {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail?: unknown }).detail
    if (typeof detail === 'string') return detail.slice(0, 180)
  }
  return fallback
}

async function postJson<T>(path: string, payload: unknown, controller: AbortController, fallback: string) {
  const timeout = window.setTimeout(() => controller.abort('timeout'), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { accept: 'application/json', 'content-type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
      credentials: 'omit',
      cache: 'no-store',
      referrerPolicy: 'no-referrer',
    })
    return await readResponse<T>(response, fallback)
  } finally {
    window.clearTimeout(timeout)
  }
}

function requestError(reason: unknown, controller: AbortController, fallback: string) {
  if (controller.signal.aborted) {
    return controller.signal.reason === 'timeout' ? '请求超过 15 秒，请检查服务后重试。' : null
  }
  if (reason instanceof Error && reason.message && !/failed to fetch|load failed|networkerror/i.test(reason.message)) {
    return reason.message.slice(0, 180)
  }
  return fallback
}

async function readResponse<T>(response: Response, fallback: string) {
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) throw new Error(responseError(body, fallback))
  return body as T
}

export function App() {
  const [themeId, setThemeId] = useState<ThemeId>(initialTheme)
  const [shuffleSeed, setShuffleSeed] = useState(initialSeed)
  const [isThemeChanging, setIsThemeChanging] = useState(false)
  const [motionPaused, setMotionPaused] = useState(() => localStorage.getItem('fortune-motion-paused') === 'true')
  const [chart, setChart] = useState<ChartResponse | null>(null)
  const [birthPayload, setBirthPayload] = useState<BirthPayload | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [daily, setDaily] = useState<DailyTransitResponse | null>(null)
  const [periods, setPeriods] = useState<TransitResponse | null>(null)
  const [windowTransit, setWindowTransit] = useState<TransitWindowResponse | null>(null)
  const [fortuneScope, setFortuneScope] = useState<FortuneScope>('today')
  const [requestedFortuneScope, setRequestedFortuneScope] = useState<FortuneScope>('today')
  const [fortuneError, setFortuneError] = useState<string | null>(null)
  const [isLoadingFortune, setIsLoadingFortune] = useState(false)
  const [savedReadings, setSavedReadings] = useState<SavedReading[]>(initialSavedReadings)
  const [savedNotice, setSavedNotice] = useState<string | null>(null)
  const theme = useMemo(() => resolveTheme(themeId, shuffleSeed), [themeId, shuffleSeed])
  const chartRequest = useRef<AbortController | null>(null)
  const fortuneRequest = useRef<AbortController | null>(null)
  const themeTimer = useRef<number | null>(null)
  const noticeTimer = useRef<number | null>(null)
  const chartSectionRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    const color = theme.palette === 'nailong' ? '#fff200' : theme.palette === 'ggbond' ? '#e31b23' : '#fffaf7'
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', color)
  }, [theme.palette])

  useEffect(() => () => {
    chartRequest.current?.abort('unmount')
    fortuneRequest.current?.abort('unmount')
    if (themeTimer.current !== null) window.clearTimeout(themeTimer.current)
    if (noticeTimer.current !== null) window.clearTimeout(noticeTimer.current)
  }, [])

  function persistSaved(next: SavedReading[]) {
    try {
      localStorage.setItem(SAVED_READINGS_KEY, JSON.stringify(next))
      setSavedReadings(next)
      return true
    } catch {
      showSavedNotice('本机存储不可用，未能保存这次结果')
      return false
    }
  }

  function showSavedNotice(message: string) {
    setSavedNotice(message)
    if (noticeTimer.current !== null) window.clearTimeout(noticeTimer.current)
    noticeTimer.current = window.setTimeout(() => setSavedNotice(null), 2400)
  }

  function saveReading(draft: SaveDraft) {
    const record: SavedReading = {
      ...draft,
      id: crypto.randomUUID(),
      savedAt: new Date().toISOString(),
    }
    const next = [record, ...savedReadings.filter((item) => !(
      item.kind === draft.kind && item.title === draft.title && item.summary === draft.summary
    ))].slice(0, 24)
    if (persistSaved(next)) showSavedNotice('已保存命理结果 · 不含出生资料')
  }

  function removeSaved(id: string) {
    persistSaved(savedReadings.filter((item) => item.id !== id))
  }

  function clearSaved() {
    persistSaved([])
  }

  function selectTheme(nextTheme: ThemeId) {
    if (nextTheme === themeId && nextTheme !== 'shuffle') return
    if (nextTheme === 'shuffle') {
      const nextSeed = Math.floor(Math.random() * 1_000_000_000)
      setShuffleSeed(nextSeed)
      localStorage.setItem('fortune-shuffle-seed', String(nextSeed))
    }
    setIsThemeChanging(true)
    setThemeId(nextTheme)
    localStorage.setItem('fortune-theme', nextTheme)
    if (themeTimer.current !== null) window.clearTimeout(themeTimer.current)
    themeTimer.current = window.setTimeout(() => setIsThemeChanging(false), 460)
  }

  function toggleMotion() {
    setMotionPaused((current) => {
      const next = !current
      localStorage.setItem('fortune-motion-paused', String(next))
      return next
    })
  }

  function clearSession() {
    if (chart && !window.confirm('将清除当前表单、命盘和未保存结果；保存区不受影响。确定继续吗？')) return false
    chartRequest.current?.abort('cleared')
    fortuneRequest.current?.abort('cleared')
    chartRequest.current = null
    fortuneRequest.current = null
    setChart(null)
    setBirthPayload(null)
    setDaily(null)
    setPeriods(null)
    setWindowTransit(null)
    setFortuneScope('today')
    setRequestedFortuneScope('today')
    setError(null)
    setFortuneError(null)
    setIsSubmitting(false)
    setIsLoadingFortune(false)
    return true
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const fields = new FormData(event.currentTarget)
    const civilDate = String(fields.get('civilDate') ?? '')
    const civilTime = String(fields.get('civilTime') ?? '')
    const apparentDate = String(fields.get('apparentDate') ?? '')
    const apparentTime = String(fields.get('apparentTime') ?? '')
    const longitude = Number(fields.get('longitude'))
    const latitude = Number(fields.get('latitude'))
    if ((apparentDate && !apparentTime) || (!apparentDate && apparentTime)) {
      setError('高级校正的日期和时间需要一起填写。')
      event.currentTarget.querySelector<HTMLInputElement>(`input[name="${apparentDate ? 'apparentTime' : 'apparentDate'}"]`)?.focus()
      return
    }
    if (!civilDate || !civilTime || !Number.isFinite(longitude) || !Number.isFinite(latitude)) {
      setError('请完整填写有效的出生日期、时间与经纬度。')
      return
    }
    const payload: BirthPayload = {
      civil_datetime: `${civilDate}T${civilTime}:00+08:00`,
      timezone_id: 'Asia/Shanghai',
      longitude,
      latitude,
      sex_for_rule: String(fields.get('sexForRule')),
      use_apparent_solar_time: true,
      ...(apparentDate && apparentTime ? { apparent_solar_datetime: `${apparentDate}T${apparentTime}:00+08:00` } : {}),
    }

    chartRequest.current?.abort('superseded')
    fortuneRequest.current?.abort('superseded')
    const controller = new AbortController()
    chartRequest.current = controller
    setIsSubmitting(true)
    setError(null)
    setFortuneError(null)
    try {
      const result = await postJson<ChartResponse>('/v1/charts', payload, controller, '排盘服务暂时不可用。')
      if (chartRequest.current !== controller) return
      setChart(result)
      setBirthPayload(payload)
      setDaily(null)
      setPeriods(null)
      setWindowTransit(null)
      setFortuneScope('today')
      setRequestedFortuneScope('today')
      void loadFortune('today', payload)
      window.requestAnimationFrame(() => {
        const section = chartSectionRef.current
        if (!section) return
        section.focus({ preventScroll: true })
        section.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
      })
    } catch (reason) {
      if (chartRequest.current !== controller) return
      const message = requestError(reason, controller, '无法连接排盘服务。')
      if (message) setError(message)
    } finally {
      if (chartRequest.current === controller) {
        chartRequest.current = null
        setIsSubmitting(false)
      }
    }
  }

  async function loadFortune(scope: FortuneScope, payloadOverride?: BirthPayload) {
    const payload = payloadOverride ?? birthPayload
    if (!payload) return
    const period = fortuneWindow(scope)
    const startDate = dateKey(period.start)
    const endDate = dateKey(period.end)
    fortuneRequest.current?.abort('superseded')
    const controller = new AbortController()
    fortuneRequest.current = controller
    setRequestedFortuneScope(scope)
    setIsLoadingFortune(true)
    setFortuneError(null)
    try {
      if (startDate !== endDate) {
        const result = await postJson<TransitWindowResponse>('/v1/transits/window', {
          birth: payload, start_date: startDate, end_date: endDate,
        }, controller, '周期运势服务暂时不可用。')
        if (fortuneRequest.current !== controller) return
        setWindowTransit(result)
        setDaily(null)
        setPeriods(null)
        setFortuneScope(scope)
        return
      }
      const [nextDaily, nextPeriods] = await Promise.allSettled([
        postJson<DailyTransitResponse>('/v1/transits/daily', { birth: payload, transit_date: startDate }, controller, '运势事实服务暂时不可用。'),
        postJson<TransitResponse>('/v1/transits', { birth: payload, transit_date: startDate }, controller, '时间层事实服务暂时不可用。'),
      ])
      if (fortuneRequest.current !== controller) return
      if (nextDaily.status === 'rejected') throw nextDaily.reason
      setDaily(nextDaily.value)
      setPeriods(nextPeriods.status === 'fulfilled' ? nextPeriods.value : null)
      setWindowTransit(null)
      setFortuneScope(scope)
      if (nextPeriods.status === 'rejected') setFortuneError(`${period.label}基础结果已生成，时间层补充暂时不可用。`)
    } catch (reason) {
      if (fortuneRequest.current !== controller) return
      const message = requestError(reason, controller, '无法连接运势服务。')
      if (message) setFortuneError(message)
    } finally {
      if (fortuneRequest.current === controller) {
        fortuneRequest.current = null
        setIsLoadingFortune(false)
      }
    }
  }

  return <div className="app-shell" data-theme={theme.id} data-palette={theme.palette} data-layout={theme.layout} data-motion={theme.motion} data-motion-paused={motionPaused || undefined}>
    <a className="skip-link" href="#birth-form">跳到排盘表单</a>
    <header className="site-header">
      <a className="brand" href="#top"><strong>看运</strong><span>FORTUNE, BUT MEME</span></a>
      <nav aria-label="主导航"><a href="#start">排盘</a><a href="#analysis">专项</a><a href="#fortune">运势</a><a href="#saved">保存</a></nav>
      <ThemeRemote activeTheme={themeId} motionPaused={motionPaused} onSelect={selectTheme} onToggleMotion={toggleMotion} />
    </header>

    <main id="top">
      <section className="launch-section" id="start">
        <div className="launch-copy">
          <p className="eyebrow">当前主题 · {theme.navLabel}</p>
          <h1>{theme.headline}</h1>
          <p className="launch-deck">{theme.deck}</p>
          <BirthForm isSubmitting={isSubmitting} error={error} onSubmit={submit} onClear={clearSession} />
        </div>
        <MemeStage theme={theme} motionPaused={motionPaused} />
      </section>

      <section className="chart-section" id="chart" ref={chartSectionRef} tabIndex={-1}>
        <header className="content-heading compact-heading"><span>命盘底稿</span><h2>先把基础盘算清楚。</h2><p>固定时间口径、星历与规则包；主题只改变呈现，不参与计算。</p></header>
        <div className="chart-output" aria-live="polite">
          {error && !chart && <div className="chart-error"><WarningCircle size={28} weight="fill" /><div><strong>排盘没有完成</strong><p>{error}</p></div></div>}
          {isSubmitting && !chart && <div className="chart-loading" role="status"><span /><span /><span /><p>校准时间、经纬度与规则中</p></div>}
          {isSubmitting && chart && <div className="updating-status" role="status">正在按新资料更新，上一份有效命盘暂时保留。</div>}
          {chart && <Chart chart={chart} />}
          {!isSubmitting && !chart && !error && <div className="chart-empty">
            <div className="empty-meme"><MemeMedia source={theme.stickers[1] ?? theme.mainMedia} /></div>
            <div><span>NO CHART YET</span><h3>先排盘，再展开两大功能。</h3><p>四柱、紫微宫位与计算轨迹会先在这里出现，随后可以按需分析专项与运势。</p></div>
          </div>}
        </div>
      </section>

      <DomainAnalysisConsole chart={chart} onSave={saveReading} />
      <FortuneConsole
        chartReady={Boolean(chart)} daily={daily} periods={periods} windowTransit={windowTransit}
        scope={fortuneScope} requestedScope={requestedFortuneScope} error={fortuneError} isLoading={isLoadingFortune} theme={theme}
        onRequest={(scope) => void loadFortune(scope)}
        onSave={saveReading}
      />
      <SavedReadings items={savedReadings} onRemove={removeSaved} onClear={clearSaved} />
    </main>

    <footer className="site-footer">
      <div><strong>看运</strong><span>认真计算，随便长相。</span></div>
      <p>传统解释框架，不构成医疗、法律或投资建议。</p>
      <span><CheckCircle size={17} weight="fill" /> 主题不参与计算</span>
    </footer>

    {savedNotice && <div className="save-toast" role="status"><CheckCircle size={18} weight="fill" />{savedNotice}</div>}
    {isThemeChanging && <div className="theme-wipe" aria-hidden="true"><span>{theme.navLabel}</span></div>}
  </div>
}
