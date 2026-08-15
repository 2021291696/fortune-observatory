import { CheckCircle, WarningCircle } from '@phosphor-icons/react'
import type { ChartResponse, VerificationStatus } from '../types'

const pillarLabels = ['年柱', '月柱', '日柱', '时柱']
const qizhengBodyLabels = { sun: '日', moon: '月', mercury: '水', venus: '金', mars: '火', jupiter: '木', saturn: '土' }

function statusCopy(status: VerificationStatus) {
  if (status === 'verified') return '计算已核验'
  if (status === 'ambiguous') return '存在临界条件'
  return '计算待核验'
}

export function Chart({ chart }: { chart: ChartResponse }) {
  const pillars = Object.values(chart.bazi.pillars)
  const isVerified = chart.bazi.verification_status === 'verified'
  const starPalaces = chart.ziwei.palaces.filter((palace) => palace.major_stars.length)
  const minorPalaces = chart.ziwei.palaces.filter((palace) => palace.minor_stars.length)

  return <article className="chart-result">
    <header className="result-header">
      <div>
        <span>命盘摘要</span>
        <h2>{pillars.join(' · ')}</h2>
        <p>农历 {chart.bazi.lunar_date}，{chart.bazi.input_time_basis === 'apparent_solar' ? '真太阳时口径' : '民用时间口径'}</p>
      </div>
      <div className={`verification-badge ${isVerified ? 'is-verified' : ''}`}>
        {isVerified ? <CheckCircle size={22} weight="fill" /> : <WarningCircle size={22} weight="fill" />}
        {statusCopy(chart.bazi.verification_status)}
      </div>
    </header>

    <div className="pillar-row" aria-label="八字四柱">
      {pillars.map((pillar, index) => <div key={pillarLabels[index]}>
        <small>{pillarLabels[index]}</small><strong>{pillar}</strong>
      </div>)}
    </div>

    <section className="result-summary">
      <div className="result-fact">
        <span>大运起点</span>
        <strong>{chart.bazi.great_luck_start.direction === 'forward' ? '顺排' : '逆排'} · {chart.bazi.great_luck_start.first_pillar}</strong>
        <p>{chart.bazi.great_luck_start.years} 年 {chart.bazi.great_luck_start.months} 月 {chart.bazi.great_luck_start.days} 日后起运</p>
      </div>
      <div className="result-fact">
        <span>紫微定位</span>
        <strong>命宫 {chart.ziwei.life_branch} · 身宫 {chart.ziwei.body_branch}</strong>
        <p>{chart.ziwei.five_elements_bureau} 局，{statusCopy(chart.ziwei.verification_status)}</p>
      </div>
    </section>

    <details className="chart-full-details">
      <summary>查看完整命盘、十二宫与计算依据</summary>
    {chart.natal_insights.length > 0 && <section className="insight-section">
      <div className="section-kicker"><span>可执行解读</span></div>
      <div className="insight-list">
        {chart.natal_insights.map((insight, index) => <article key={insight.insight_id}>
          <b>{String(index + 1).padStart(2, '0')}</b>
          <div><h3>{insight.title}</h3><p>{insight.summary}</p><strong>{insight.action}</strong><small>依据：{insight.fact_ids.join('、')}</small></div>
        </article>)}
      </div>
    </section>}

    <section className="ziwei-section">
      <div className="section-kicker"><span>紫微十二宫</span></div>
      <div className="palace-grid">
        {chart.ziwei.palaces.map((palace) => <article className={palace.is_body_palace ? 'is-body-palace' : ''} key={`${palace.name}-${palace.branch}`}>
          <span>{palace.branch}</span><h3>{palace.name}{palace.is_body_palace ? ' · 身宫' : ''}</h3>
          <p>大限 {palace.decadal_range[0]}-{palace.decadal_range[1]}</p>
          <small>小限 {palace.minor_limit_ages.slice(0, 4).join('/')}</small>
        </article>)}
      </div>
    </section>

    <details className="technical-details">
      <summary>展开计算依据与深层数据</summary>
      <div className="technical-grid">
        <section>
          <h3>时间计算轨迹</h3>
          <p>坐标：{chart.time_trace.longitude.toFixed(4)}° / {chart.time_trace.latitude.toFixed(4)}°</p>
          <p>民用时间：{chart.time_trace.civil_datetime}</p>
          <p>地方平太阳时：{chart.time_trace.local_mean_solar_datetime}</p>
          <p>真太阳时：{chart.time_trace.apparent_solar_datetime ?? '未启用'}，来源 {chart.time_trace.apparent_solar_source}</p>
        </section>
        <section>
          <h3>主星与亮度</h3>
          <p>{starPalaces.map((palace) => `${palace.branch}宫：${palace.major_star_brightness.map(([star, brightness]) => `${star}${brightness}`).join('、')}`).join('；') || '当前无主星数据'}</p>
        </section>
        <section>
          <h3>辅星与四化</h3>
          <p>{minorPalaces.map((palace) => `${palace.branch}宫：${palace.minor_stars.join('、')}`).join('；') || '当前无辅星数据'}</p>
          <p>{chart.ziwei.year_stem}年干：{chart.ziwei.birth_mutagens.map((item) => `${item.star}化${item.mutagen}`).join('、')}</p>
        </section>
        <section>
          <h3>七政物理位置</h3>
          <p>{chart.qizheng.bodies.map((body) => `${qizhengBodyLabels[body.body]} ${body.longitude_deg.toFixed(3)}°${body.motion === 'retrograde' ? '逆行' : ''}`).join('；')}</p>
          <small>当前仅显示地心视黄经，不输出尚未达到稳定门槛的传统宫位结论。</small>
        </section>
      </div>
      <p className="trace-line">规则包 {chart.bazi.profile_id} · 星历 {chart.time_trace.ephemeris_id} / {chart.time_trace.ephemeris_sha256.slice(0, 12)}… · trace {chart.trace_id}</p>
    </details>
    </details>
  </article>
}
