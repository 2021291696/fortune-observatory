import { ArrowRight, FloppyDisk, SpinnerGap } from '@phosphor-icons/react'
import { useMemo, useState } from 'react'
import type { DailyTransitResponse, FortuneScope, SaveDraft, TransitResponse, TransitWindowResponse } from '../types'
import { fortuneScopes } from '../types'
import type { ThemeConfig } from '../themes'
import { factDomain, plainFactLine, termGlossary } from '../terminology'
import type { AiExplainSource } from '../types'
import { AiExplainPanel } from './AiExplainPanel'
import { MemeCompanion } from './MemeCompanion'
import { MemeMedia } from './MemeMedia'

const relationLabels = { branch_clash: '地支冲', branch_combination: '地支合', branch_same: '同支' }
const periodLabels = { great_luck: '大运', year: '流年', month: '流月', day: '流日' }

type DayFact = { fact_id: string; relation: 'branch_clash' | 'branch_combination' | 'branch_same'; natal_pillar: string; transit_pillar: string }

function dayPlain(facts: DayFact[]) {
  const clash = facts.filter((fact) => fact.relation === 'branch_clash')
  const comb = facts.filter((fact) => fact.relation === 'branch_combination')
  const mainClash = clash[0]
  const mainComb = comb[0]
  if (clash.length > comb.length && mainClash) {
    return {
      keyword: '变动日', tone: 'tension' as const,
      line: `今天（${mainClash.transit_pillar}）与你的${mainClash.natal_pillar}相冲，主要牵动${factDomain(mainClash)}——节奏容易被外力打断，重大决定和签署先放一放，把大任务拆成小块推进更稳。`,
    }
  }
  if (clash.length > comb.length) return {
    keyword: '变动日', tone: 'tension' as const,
    line: '这天节奏容易被外力打断、意见分歧变多——重大决定和签署先放一放，把大任务拆成小块推进会更稳。',
  }
  if (comb.length > clash.length && mainComb) {
    return {
      keyword: '顺合日', tone: 'support' as const,
      line: `今天（${mainComb.transit_pillar}）与你的${mainComb.natal_pillar}相合，主要牵动${factDomain(mainComb)}——适合主动沟通、修复关系、推进合作，把话说开更容易成。`,
    }
  }
  if (comb.length > clash.length) return {
    keyword: '顺合日', tone: 'support' as const,
    line: '这天与人协作、修复关系、推进合作都比较顺，适合主动沟通和把话说开。',
  }
  if (facts.length) return {
    keyword: '平稳日', tone: 'neutral' as const,
    line: '这天与命盘只是同气重复，没有明显冲合——按既定安排走就好。',
  }
  return {
    keyword: '平常日', tone: 'plain' as const,
    line: '这天与命盘没有已定义的冲合关系，平常节奏安排即可。',
  }
}

const weekdayLabels = ['一', '二', '三', '四', '五', '六', '日']

type FortuneProps = {
  chartReady: boolean
  aiOwner: string
  daily: DailyTransitResponse | null
  periods: TransitResponse | null
  windowTransit: TransitWindowResponse | null
  scope: FortuneScope
  requestedScope: FortuneScope
  error: string | null
  isLoading: boolean
  theme: ThemeConfig
  onRequest: (scope: FortuneScope) => void
  onSave: (draft: SaveDraft) => void
}

