import { ArrowClockwise, CheckCircle, Lightning, ShieldCheck, SpinnerGap, WarningCircle } from '@phosphor-icons/react'
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
  chartReady,
  daily,
  periods,
  error,
  isLoading,
  onRetry,
}: {
  chartReady: boolean
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
  const verified = daily?.transit.verification_status === 'verified'

  return <section className="daily-brief" id="today-brief" aria-labelledby="daily-brief-title" tabIndex={-1}>
    <div className="daily-brief-heading">
      <div>
        <span><Lightning size={17} weight="fill" /> 排盘后自动生成</span>
        <h2 id="daily-brief-title">今天，先做这一件事。</h2>
      </div>
      <p><ShieldCheck size={17} weight="bold" /> 固定规则计算 · 结果可复现</p>
    </div>

    {!chartReady && <div className="daily-brief-empty">
      <strong>填写出生资料后，今日结果会出现在这里。</strong>
      <span>没有可靠事实就不生成结论，也不会用套话填空。</span>
    </div>}

    {chartReady && isLoading && !daily && <div className="daily-brief-loading" role="status">
      <SpinnerGap className="spin" size={24} />
      <div><strong>正在读取今天的干支关系</strong><span>命盘已完成，今日层正在计算。</span></div>
    </div>}

    {chartReady && error && !daily && <div className="daily-brief-error" role="alert">
      <div><strong>今日结果暂时没有生成</strong><span>{error}</span></div>
      <button type="button" onClick={onRetry}><ArrowClockwise size={18} weight="bold" /> 重试</button>
    </div>}

    {daily && error && <div className="daily-brief-partial" role="status">
      <WarningCircle size={19} weight="fill" />
      <span><strong>今日基础结果已生成，详细时间层暂不可用。</strong>{error}</span>
      <button type="button" onClick={onRetry}><ArrowClockwise size={17} weight="bold" /> 重试时间层</button>
    </div>}

    {daily && <><div className="daily-brief-grid" aria-live="polite">
      <article className="daily-card daily-card-primary daily-card-action">
        <span>今天可以先做</span>
        <strong>{action ?? (error ? '详细建议暂不可用' : periods ? '本次不生成行动建议' : '等待详细时间层')}</strong>
        <p>{periods?.transit.insights[0]?.summary
          ?? (error ? '时间层没有完整返回，系统不会用套话补写行动建议。' : '当前没有足够事实支持额外建议。')}</p>
      </article>
      <article className="daily-card">
        <span>主要关系信号</span>
        <strong>{primaryFact ? relationLabels[primaryFact.relation] : '未见已定义关系'}</strong>
        <p>{primaryFact
          ? `${primaryFact.natal_pillar} 与 ${primaryFact.transit_pillar}，共 ${facts.length} 条可追溯事实`
          : '未检测到地支冲、合或同支，不额外推断吉凶。'}</p>
      </article>
      <article className="daily-card">
        <span>今日计算状态</span>
        <strong>{daily.transit.transit_date}</strong>
        <b>日柱 {daily.transit.day_pillar}</b>
        <small className={verified ? 'is-verified' : ''}><CheckCircle size={15} weight="fill" />{verified ? '计算已核验' : '计算待核验'}</small>
      </article>
      <article className="daily-card">
        <span>当前时间层</span>
        <strong>{greatLuck ? `${periodLabels[greatLuck.period]} ${greatLuck.pillar}` : error ? '详细时间层暂不可用' : '等待时间层'}</strong>
        <p>{periods
          ? `流年、流月、流日均已按 ${daily.transit.transit_date} 计算。`
          : error ? '系统保留已经验证的日柱，不会用缺失数据补写大运。' : '基础日柱已经生成，详细时间层仍在读取。'}</p>
      </article>
    </div><p className="daily-brief-note">传统命理解释仅供参考；“计算可复现”不代表对现实结果的科学预测。</p></>}
  </section>
}
