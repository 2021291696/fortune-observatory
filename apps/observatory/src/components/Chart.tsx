import { useState } from 'react'
import type { ThemeConfig } from '../themes'
import type { ChartResponse } from '../types'
import { termGlossary, branchesFromYin } from '../terminology'
import { AiExplainPanel } from './AiExplainPanel'
import { MemeCompanion } from './MemeCompanion'

const pillarLabels = ['年柱', '月柱', '日柱', '时柱']
const qizhengBodyLabels = { sun: '日', moon: '月', mercury: '水', venus: '金', mars: '火', jupiter: '木', saturn: '土' }
const traditionalLabels: Record<string, string> = {
  sun: '太阳', moon: '太阴', mercury: '水星', venus: '金星', mars: '火星',
  jupiter: '木星', saturn: '土星', rahu: '罗睺', ketu: '计都', apogee: '月孛', ziqi: '紫炁',
}

const STEM_ELEMENTS: Record<string, string> = {
  甲: 'wood', 乙: 'wood', 丙: 'fire', 丁: 'fire', 戊: 'earth',
  己: 'earth', 庚: 'metal', 辛: 'metal', 壬: 'water', 癸: 'water',
}
const BRANCH_ELEMENTS: Record<string, string> = {
  子: 'water', 丑: 'earth', 寅: 'wood', 卯: 'wood', 辰: 'earth',
  巳: 'fire', 午: 'fire', 未: 'earth', 申: 'metal', 酉: 'metal',
  戌: 'earth', 亥: 'water',
}

export function stemClass(stem: string) {
  return `el-${STEM_ELEMENTS[stem] ?? 'earth'}`
}

export function branchClass(branch: string) {
  return `el-${BRANCH_ELEMENTS[branch] ?? 'earth'}`
}

