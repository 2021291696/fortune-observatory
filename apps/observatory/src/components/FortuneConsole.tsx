import { ArrowRight, FloppyDisk, Lightning, SpinnerGap } from '@phosphor-icons/react'
import type { DailyTransitResponse, FortuneScope, SaveDraft, TransitResponse, TransitWindowResponse } from '../types'
import { fortuneScopes } from '../types'
import type { ThemeConfig } from '../themes'
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

  return <section className="fortune-section" id="fortune">
    <header className="content-heading">
      <span>02 / 六种运势</span>
      <h2>排完今天自动看，其他周期你来点。</h2>
      <p>今日在命盘完成后自动分析。明日、本周、下周、本月和下月，只有你主动要求时才计算。</p>
    </header>
    <div className={`fortune-console ${chartReady ? 'is-ready' : ''}`} aria-live="polite">
      {!chartReady ? <div className="fortune-empty">
        <div className="reaction-frame"><MemeMedia source={theme.stickers[0] ?? theme.mainMedia} /></div>
        <div><span>WAITING FOR CHART</span><h3>先完成上面的排盘。</h3><p>命盘验证完成后，今日运势会自动在这里出现。</p><a href="#birth-form">去填写资料 <ArrowRight size={18} /></a></div>
      </div> : <>
        <div className="fortune-toolbar">
          <div><Lightning size={19} weight="fill" /><span>{selectedLabel}分析</span><small>{isLoading ? `正在生成${requestedLabel}` : scope === 'today' ? '排盘后自动' : '按你的要求'}</small></div>
          <div className="fortune-scopes" role="group" aria-label="选择运势周期">
            {fortuneScopes.map(([key, label]) => <button
              key={key}
              type="button"
              className={(isLoading || error ? requestedScope : scope) === key ? 'is-active' : ''}
              aria-pressed={(isLoading || error ? requestedScope : scope) === key}
              disabled={isLoading}
              onClick={() => onRequest(key)}
            >{label}{key === 'today' && <small>自动</small>}</button>)}
          </div>
        </div>
        <div className="fortune-output">
          {isLoading && <div className={hasReading ? 'fortune-refreshing' : 'fortune-loading'} role="status"><SpinnerGap className="spin" size={28} /><strong>正在读取干支关系与时间层</strong><span>{hasReading ? '上一份有效结果暂时保留。' : '这一步只使用已经生成的命盘事实。'}</span></div>}
          {error && <div className="fortune-error"><strong>{error.includes('已生成') ? '部分结果已生成' : `${requestedLabel}这次没算出来`}</strong><p>{error}</p><button type="button" disabled={isLoading} onClick={() => onRequest(requestedScope)}>重试{requestedLabel}</button></div>}
          {daily && <div className="fortune-reading">
            <header><div><span>{daily.transit.transit_date}</span><h3>日柱 {daily.transit.day_pillar}</h3></div><em>{daily.transit.verification_status === 'verified' ? '已验证' : '待验证'}</em></header>
            <p className="reading-lead">{dailyRead}</p>
            {periods && <div className="fortune-layers">{periods.transit.layers.map((layer) => <span key={layer.period}><small>{periodLabels[layer.period]}</small><b>{layer.pillar}</b>{layer.facts.length > 0 && <i>{layer.facts.map((fact) => relationLabels[fact.relation]).join('、')}</i>}</span>)}</div>}
            {periods?.transit.insights.length ? <div className="fortune-insights">{periods.transit.insights.map((insight) => <article key={insight.insight_id}><h4>{insight.title}</h4><p>{insight.summary}</p><strong>{insight.action}</strong><small>依据：{insight.fact_ids.join('、')}</small></article>)}</div> : null}
            <button className="reading-save" type="button" disabled={isLoading} onClick={saveFortune}><FloppyDisk size={18} weight="bold" /> 保存{selectedLabel}运势</button>
          </div>}
          {windowTransit && <div className="fortune-reading window-reading">
            <header><div><span>{windowTransit.transit.start_date} 至 {windowTransit.transit.end_date}</span><h3>{selectedLabel}时间窗口</h3></div><em>{windowTransit.transit.verification_status === 'verified' ? '已验证' : '待验证'}</em></header>
            <p className="reading-lead">共覆盖 {windowDays.length} 天，其中 {activeDays.length} 天出现可追溯关系。{windowRead}</p>
            <div className="fortune-counts"><span><b>{supportCount}</b>合</span><span><b>{tensionCount}</b>冲</span><span><b>{sameCount}</b>同支</span></div>
            {activeDays.length > 0 && <div className="active-dates">{activeDays.slice(0, 12).map((day) => <span key={day.transit_date}><b>{day.transit_date.slice(5)}</b>{day.facts.map((fact) => relationLabels[fact.relation]).join('、')}</span>)}</div>}
            <button className="reading-save" type="button" disabled={isLoading} onClick={saveFortune}><FloppyDisk size={18} weight="bold" /> 保存{selectedLabel}运势</button>
          </div>}
        </div>
      </>}
    </div>
  </section>
}
