import { ArrowRight, FloppyDisk, SpinnerGap } from '@phosphor-icons/react'
import type { DailyTransitResponse, FortuneScope, SaveDraft, TransitResponse, TransitWindowResponse } from '../types'
import { fortuneScopes } from '../types'
import type { ThemeConfig } from '../themes'
import type { AiExplainSource } from '../types'
import { AiExplainPanel } from './AiExplainPanel'
import { MemeMedia } from './MemeMedia'

const relationLabels = { branch_clash: '地支冲', branch_combination: '地支合', branch_same: '同支' }
const periodLabels = { great_luck: '大运', year: '流年', month: '流月', day: '流日' }

type FortuneProps = {
  chartReady: boolean
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
  const { chartReady, daily, periods, windowTransit, scope, requestedScope, error, isLoading, theme, onRequest, onSave } = props
  const selectedLabel = fortuneScopes.find(([key]) => key === scope)?.[1] ?? '今日'
  const requestedLabel = fortuneScopes.find(([key]) => key === requestedScope)?.[1] ?? '今日'
  const windowDays = windowTransit?.transit.daily ?? []
  const windowFacts = windowDays.flatMap((day) => day.facts)
  const supportCount = windowFacts.filter((fact) => fact.relation === 'branch_combination').length
  const tensionCount = windowFacts.filter((fact) => fact.relation === 'branch_clash').length
  const sameCount = windowFacts.filter((fact) => fact.relation === 'branch_same').length
  const activeDays = windowDays.filter((day) => day.facts.length)
  const hasReading = Boolean(daily || windowTransit)
  const windowRead = tensionCount > supportCount
    ? '冲关系更集中，重要选择适合拆成较小、可验证的步骤。'
    : supportCount > tensionCount
      ? '合关系更多，适合推进协作、整理关系和完成衔接事项。'
      : '冲合信号没有形成单边倾向，保持既定节奏即可。'
  const dailyRead = daily?.transit.facts.length
    ? daily.transit.facts.map((fact) => `${relationLabels[fact.relation]}：${fact.natal_pillar} / ${fact.transit_pillar}`).join('；')
    : '未检测到已定义的地支冲、合或同支关系。'

  const aiSource: AiExplainSource | null = daily ? {
    key: `daily-${daily.trace_id}-${scope}`,
    kind: 'fortune',
    title: `${selectedLabel}运势 · 日柱 ${daily.transit.day_pillar}`,
    summary: dailyRead,
    facts: daily.ai_context && periods?.ai_context
      ? [...daily.ai_context.facts, ...periods.ai_context.facts].slice(0, 12)
      : daily.ai_context?.facts ?? [
      { id: 'fortune-1', text: `${daily.transit.transit_date}的日柱为${daily.transit.day_pillar}` },
      ...(daily.transit.facts.length
        ? daily.transit.facts.map((fact) => `${relationLabels[fact.relation]}：${fact.natal_pillar} / ${fact.transit_pillar}`)
        : ['该日未检测到已定义的地支冲、合或同支关系']),
      ...(periods?.transit.layers.map((layer) => `${periodLabels[layer.period]}为${layer.pillar}${layer.facts.length ? `，出现${layer.facts.map((fact) => relationLabels[fact.relation]).join('、')}` : '，未出现已定义关系'}`) ?? []),
      ...(periods?.transit.insights.map((insight) => `${insight.title}：${insight.summary}；${insight.action}`) ?? []),
    ].slice(0, 12).map((text, index) => typeof text === 'string' ? { id: `fortune-${index + 1}`, text } : text),
    contextTokens: [daily.ai_context?.token, periods?.ai_context?.token].filter((token): token is string => Boolean(token)),
  } : windowTransit ? {
    key: `window-${windowTransit.trace_id}-${scope}`,
    kind: 'fortune',
    title: `${selectedLabel}运势 · ${windowTransit.transit.start_date} 至 ${windowTransit.transit.end_date}`,
    summary: `共覆盖 ${windowDays.length} 天，其中 ${activeDays.length} 天出现可追溯关系。${windowRead}`,
    facts: windowTransit.ai_context?.facts ?? [
      `时间范围为${windowTransit.transit.start_date}至${windowTransit.transit.end_date}，共${windowDays.length}天`,
      `其中${activeDays.length}天出现可追溯关系`,
      `地支合${supportCount}次，地支冲${tensionCount}次，同支${sameCount}次`,
      ...activeDays.map((day) => `${day.transit_date}：${day.facts.map((fact) => relationLabels[fact.relation]).join('、')}`),
    ].slice(0, 12).map((text, index) => ({ id: `fortune-${index + 1}`, text })),
    contextTokens: windowTransit.ai_context ? [windowTransit.ai_context.token] : [],
  } : null

  function saveFortune() {
    if (isLoading) return
    if (daily) {
      const layerDetails = periods?.transit.layers.map((layer) => `${periodLabels[layer.period]} ${layer.pillar}${layer.facts.length ? ` · ${layer.facts.map((fact) => relationLabels[fact.relation]).join('、')}` : ''}`) ?? []
      const insightDetails = periods?.transit.insights.map((insight) => `${insight.title}：${insight.action}`) ?? []
      onSave({
        kind: 'fortune', title: `${selectedLabel}运势 · 日柱 ${daily.transit.day_pillar}`,
        summary: dailyRead, details: [...layerDetails, ...insightDetails],
      })
    } else if (windowTransit) {
      onSave({
        kind: 'fortune', title: `${selectedLabel}运势 · ${windowTransit.transit.start_date} 至 ${windowTransit.transit.end_date}`,
        summary: `共覆盖 ${windowDays.length} 天，其中 ${activeDays.length} 天出现可追溯关系。${windowRead}`,
        details: [`地支合 ${supportCount} 次 · 地支冲 ${tensionCount} 次 · 同支 ${sameCount} 次`, ...activeDays.slice(0, 12).map((day) => `${day.transit_date} · ${day.facts.map((fact) => relationLabels[fact.relation]).join('、')}`)],
      })
    }
  }

  return <section className="fortune-section" id="fortune" aria-label="时间范围">
    <div className={`fortune-console ${chartReady ? 'is-ready' : ''}`} aria-live="polite">
      {!chartReady ? <div className="fortune-empty">
        <div className="reaction-frame"><MemeMedia source={theme.stickers[0] ?? theme.mainMedia} /></div>
        <div><span>WAITING FOR CHART</span><h3>先完成排盘</h3><a href="#birth-form">去填写资料 <ArrowRight size={18} /></a></div>
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
          {daily && <div className="fortune-reading">
            <header><div><span>{daily.transit.transit_date}</span><h3>日柱 {daily.transit.day_pillar}</h3></div></header>
            <p className="reading-lead">{dailyRead}</p>
            {periods && <div className="fortune-layers">{periods.transit.layers.map((layer) => <span key={layer.period}><small>{periodLabels[layer.period]}</small><b>{layer.pillar}</b>{layer.facts.length > 0 && <i>{layer.facts.map((fact) => relationLabels[fact.relation]).join('、')}</i>}</span>)}</div>}
            {periods?.transit.insights.length ? <div className="fortune-insights">{periods.transit.insights.map((insight) => <article key={insight.insight_id}><h4>{insight.title}</h4><p>{insight.summary}</p><strong>{insight.action}</strong></article>)}</div> : null}
            <button className="reading-save" type="button" disabled={isLoading} onClick={saveFortune}><FloppyDisk size={18} weight="bold" /> 保存{selectedLabel}运势</button>
            {aiSource && <AiExplainPanel source={aiSource} defaultQuestion={`请把${selectedLabel}运势讲得更直白，并指出我最值得注意的一件事。`} />}
          </div>}
          {windowTransit && <div className="fortune-reading window-reading">
            <header><div><span>{windowTransit.transit.start_date} 至 {windowTransit.transit.end_date}</span><h3>{selectedLabel}时间窗口</h3></div></header>
            <p className="reading-lead">共 {windowDays.length} 天，{activeDays.length} 天出现可追溯关系。{windowRead}</p>
            <div className="fortune-counts"><span><b>{supportCount}</b>合</span><span><b>{tensionCount}</b>冲</span><span><b>{sameCount}</b>同支</span></div>
            {activeDays.length > 0 && <div className="active-dates">{activeDays.slice(0, 12).map((day) => <span key={day.transit_date}><b>{day.transit_date.slice(5)}</b>{day.facts.map((fact) => relationLabels[fact.relation]).join('、')}</span>)}</div>}
            <button className="reading-save" type="button" disabled={isLoading} onClick={saveFortune}><FloppyDisk size={18} weight="bold" /> 保存{selectedLabel}运势</button>
            {aiSource && <AiExplainPanel source={aiSource} defaultQuestion={`请把${selectedLabel}时间窗口讲得更直白，并指出最值得安排的一件事。`} />}
          </div>}
        </div>
      </>}
    </div>
  </section>
}