export function FortuneConsole(props: FortuneProps) {
  const { chartReady, aiOwner, daily, periods, windowTransit, scope, requestedScope, error, isLoading, theme, onRequest, onSave } = props
  const selectedLabel = fortuneScopes.find(([key]) => key === scope)?.[1] ?? '今日'
  const requestedLabel = fortuneScopes.find(([key]) => key === requestedScope)?.[1] ?? '今日'
  const windowDays = windowTransit?.transit.daily ?? []
  const windowFacts = windowDays.flatMap((day) => day.facts)
  const supportCount = windowFacts.filter((fact) => fact.relation === 'branch_combination').length
  const tensionCount = windowFacts.filter((fact) => fact.relation === 'branch_clash').length
  const sameCount = windowFacts.filter((fact) => fact.relation === 'branch_same').length
  const activeDays = windowDays.filter((day) => day.facts.length)
  const hasReading = Boolean(daily || windowTransit)
  const todayKey = new Date().toISOString().slice(0, 10)
  const dailyRead = daily?.transit.facts.length
    ? daily.transit.facts.map((fact) => plainFactLine(fact)).join('；')
    : '未检测到已定义的地支冲、合或同支关系。'
  const plain = daily ? dayPlain(daily.transit.facts as DayFact[]) : null

  const dailyAi: AiExplainSource | null = daily ? {
    key: `daily-${daily.trace_id}-${scope}`,
    kind: 'fortune',
    title: `${selectedLabel}运势 · 流日 ${daily.transit.day_pillar}`,
    summary: dailyRead,
    facts: daily.ai_context?.facts ?? [],
    // Single token keeps the prompt compact; the period facts stay folded under
    // 查看依据 instead of slowing the auto reading past the provider budget.
    contextTokens: daily.ai_context ? [daily.ai_context.token] : [],
  } : null

  function saveFortune() {
    if (isLoading) return
    if (daily) {
      const layerDetails = periods?.transit.layers.map((layer) => `${periodLabels[layer.period]} ${layer.pillar}${layer.facts.length ? ` · ${layer.facts.map((fact) => relationLabels[fact.relation]).join('、')}` : ''}`) ?? []
      const insightDetails = periods?.transit.insights.map((insight) => `${insight.title}：${insight.action}`) ?? []
      onSave({
        kind: 'fortune', title: `${selectedLabel}运势 · 流日 ${daily.transit.day_pillar}`,
        summary: dailyRead, details: [...layerDetails, ...insightDetails],
      })
    } else if (windowTransit) {
      onSave({
        kind: 'fortune', title: `${selectedLabel}运势 · ${windowTransit.transit.start_date} 至 ${windowTransit.transit.end_date}`,
        summary: `共覆盖 ${windowDays.length} 天，其中 ${activeDays.length} 天出现可追溯关系。`,
        details: [`地支合 ${supportCount} 次 · 地支冲 ${tensionCount} 次 · 同支 ${sameCount} 次`, ...activeDays.slice(0, 12).map((day) => `${day.transit_date} · ${day.facts.map((fact) => relationLabels[fact.relation]).join('、')}`)],
      })
    }
  }

  return <section className="fortune-section" aria-label="时间范围">
    <div className={`fortune-console ${chartReady ? 'is-ready' : ''}`} aria-live="polite">
      {!chartReady ? <div className="fortune-empty">
        <div className="reaction-frame"><MemeMedia source={theme.stickers[0] ?? theme.mainMedia} /></div>
        <div><h3>命盘还没就绪</h3><a href="#birth-form">填写资料开始 <ArrowRight size={18} /></a></div>
      </div> : <>
        <div className="fortune-toolbar">
          <div className="fortune-scopes" role="group" aria-label="选择运势周期">
            {fortuneScopes.map(([key, label]) => <button
              key={key}
              type="button"
              className={(isLoading || error ? requestedScope : scope) === key ? 'is-active' : ''}
              aria-pressed={(isLoading || error ? requestedScope : scope) === key}
              disabled={isLoading}
              onClick={() => onRequest(key)}
            >{label}</button>)}
          </div>
        </div>
        <div className="fortune-output">
          {isLoading && <div className={hasReading ? 'fortune-refreshing' : 'fortune-loading'} role="status"><SpinnerGap className="spin" size={28} /><strong>正在计算{requestedLabel}</strong>{hasReading && <span>上一份结果暂时保留</span>}</div>}
          {error && <div className="fortune-error"><strong>{error.includes('已生成') ? '部分结果已生成' : `${requestedLabel}这次没算出来`}</strong><p>{error}</p><button type="button" disabled={isLoading} onClick={() => onRequest(requestedScope)}>重试{requestedLabel}</button></div>}

          {daily && plain && <div className="fortune-reading">
            <MemeCompanion theme={theme} />
            <header><div><span>{daily.transit.transit_date}</span><h3>流日 {daily.transit.day_pillar}</h3></div><span className={`day-tone is-${plain.tone}`}>{plain.keyword}</span></header>
            <p className="reading-lead">{plain.line}</p>
            {daily.ziwei_yearly && <div className="yearly-ziwei">
              <span className="yz-pill" title={termGlossary['流年四化']}>{daily.ziwei_yearly.year_pillar}年 · 虚岁{daily.ziwei_yearly.nominal_age}</span>
              <p>{daily.ziwei_yearly.yearly_mutagens.map((entry) => {
                const label = entry.palace_name || entry.palace_branch
                return `${entry.star}化${entry.mutagen}入${label.endsWith('宫') ? label : `${label}宫`}`
              }).join('；')}</p>
              <small title={termGlossary[daily.ziwei_yearly.decadal.is_childhood ? '童限' : '大限']}>
                {daily.ziwei_yearly.decadal.is_childhood
                  ? `童限行${daily.ziwei_yearly.decadal.branch}宫`
                  : `大限${daily.ziwei_yearly.decadal.stem}${daily.ziwei_yearly.decadal.branch} · ${daily.ziwei_yearly.decadal.start_age}-${daily.ziwei_yearly.decadal.end_age}岁`}
              </small>
            </div>}
            {dailyAi && <AiExplainPanel
              auto
              cacheKey={`ai-${aiOwner}-${daily.transit.transit_date}`}
              source={dailyAi}
              defaultQuestion={`请把我的${selectedLabel}运势（${daily.transit.transit_date}，流日${daily.transit.day_pillar}）讲成一段直白的白话解读，告诉我今天最值得注意的一件事和一件适合先做的小事。`}
            />}
            <details className="fact-details"><summary>查看依据（流年流月流日与冲合明细）</summary>
              <p>{dailyRead}</p>
              {periods && <div className="fortune-layers">{periods.transit.layers.map((layer) => <span key={layer.period}><small>{periodLabels[layer.period]}</small><b>{layer.pillar}</b>{layer.facts.length > 0 && <i>{layer.facts.map((fact) => relationLabels[fact.relation]).join('、')}</i>}</span>)}</div>}
              {periods?.transit.insights.length ? <div className="fortune-insights">{periods.transit.insights.map((insight) => <article key={insight.insight_id}><h4>{insight.title}</h4><p>{insight.summary}</p><strong>{insight.action}</strong></article>)}</div> : null}
            </details>
            <button className="reading-save" type="button" disabled={isLoading} onClick={saveFortune}><FloppyDisk size={18} weight="bold" /> 保存{selectedLabel}运势</button>
          </div>}

          {windowTransit && <CalendarView
            windowTransit={windowTransit}
            todayKey={todayKey}
            aiOwner={aiOwner}
            selectedLabel={selectedLabel}
            onSave={saveFortune}
            isLoading={isLoading}
          />}
        </div>
      </>}
    </div>
  </section>
}