export function Chart({ chart, theme }: { chart: ChartResponse; theme: ThemeConfig }) {
  const [inspectIndex, setInspectIndex] = useState<number | null>(null)
  const pillars = Object.values(chart.bazi.pillars)
  const details = chart.bazi.pillar_details.length === 4
    ? chart.bazi.pillar_details
    : pillars.map((pillar) => ({ pillar, ten_god: '', hidden_stems: [] as { stem: string; ten_god: string }[], nayin: '' }))
  const dayun = chart.bazi.great_luck_periods.slice(0, 8)
  const mutagenOf = new Map(chart.ziwei.birth_mutagens.map((item) => [item.star, item.mutagen]))
  const starPalaces = chart.ziwei.palaces.filter((palace) => palace.major_stars.length)
  const minorPalaces = chart.ziwei.palaces.filter((palace) => palace.minor_stars.length)

  return <article className="chart-result">
    <header className="result-header">
      <MemeCompanion theme={theme} />
      <div>
        <span>命盘</span>
        <h2>{pillars.join(' · ')}</h2>
        <p>农历 {chart.bazi.lunar_date}，{chart.bazi.input_time_basis === 'apparent_solar' ? '真太阳时口径' : '民用时间口径'}</p>
      </div>
    </header>

    <div className="pillars-board" aria-label="四柱八字">
      <div className="board-row board-head">
        <span className="row-label" />
        {pillarLabels.map((label) => <b key={label}>{label}</b>)}
      </div>
      <div className="board-row">
        <span className="row-label">十神</span>
        {details.map((detail) => <b key={detail.pillar} className={detail.ten_god === '日主' ? 'is-daymaster' : ''}>{detail.ten_god || '—'}</b>)}
      </div>
      <div className="board-row board-gan">
        <span className="row-label">天干</span>
        {details.map((detail) => <b key={detail.pillar} className={`gan-zhi ${stemClass(detail.pillar[0])}`}>{detail.pillar[0]}</b>)}
      </div>
      <div className="board-row board-zhi">
        <span className="row-label">地支</span>
        {details.map((detail) => <b key={detail.pillar} className={`gan-zhi ${branchClass(detail.pillar[1])}`}>{detail.pillar[1]}</b>)}
      </div>
      <div className="board-row board-hidden">
        <span className="row-label">藏干</span>
        {details.map((detail) => <div className="hidden-stack" key={detail.pillar}>
          {detail.hidden_stems.length ? detail.hidden_stems.map((hidden) => (
            <i key={hidden.stem} className={stemClass(hidden.stem)} title={`${hidden.stem}·${hidden.ten_god}`}>
              {hidden.stem}<em>{hidden.ten_god}</em>
            </i>
          )) : <i className="hidden-empty">—</i>}
        </div>)}
      </div>
      <div className="board-row board-nayin">
        <span className="row-label">纳音</span>
        {details.map((detail) => <small key={detail.pillar}>{detail.nayin || '—'}</small>)}
      </div>
    </div>

    {dayun.length > 0 && <div className="dayun-strip" aria-label="大运">
      <span className="dayun-label">大运<br />{chart.bazi.great_luck_start.direction === 'forward' ? '顺行' : '逆行'}</span>
      {dayun.map((period) => <div className="dayun-cell" key={period.pillar + period.start_age}>
        <small>{period.start_age}岁</small>
        <b><span className={stemClass(period.pillar[0])}>{period.pillar[0]}</span><span className={branchClass(period.pillar[1])}>{period.pillar[1]}</span></b>
        <small>{period.end_age}</small>
      </div>)}
    </div>}

    <section className="result-summary">
      <div className="result-fact">
        <span>起运</span>
        <strong>{chart.bazi.great_luck_start.direction === 'forward' ? '顺排' : '逆排'} · {chart.bazi.great_luck_start.first_pillar}</strong>
        <p>{chart.bazi.great_luck_start.years} 年 {chart.bazi.great_luck_start.months} 月 {chart.bazi.great_luck_start.days} 日后起运</p>
      </div>
      <div className="result-fact">
        <span>紫微定位</span>
        <strong>命宫 {chart.ziwei.life_branch} · 身宫 {chart.ziwei.body_branch}</strong>
        <p>{chart.ziwei.five_elements_bureau} 局</p>
      </div>
    </section>

    <section className="ziwei-section">
      <div className="section-kicker"><span>紫微十二宫</span><small>点击宫位看三方四正与飞化 · 禄/权/科/忌 = 生年四化</small></div>
      <div className="palace-grid">
        {chart.ziwei.palaces.map((palace, index) => {
          const targetBranch = inspectIndex !== null ? chart.ziwei.palaces[inspectIndex].branch : null
          const targetBranchIndex = targetBranch ? branchesFromYin.indexOf(targetBranch) : -1
          const inspectingBranches = targetBranch
            ? [targetBranch, ...[6, 4, 8].map((offset) => branchesFromYin[(targetBranchIndex + offset) % 12])]
            : []
          return <article
            className={`${palace.is_body_palace ? 'is-body-palace ' : ''}${inspectingBranches.includes(palace.branch) ? 'is-inspecting ' : ''}${inspectIndex === index ? 'is-target' : ''}`}
            key={`${palace.name}-${palace.branch}`}
            role="button"
            tabIndex={0}
            title="点击查看三方四正与飞化"
            onClick={() => setInspectIndex(inspectIndex === index ? null : index)}
            onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') setInspectIndex(inspectIndex === index ? null : index) }}
          >
            <span title={termGlossary['宫干']}>{palace.stem}{palace.branch}</span><h3>{palace.name}{palace.is_body_palace ? ' · 身宫' : ''}</h3>
            <div className="palace-stars">
              {palace.major_star_brightness.map(([star, brightness]) => {
                const mutagen = mutagenOf.get(star)
                return <i key={star} className={`star-chip${mutagen ? ` is-mutagen is-${mutagen}` : ''}`} title={termGlossary[brightness] ?? ''}>
                  {star}<em>{brightness}</em>{mutagen ? <b title={termGlossary[`化${mutagen}`]}>{mutagen}</b> : null}
                </i>
              })}
              {!palace.major_stars.length && <i className="star-chip is-empty">无主星</i>}
            </div>
            <p title={termGlossary['大限']}>大限 {palace.decadal_range[0]}-{palace.decadal_range[1]}</p>
            <small title={termGlossary['小限']}>小限 {palace.minor_limit_ages.slice(0, 4).join('/')}</small>
          </article>
        })}
      </div>
      {inspectIndex !== null && (() => {
        const target = chart.ziwei.palaces[inspectIndex]
        const targetBranchIndex = branchesFromYin.indexOf(target.branch)
        const surrounds = [6, 4, 8].map((offset) =>
          chart.ziwei.palaces.find((item) => item.branch === branchesFromYin[(targetBranchIndex + offset) % 12]))
          .filter((item): item is NonNullable<typeof item> => Boolean(item))
        const flying = (chart.ziwei.flying_mutagens ?? []).filter((entry) => entry.from_branch === target.branch)
        const nameOf = (branch: string) => chart.ziwei.palaces.find((item) => item.branch === branch)?.name ?? branch
        return <div className="palace-inspect">
          <header>
            <strong>{target.name}宫 · {target.stem}{target.branch}</strong>
            <button type="button" onClick={() => setInspectIndex(null)}>收起</button>
          </header>
          <p title={termGlossary['三方四正']}>三方四正会照：{surrounds.map((item) => `${item.name}宫（${item.major_stars.join('、') || '无主星'}）`).join('；')}</p>
          {flying.length > 0 && <p title={termGlossary['飞化']}>宫干飞化：{flying.map((entry) => `${entry.star}化${entry.mutagen}→${nameOf(entry.to_branch)}宫${entry.is_self ? `（${termGlossary['自化']}）` : ''}`).join('；')}</p>}
          {chart.ai_contexts.ziwei && <AiExplainPanel
            auto
            cacheKey={`ai-ziwei-${chart.trace_id}-${target.branch}`}
            source={{
              key: `ziwei-${chart.trace_id}-${target.branch}`,
              kind: 'domain',
              title: `${target.name}宫详解`,
              summary: `${target.stem}${target.branch}宫，主星：${target.major_stars.join('、') || '无主星'}`,
              facts: chart.ai_contexts.ziwei.facts,
              contextTokens: [chart.ai_contexts.ziwei.token],
            }}
            defaultQuestion={`请详解我的${target.name}宫（${target.stem}${target.branch}，主星：${target.major_stars.join('、') || '无主星'}；三方四正：${surrounds.map((item) => item.name + '宫').join('、')}）：先一句话结论加一个比喻，再讲这个宫位管辖的生活领域在我身上的典型表现（每个术语配一句白话），最后给2条具体行动建议。`}
          />}
        </div>
      })()}
      {chart.ai_contexts.ziwei && <AiExplainPanel
        auto
        cacheKey={`ai-ziwei-${chart.trace_id}`}
        source={{
          key: `ziwei-${chart.trace_id}`,
          kind: 'domain',
          title: `紫微命盘 · 命宫${chart.ziwei.life_branch} 身宫${chart.ziwei.body_branch}`,
          summary: `${chart.ziwei.five_elements_bureau}局十二宫整盘解读`,
          facts: chart.ai_contexts.ziwei.facts,
          contextTokens: [chart.ai_contexts.ziwei.token],
        }}
        defaultQuestion="请用白话解读我的紫微命盘整体格局：先一句话结论加一个比喻；再讲命宫和身宫的星曜组合各意味着什么（每个术语都配一句白话）；最后给我2到4条今天就能做的具体行动建议。"
      />}
    </section>

    <details className="chart-full-details">
      <summary>解读、紫微十二宫与计算依据</summary>
    {chart.natal_insights.length > 0 && <section className="insight-section">
      <div className="section-kicker"><span>解读</span></div>
      <div className="insight-list">
        {chart.natal_insights.map((insight, index) => <article key={insight.insight_id}>
          <b>{String(index + 1).padStart(2, '0')}</b>
          <div><h3>{insight.title}</h3><p>{insight.summary}</p><strong>{insight.action}</strong></div>
        </article>)}
      </div>
    </section>}

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
          <h3>七政四余 · 恒星黄道 <em className="alpha-badge">传统层 alpha</em></h3>
          {chart.qizheng.traditional && (
            <table className="qz-table">
              <thead><tr><th>星曜</th><th>黄经</th><th>入宿</th><th>行度</th></tr></thead>
              <tbody>
                {chart.qizheng.traditional.bodies.map((body) => (
                  <tr key={body.body}>
                    <td title={termGlossary[traditionalLabels[body.body]] ?? ''}>{traditionalLabels[body.body]}</td>
                    <td title={termGlossary['恒星黄道']}>{body.longitude_deg.toFixed(2)}°</td>
                    <td title={termGlossary['入宿']}>入{body.mansion}宿 {body.mansion_offset_deg.toFixed(1)}°</td>
                    <td>{body.motion === 'retrograde' ? '逆行' : '顺行'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {chart.qizheng.traditional?.houses && (
            <p title={termGlossary['命宫']}>
              命宫{chart.qizheng.traditional.houses.life_branch} · 身宫{chart.qizheng.traditional.houses.body_branch}：
              {chart.qizheng.traditional.houses.houses.map(([name, branch]) => `${name}${branch}`).join('、')}
            </p>
          )}
          <p>{chart.qizheng.bodies.map((body) => `${qizhengBodyLabels[body.body]} ${body.longitude_deg.toFixed(3)}°${body.motion === 'retrograde' ? '逆行' : ''}`).join('；')}</p>
          <small title={termGlossary['二十八宿']}>{chart.qizheng.traditional ? `${chart.qizheng.traditional.notes.join('；')} · 口径见规则包 ${chart.qizheng.traditional.profile_id}` : '当前仅显示地心视黄经，不输出尚未达到稳定门槛的传统宫位结论。'}</small>
        </section>
      </div>
      <p className="trace-line">规则包 {chart.bazi.profile_id} · 星历 {chart.time_trace.ephemeris_id} / {chart.time_trace.ephemeris_sha256.slice(0, 12)}… · trace {chart.trace_id}</p>
    </details>
    </details>
  </article>
}
