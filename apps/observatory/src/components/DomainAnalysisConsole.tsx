import { Briefcase, Coins, FloppyDisk, Heart, Heartbeat, ShieldCheck } from '@phosphor-icons/react'
import { useEffect, useState, type ComponentType } from 'react'
import type { AnalysisDomain, ChartResponse, SaveDraft } from '../types'
import { analysisDomains } from '../types'

type DomainResult = {
  title: string
  lead: string
  structure: string
  action: string
  evidence: string[]
  disclaimer?: string
}

const domainConfig: Record<AnalysisDomain, {
  palace: string
  label: string
  prompt: string
  action: string
  icon: ComponentType<{ size?: number; weight?: 'bold' | 'fill' }>
}> = {
  health: {
    palace: '疾厄', label: '健康', prompt: '从疾厄宫读取身体议题的结构入口', icon: Heartbeat,
    action: '把睡眠、饮食、活动量与不适记录成可复查的时间线；持续或明显不适请优先交给专业医生。',
  },
  relationship: {
    palace: '夫妻', label: '姻缘', prompt: '从夫妻宫读取亲密关系的互动入口', icon: Heart,
    action: '把沟通节奏、个人边界与冲突后的恢复方式分开观察，用真实互动校准命盘语言。',
  },
  career: {
    palace: '官禄', label: '事业', prompt: '从官禄宫读取职业发展的结构入口', icon: Briefcase,
    action: '把专业能力、责任边界与下一阶段作品拆开列出，先推进一个可以被验证的最小成果。',
  },
  wealth: {
    palace: '财帛', label: '财运', prompt: '从财帛宫读取资源与现金流的结构入口', icon: Coins,
    action: '先定义现金流、风险上限和不可承受损失，再讨论机会；命盘不能替代具体财务数据。',
  },
}

function buildResult(chart: ChartResponse, domain: AnalysisDomain): DomainResult {
  const config = domainConfig[domain]
  const palace = chart.ziwei.palaces.find((item) => item.name === config.palace)
  if (!palace) {
    return {
      title: `${config.label}分析暂不可用`,
      lead: `当前命盘没有返回${config.palace}宫，系统不会用其他宫位补写结论。`,
      structure: '缺少领域定位事实，本次分析到此为止。',
      action: '可以先展开完整命盘检查数据；若仍缺失，请重新排盘或稍后再试。',
      evidence: ['未找到对应宫位'],
    }
  }

  const majorStars = palace.major_star_brightness.length
    ? palace.major_star_brightness.map(([star, brightness]) => `${star}（${brightness}）`).join('、')
    : palace.major_stars.join('、') || '当前无主星数据'
  const minorStars = palace.minor_stars.join('、') || '当前无辅星数据'
  const palaceStars = new Set([...palace.major_stars, ...palace.minor_stars])
  const mutagens = chart.ziwei.birth_mutagens
    .filter((item) => palaceStars.has(item.star))
    .map((item) => `${item.star}化${item.mutagen}`)
  const mutagenCopy = mutagens.length ? `；同宫可追溯四化为${mutagens.join('、')}` : '；当前未检测到同宫生年四化'

  return {
    title: `${config.label} · ${config.palace}宫在${palace.branch}`,
    lead: `${config.prompt}。宫内主星：${majorStars}；辅星：${minorStars}${mutagenCopy}。`,
    structure: `这是一组领域定位事实，不是吉凶评分。单宫尚不足以推出确定结果，当前引擎也不会把八字、紫微和七政机械相加。`,
    action: config.action,
    evidence: [
      `${config.palace}宫 · ${palace.branch}`, `大限 ${palace.decadal_range[0]}–${palace.decadal_range[1]}`,
      `主星 ${majorStars}`, `辅星 ${minorStars}`, ...(mutagens.length ? [`四化 ${mutagens.join('、')}`] : []),
    ],
    ...(domain === 'health' ? { disclaimer: '命理分析不构成诊断、治疗或用药建议。' } : {}),
  }
}

export function DomainAnalysisConsole({ chart, onSave }: {
  chart: ChartResponse | null
  onSave: (draft: SaveDraft) => void
}) {
  const [active, setActive] = useState<AnalysisDomain | null>(null)
  const [results, setResults] = useState<Partial<Record<AnalysisDomain, DomainResult>>>({})

  useEffect(() => {
    setActive(null)
    setResults({})
  }, [chart?.trace_id])

  function request(domain: AnalysisDomain) {
    if (!chart) return
    setResults((current) => current[domain] ? current : { ...current, [domain]: buildResult(chart, domain) })
    setActive(domain)
  }

  const result = active ? results[active] : null
  const activeConfig = active ? domainConfig[active] : null

  return <section className="analysis-section" id="analysis">
    <header className="content-heading compact-heading">
      <span>01 / 命盘专项</span>
      <h2>四个问题，分开分析。</h2>
      <p>健康、姻缘、事业、财运互不捆绑。排盘完成后，只有你点击的领域才会展开。</p>
    </header>
    <div className={`domain-console ${chart ? 'is-ready' : ''}`}>
      <div className="domain-choices" role="group" aria-label="选择专项分析">
        {analysisDomains.map(([domain, label]) => {
          const Icon = domainConfig[domain].icon
          return <button
            key={domain}
            type="button"
            className={active === domain ? 'is-active' : ''}
            aria-pressed={active === domain}
            disabled={!chart}
            onClick={() => request(domain)}
          >
            <Icon size={25} weight={active === domain ? 'fill' : 'bold'} />
            <span>{label}<small>{results[domain] ? '已生成 · 查看' : '按需分析'}</small></span>
          </button>
        })}
      </div>

      <div className="domain-output" aria-live="polite">
        {!chart && <div className="feature-empty"><ShieldCheck size={34} weight="bold" /><div><strong>等待命盘完成</strong><p>这里不会提前生成套话，也不会自动分析四个领域。</p></div></div>}
        {chart && !result && <div className="feature-empty"><ShieldCheck size={34} weight="bold" /><div><strong>命盘已就绪</strong><p>选择一个领域开始。已经生成的其他领域会继续保留。</p></div></div>}
        {result && activeConfig && active && chart && <article className="domain-reading">
          <header><span>{activeConfig.label.toUpperCase()} / FACT-GROUNDED</span><h3>{result.title}</h3></header>
          <p className="domain-lead">{result.lead}</p>
          <div className="domain-interpretation"><span>怎么读</span><p>{result.structure}</p></div>
          <blockquote><span>你可以把握的是</span>{result.action}</blockquote>
          {result.disclaimer && <p className="domain-disclaimer">{result.disclaimer}</p>}
          <footer>
            <div className="evidence-list" aria-label="分析依据">{result.evidence.map((item) => <span key={item}>{item}</span>)}</div>
            <button type="button" onClick={() => onSave({
              kind: 'domain', title: result.title, summary: result.lead,
              details: [result.structure, result.action, ...result.evidence],
            })}><FloppyDisk size={18} weight="bold" /> 保存这项分析</button>
          </footer>
        </article>}
      </div>
    </div>
  </section>
}
