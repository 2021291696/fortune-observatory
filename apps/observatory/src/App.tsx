import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { ArrowRight, CheckCircle, ShieldCheck, WarningCircle } from '@phosphor-icons/react'
import { AppNavigation, viewFromHash, type AppView } from './components/AppNavigation'
import { BirthForm } from './components/BirthForm'
import { Chart } from './components/Chart'
import { DailyBrief } from './components/DailyBrief'
import { DomainAnalysisConsole } from './components/DomainAnalysisConsole'
import { FortuneConsole } from './components/FortuneConsole'
import { MemeStage } from './components/MemeStage'
import { ProfileView } from './components/ProfileView'
import { birthPlaces } from './birthPlaces'
import { dateKey, fortuneWindow } from './dates'
import { resolveTheme, type ThemeId } from './themes'
import type { ChartResponse, DailyTransitResponse, FortuneScope, SavedReading, SaveDraft, TransitResponse, TransitWindowResponse } from './types'

const API_BASE = import.meta.env.VITE_API_BASE ?? (import.meta.env.PROD
  ? 'https://sol-d2ga5fpq8bcf67f5a.service.tcloudbase.com/destiny'
  : 'http://127.0.0.1:8000')
const REQUEST_TIMEOUT_MS = 20_000
const validThemes: ThemeId[] = ['phoebe', 'ggbond', 'nailong', 'kawaii', 'shuffle']
const SAVED_READINGS_KEY = 'fortune-saved-readings-v1'

function readLocalStorage(key: string) {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeLocalStorage(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value)
    return true
  } catch {
    return false
  }
}

const shanghaiClock = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
})

function shanghaiCivilCandidates(date: string, time: string) {
  const expected = `${date} ${time}`
  return ['+08:00', '+09:00'].map((offset) => {
    const timestamp = `${date}T${time}:00${offset}`
    const instant = new Date(timestamp)
    const values = Object.fromEntries(
      shanghaiClock.formatToParts(instant)
        .filter((part) => part.type !== 'literal')
        .map((part) => [part.type, part.value]),
    )
    const roundTrip = `${values.year}-${values.month}-${values.day} ${values.hour}:${values.minute}`
    return { timestamp, offset, roundTrip }
  }).filter((candidate) => candidate.roundTrip === expected)
}

type BirthPayload = {
  civil_datetime: string
  timezone_id: 'Asia/Shanghai'
  longitude: number
  latitude: number
  sex_for_rule: string
  use_apparent_solar_time: true
}

function initialTheme(): ThemeId {
  const saved = readLocalStorage('fortune-theme') as ThemeId | null
  return saved && validThemes.includes(saved) ? saved : 'nailong'
}

function initialSeed() {
  const saved = Number(readLocalStorage('fortune-shuffle-seed'))
  return Number.isFinite(saved) && saved > 0 ? saved : Math.floor(Math.random() * 1_000_000_000)
}

