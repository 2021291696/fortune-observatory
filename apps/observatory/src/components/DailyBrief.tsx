import { ArrowClockwise, SpinnerGap, WarningCircle } from '@phosphor-icons/react'
import type { DailyTransitResponse, TransitResponse } from '../types'

const relationLabels = {
  branch_clash: '地支冲',
  branch_combination: '地支合',
  branch_same: '同支',
}

const periodLabels = {
  great_luck: '当前大运',
  year: '流年',
  month: '流月',
  day: '流日',
}

export function DailyBrief({
  daily,
  periods,
  error,
  isLoading,
  onRetry,
}: {
  daily: DailyTransitResponse | null
  periods: TransitResponse | null
  error: string | null
  isLoading: boolean
  onRetry: () => void
}) {
  const facts = daily?.transit.facts ?? []
  const primaryFact = facts[0]
  const greatLuck = periods?.transit.layers.find((layer) => layer.period === 'great_luck')
  const action = periods?.transit.insights[0]?.action

  return <section className="daily-brief" id="today-brief" aria-label="今日结果" tabIndex={-1}>
    {isLoading && !daily && <div className="daily-brief-loading" role="status">
      <SpinnerGap className="spin" size={24} />
      <div><strong>正在计算今日运势</strong></div>
    </div>}

    {error && !daily && <div className="daily-brief-error" role="alert">
      <div><strong>今日结果暂时没有生成</strong><span>{error}</span></div>
      <button type="button" onClick={onRetry}><ArrowClockwise size={18} weight="bold" /> 重试</button>
    </div>}

    {daily && error && <div className="daily-brief-partial" role="status">
      <WarningCircle size={19} weight="fill" />
      <span><strong>今日基础结果已生成，详细时间层暂不可用。</strong>{error}</span>
      <button type="button" onClick={onRetry}><ArrowClockwise size={17} weight="bold" /> 重试时间层</button>
    </div>}

    {daily && <>
      <article className="daily-card daily-card-primary">
        <strong>{action ?? (error ? '详细建议暂不可用' : periods ? '本次不生成行动建议' : '等待详细时间层')}</strong>
        <p>{periods?.transit.insights[0]?.summary ?? (error ? '详细建议暂不可用。' : '当前没有足够事实支持额外建议。')}</p>
      </article>
      <div className="daily-brief-grid" aria-live="polite">
        <article className="daily-card">
          <strong>{primaryFact ? relationLabels[primaryFact.relation] : '未见已定义关系'}</strong>
          <p>{primaryFact
            ? `${primaryFact.natal_pillar} 与 ${primaryFact.transit_pillar}，共 ${facts.length} 条可追溯事实`
            : '未检测到地支冲、合或同支。'}</p>
        </article>
        <article className="daily-card">
          <strong>{daily.transit.transit_date}</strong>
          <b>日柱 {daily.transit.day_pillar}</b>
        </article>
        <article className="daily-card">
          <strong>{greatLuck ? `${periodLabels[greatLuck.period]} ${greatLuck.pillar}` : error ? '详细时间层暂不可用' : '等待时间层'}</strong>
          <p>{periods
            ? `流年、流月、流日均已按 ${daily.transit.transit_date} 计算。`
            : error ? '详细时间层暂不可用。' : '详细时间层仍在读取。'}</p>
        </article>
      </div>
    </>}
  </section>
}