function CalendarView({ windowTransit, todayKey, aiOwner, selectedLabel, onSave, isLoading }: {
  windowTransit: TransitWindowResponse
  todayKey: string
  aiOwner: string
  selectedLabel: string
  onSave: () => void
  isLoading: boolean
}) {
  const days = windowTransit.transit.daily
  const [selectedDate, setSelectedDate] = useState(() => {
    const hit = days.find((day) => day.transit_date === todayKey && day.facts.length)
    return hit?.transit_date ?? days.find((day) => day.facts.length)?.transit_date ?? days[0]?.transit_date ?? todayKey
  })
  const selected = days.find((day) => day.transit_date === selectedDate) ?? days[0]
  const selectedPlain = selected ? dayPlain(selected.facts as DayFact[]) : null

  const isMonth = (days.length) > 10
  const leadingBlanks = useMemo(() => {
    if (!isMonth || !days.length) return 0
    const first = new Date(`${days[0].transit_date}T00:00:00`)
    return (first.getDay() + 6) % 7
  }, [isMonth, days])

  const selectedAi: AiExplainSource | null = selected && windowTransit.ai_context ? {
    key: `window-${windowTransit.trace_id}-${selected.transit_date}`,
    kind: 'fortune',
    title: `${selected.transit_date}运势`,
    summary: `${selected.transit_date}：${selected.facts.map((fact) => relationLabels[fact.relation]).join('、') || '无已定义关系'}`,
    facts: windowTransit.ai_context.facts,
    contextTokens: [windowTransit.ai_context.token],
  } : null

  const clashDays = days.filter((day) => day.facts.filter((f) => f.relation === 'branch_clash').length > day.facts.filter((f) => f.relation === 'branch_combination').length).length
  const smoothDays = days.filter((day) => day.facts.filter((f) => f.relation === 'branch_combination').length > day.facts.filter((f) => f.relation === 'branch_clash').length).length

  return <div className="fortune-reading window-reading calendar-reading">
    <header><div><span>{windowTransit.transit.start_date} 至 {windowTransit.transit.end_date}</span><h3>{selectedLabel}日历</h3></div><span className="calendar-legend"><i className="lg-tension" />变动 {clashDays}<i className="lg-support" />顺合 {smoothDays}</span></header>
    <div className={`calendar-grid ${isMonth ? 'is-month' : 'is-week'}`} role="grid" aria-label="每日冲合日历">
      {isMonth && weekdayLabels.map((label) => <b key={label} className="calendar-weekday">周{label}</b>)}
      {Array.from({ length: leadingBlanks }, (_, index) => <span key={`blank-${index}`} className="calendar-cell is-blank" />)}
      {days.map((day) => {
        const tone = dayPlain(day.facts as DayFact[]).tone
        return <button
          key={day.transit_date}
          type="button"
          className={`calendar-cell is-${tone} ${day.transit_date === selectedDate ? 'is-selected' : ''} ${day.transit_date === todayKey ? 'is-today' : ''}`}
          onClick={() => setSelectedDate(day.transit_date)}
        >
          <b>{Number(day.transit_date.slice(8))}</b>
          <i>{dayPlain(day.facts as DayFact[]).keyword}</i>
        </button>
      })}
    </div>

    {selected && selectedPlain && <div className="day-card">
      <header><strong>{selected.transit_date}{selected.transit_date === todayKey ? ' · 今天' : ''}</strong><span className={`day-tone is-${selectedPlain.tone}`}>{selectedPlain.keyword}</span></header>
      <p>{selectedPlain.line}</p>
      {selectedAi && <AiExplainPanel
        auto
        cacheKey={`ai-${aiOwner}-${selected.transit_date}`}
        source={selectedAi}
        defaultQuestion={`请讲讲 ${selected.transit_date} 这一天我的运势，用白话说清该注意什么、适合先做什么。`}
      />}
      <details className="fact-details"><summary>查看依据</summary><p>{selected.facts.length ? selected.facts.map((fact) => `${relationLabels[fact.relation]}：${fact.natal_pillar} / ${fact.transit_pillar}`).join('；') : '该日未检测到已定义的冲合关系。'}</p></details>
    </div>}

    <button className="reading-save" type="button" disabled={isLoading} onClick={onSave}><FloppyDisk size={18} weight="bold" /> 保存{selectedLabel}概览</button>
  </div>
}