function initialSavedReadings(): SavedReading[] {
  try {
    const raw = readLocalStorage(SAVED_READINGS_KEY) ?? '[]'
    if (raw.length > 120_000) return []
    const parsed: unknown = JSON.parse(raw)
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
      writeLocalStorage(SAVED_READINGS_KEY, JSON.stringify(sanitized))
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
  const [activeView, setActiveView] = useState<AppView>(viewFromHash)
  const [themeId, setThemeId] = useState<ThemeId>(initialTheme)
  const [shuffleSeed, setShuffleSeed] = useState(initialSeed)
  const [isThemeChanging, setIsThemeChanging] = useState(false)
  const [motionPaused, setMotionPaused] = useState(() => readLocalStorage('fortune-motion-paused') === 'true')
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
  const autoScrolledChart = useRef<string | null>(null)

  useEffect(() => {
    const color = theme.palette === 'nailong' ? '#fff200' : theme.palette === 'ggbond' ? '#e31b23' : '#fffaf7'
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', color)
  }, [theme.palette])

  useEffect(() => {
    const syncView = () => setActiveView(viewFromHash())
    window.addEventListener('hashchange', syncView)
    window.addEventListener('popstate', syncView)
    return () => {
      window.removeEventListener('hashchange', syncView)
      window.removeEventListener('popstate', syncView)
    }
  }, [])

  useEffect(() => {
    window.requestAnimationFrame(() => window.scrollTo({ top: 0, behavior: 'auto' }))
  }, [activeView])

  useEffect(() => () => {
    chartRequest.current?.abort('unmount')
    fortuneRequest.current?.abort('unmount')
    if (themeTimer.current !== null) window.clearTimeout(themeTimer.current)
    if (noticeTimer.current !== null) window.clearTimeout(noticeTimer.current)
  }, [])

  useEffect(() => {
    if (activeView !== 'today' || !chart || (!daily && !fortuneError) || autoScrolledChart.current === chart.trace_id) return
    autoScrolledChart.current = chart.trace_id
    window.requestAnimationFrame(() => {
      const section = document.getElementById('today-brief')
      if (!section) return
      section.focus({ preventScroll: true })
      const headerHeight = document.querySelector<HTMLElement>('.site-header')?.offsetHeight ?? 0
      const top = section.getBoundingClientRect().top + window.scrollY - headerHeight
      window.scrollTo({
        top,
        behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      })
    })
  }, [activeView, chart, daily, fortuneError])

  function persistSaved(next: SavedReading[]) {
    if (writeLocalStorage(SAVED_READINGS_KEY, JSON.stringify(next))) {
      setSavedReadings(next)
      return true
    }
    showSavedNotice('本机存储不可用，未能保存这次结果')
    return false
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
      writeLocalStorage('fortune-shuffle-seed', String(nextSeed))
    }
    setIsThemeChanging(true)
    setThemeId(nextTheme)
    writeLocalStorage('fortune-theme', nextTheme)
    if (themeTimer.current !== null) window.clearTimeout(themeTimer.current)
    themeTimer.current = window.setTimeout(() => setIsThemeChanging(false), 460)
  }

  function toggleMotion() {
    setMotionPaused((current) => {
      const next = !current
      writeLocalStorage('fortune-motion-paused', String(next))
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
    const placeId = String(fields.get('placePreset') ?? '')
    let longitude: number
    let latitude: number
    if (placeId === 'manual') {
      longitude = Number(fields.get('longitude'))
      latitude = Number(fields.get('latitude'))
    } else {
      const place = birthPlaces.find((item) => item.id === placeId)
      longitude = place?.longitude ?? Number.NaN
      latitude = place?.latitude ?? Number.NaN
    }
    if (!civilDate || !civilTime) {
      setError('请完整填写出生日期与时间。')
      return
    }
    if (!Number.isFinite(longitude) || !Number.isFinite(latitude)
      || longitude < -180 || longitude > 180 || latitude < -90 || latitude > 90) {
      setError(placeId === 'manual' ? '请填写有效的经度（-180~180）与纬度（-90~90）。' : '请选择一个出生地。')
      return
    }
    const civilCandidates = shanghaiCivilCandidates(civilDate, civilTime)
    if (civilCandidates.length !== 1) {
      setError(civilCandidates.length === 0
        ? '这个当地时间处于历史时制跳变的空缺段，当前系统不会猜测不存在的时刻。'
        : '这个当地时间处于历史夏令时回拨的重叠段，当前系统不会替你猜测具体时刻。')
      return
    }
    const civilCandidate = civilCandidates[0]
    const payload: BirthPayload = {
      civil_datetime: civilCandidate.timestamp,
      timezone_id: 'Asia/Shanghai',
      longitude,
      latitude,
      sex_for_rule: String(fields.get('sexForRule')),
      use_apparent_solar_time: true,
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

  function navigate(view: AppView) {
    setActiveView(view)
  }

  return <div className="app-shell" data-theme={theme.id} data-palette={theme.palette} data-layout={theme.layout} data-motion={theme.motion} data-motion-paused={motionPaused || undefined}>
    <a className="skip-link" href="#main-content">跳到主要内容</a>
    <header className="site-header">
      <a className="brand" href="#today" onClick={() => navigate('today')}><strong>看运</strong></a>
      <AppNavigation activeView={activeView} onNavigate={navigate} />
      <span className={`session-state ${chart ? 'is-ready' : ''}`}>
        {chart ? <CheckCircle size={17} weight="fill" /> : <ShieldCheck size={17} weight="bold" />}
        {chart ? '今日已就绪' : '资料不默认保存'}
      </span>
    </header>

    <main id="main-content">
      {activeView === 'today' && <section className={`task-view today-view ${chart ? 'is-ready' : ''}`} id="today" aria-label="今日">
        <section className="launch-section" aria-label="填写出生资料">
          <div className="launch-copy">
            <BirthForm isSubmitting={isSubmitting} error={error} onSubmit={submit} onClear={clearSession} hasChart={Boolean(chart)} />
          </div>
          <MemeStage theme={theme} motionPaused={motionPaused} />
        </section>

        <div className="today-results">
          <DailyBrief
            chartReady={Boolean(chart)} daily={daily} periods={periods} error={fortuneError}
            isLoading={isLoadingFortune} onRetry={() => void loadFortune('today')}
          />
        </div>
      </section>}

      {activeView === 'ask' && <section className="task-view ask-view" id="ask" aria-labelledby="ask-title">
        <header className="task-heading">
          <h1 id="ask-title">问事</h1>
        </header>
        {!chart ? <div className="task-gate"><ShieldCheck size={34} weight="bold" /><div><strong>先完成一次排盘</strong></div><a href="#today" onClick={() => navigate('today')}>去填写资料 <ArrowRight size={18} /></a></div> : <>
          <DomainAnalysisConsole chart={chart} onSave={saveReading} />
          <FortuneConsole
            chartReady daily={daily} periods={periods} windowTransit={windowTransit}
            scope={fortuneScope} requestedScope={requestedFortuneScope} error={fortuneError} isLoading={isLoadingFortune} theme={theme}
            onRequest={(scope) => void loadFortune(scope)} onSave={saveReading}
          />
        </>}
      </section>}

      {activeView === 'chart' && <section className="task-view chart-view" id="chart" aria-labelledby="chart-title">
        <header className="task-heading"><h1 id="chart-title">命盘</h1></header>
        <div className="chart-output" aria-live="polite">
          {isSubmitting && chart && <div className="updating-status" role="status">正在按新资料更新，上一份有效命盘暂时保留。</div>}
          {chart ? <Chart chart={chart} /> : <div className="task-gate"><WarningCircle size={34} weight="bold" /><div><strong>这里还没有命盘</strong></div><a href="#today" onClick={() => navigate('today')}>去填写资料 <ArrowRight size={18} /></a></div>}
        </div>
      </section>}

      {activeView === 'profile' && <ProfileView
        activeTheme={themeId} motionPaused={motionPaused} savedReadings={savedReadings}
        onSelectTheme={selectTheme} onToggleMotion={toggleMotion}
        onRemoveSaved={removeSaved} onClearSaved={clearSaved}
      />}
    </main>

    <footer className="site-footer">
      <p>传统命理解释框架，不构成医疗、法律或投资建议。</p>
    </footer>

    {savedNotice && <div className="save-toast" role="status"><CheckCircle size={18} weight="fill" />{savedNotice}</div>}
    {isThemeChanging && <div className="theme-wipe" aria-hidden="true"><span>{theme.navLabel}</span></div>}
  </div>
}
