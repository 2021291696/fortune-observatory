import type { ChartResponse, TransitFact } from './types'
import { factDomain, plainFactLine, termGlossary } from './terminology'

const palaceTheme: Record<string, string> = {
  疾厄: '身心状态、作息节奏和恢复能力',
  夫妻: '亲密关系里的相处模式与边界',
  官禄: '事业方向、责任边界和可被验证的成果',
  财帛: '钱怎么进、怎么留、哪里容易漏',
  命宫: '自我底色和人生节奏的起点',
}

const starPlain: Record<string, string> = {
  紫微: '像家里的主心骨，习惯统筹、也容易把责任揽到自己身上',
  天机: '脑子转得快，善于变通，也容易想太多、睡不踏实',
  太阳: '外放、要被看见，精力跟着白天走，夜里容易空转',
  武曲: '做事讲结果和数字，利落，也容易把自己逼得很紧',
  天同: '求安稳、重感受，压力来时更想躲进舒服的节奏',
  廉贞: '感受强、起伏大，对不公特别敏感',
  天府: '会囤、会守，资源意识强，变化来得慢时更踏实',
  太阴: '内收、重夜里和私下的关系，情绪潮汐比表面明显',
  贪狼: '胃口大、想尝试，机会和诱惑往往一起出现',
  巨门: '靠嘴和分辨力吃饭，话多或话少都会被人记住',
  天相: '会配合、会补位，也容易先照顾别人再照顾自己',
  天梁: '像长辈或顾问，爱提醒、爱兜底，也容易操多余的心',
  七杀: '行动快、敢冲，适合短决策，不适合把所有事一次摊开',
  破军: '先拆再建，旧秩序待不住，新方向要自己开',
}

const mutagenPlain: Record<string, string> = {
  禄: '这股力量走得比较顺，资源更容易接到',
  权: '这股力量变强势，控制欲和话语权都会抬头',
  科: '这股力量更容易被看见、被评价',
  忌: '这股力量容易卡住，要留出缓冲，不要硬顶',
}

export type NarrativeBlock = { label: string; text: string }

function brightnessPlain(mark: string): string {
  return termGlossary[mark] ?? '力量需要结合整宫来看'
}

function currentAge(chart: ChartResponse): number | null {
  const birthYear = Number(String(chart.bazi.calculation_datetime).slice(0, 4))
  return Number.isFinite(birthYear) ? new Date().getFullYear() - birthYear + 1 : null
}

export function buildDomainNarrative(chart: ChartResponse, palaceName: string): NarrativeBlock[] {
  const palace = chart.ziwei.palaces.find((item) => item.name === palaceName)
  if (!palace) {
    return [{ label: '缺宫', text: `当前命盘没有返回${palaceName}宫，系统不会用其他宫位补写结论。` }]
  }
  const life = chart.ziwei.palaces.find((item) => item.name === '命宫')
  const age = currentAge(chart)
  const stage = age === null ? undefined : chart.ziwei.palaces.find((item) => item.decadal_range[0] <= age && age <= item.decadal_range[1])
  const stars = palace.major_star_brightness.length
    ? palace.major_star_brightness
    : palace.major_stars.map((star) => [star, '平'] as [string, string])
  const starLines = stars.map(([star, mark]) => {
    const flavor = starPlain[star] ?? '这颗主星要结合同宫辅星一起看'
    return `${star}（${mark}，${brightnessPlain(mark)}）：${flavor}`
  })
  const palaceStars = new Set([...palace.major_stars, ...palace.minor_stars])
  const mutagens = chart.ziwei.birth_mutagens
    .filter((item) => palaceStars.has(item.star))
    .map((item) => `${item.star}化${item.mutagen}——${mutagenPlain[item.mutagen] ?? '这是生年四化给这颗星加的属性'}`)
  const dayDetail = chart.bazi.pillar_details.find((item) => item.pillar === chart.bazi.pillars.day)
  const theme = palaceTheme[palaceName] ?? '这个宫位对应的生活领域'
  const minor = palace.minor_stars.slice(0, 6).join('、') || '当前无辅星数据'
  const blocks: NarrativeBlock[] = [
    {
      label: '先看底色',
      text: `日主是${chart.bazi.pillars.day}${dayDetail ? `，十神记为${dayDetail.ten_god}，纳音${dayDetail.nayin}` : ''}。命宫在${life?.branch ?? '未知'}支。${palaceName}宫讲的是${theme}；它落在${palace.branch}支，先把宫位和日主当成两面镜子，不要把其中一面单独当成结论。`,
    },
    {
      label: '宫里有什么',
      text: starLines.length
        ? `${palaceName}宫主星：${starLines.join('。')}。同宫辅星有${minor}${mutagens.length ? `；四化方面，${mutagens.join('；')}` : '；当前未检测到同宫生年四化'}。`
        : `${palaceName}宫当前没有主星数据，先看辅星${minor}，不要用别的宫硬补。`,
    },
  ]
  if (stage && age !== null) {
    const stageStars = stage.major_stars.slice(0, 3).join('、') || '无主星'
    blocks.push({
      label: '现在走到哪',
      text: `按虚岁约${age}岁计，大限正在${stage.name}宫（${stage.decadal_range[0]}-${stage.decadal_range[1]}岁，${stage.branch}支），宫内主星是${stageStars}。大限是十年换一宫的阶段主题，不是这一周的天气预报；看${theme}时，把「本宫结构」和「当前十年主题」叠在一起，比单看今天更稳。`,
    })
  }
  blocks.push({
    label: '怎么用',
    text: `下面的 AI 讲解会把这组盘面翻成更长的白话。你自己先记住两件事：只观察能被记录的信号（睡眠、对话、交付、现金流），不把星曜名称当成诊断或保证；有持续不适、合同或资金决策，先交给对应的专业人士。`,
  })
  return blocks
}

export function buildFortuneNarrative(args: {
  facts: TransitFact[]
  yearLine?: string
  decadeLine?: string
}): NarrativeBlock[] {
  const blocks: NarrativeBlock[] = []
  if (args.facts.length) {
    blocks.push({
      label: '冲合落在哪',
      text: args.facts.map((fact) => `${plainFactLine(fact)}。${factDomain(fact)}今天更需要留心节奏，而不是一次把大事做完。`).join(''),
    })
  }
  if (args.yearLine) {
    blocks.push({ label: '这一年', text: args.yearLine })
  }
  if (args.decadeLine) {
    blocks.push({ label: '这一步大限', text: args.decadeLine })
  }
  blocks.push({
    label: '用法',
    text: '把今天当成观察日：记下被打断的事、谈成的事、想花钱或想躲避的瞬间。流日是一天的天气，流年是季节，大限是气候，三层不要混成一句吉凶。',
  })
  return blocks
}

export function yearlyPlain(yearPillar: string, mutagens: Array<{ star: string; mutagen: string; palace_name: string; palace_branch: string }>, nominalAge: number): string {
  if (!mutagens.length) {
    return `${yearPillar}年虚岁约${nominalAge}，当前没有列出可追溯的流年四化落宫；先用八字流年和大限看节奏，不要补写不存在的四化。`
  }
  const lines = mutagens.map((entry) => {
    const palace = entry.palace_name || `${entry.palace_branch}宫`
    const meaning = mutagenPlain[entry.mutagen] ?? '这是流年给这颗星加的属性'
    return `${entry.star}化${entry.mutagen}入${palace.endsWith('宫') ? palace : `${palace}宫`}——${meaning}`
  })
  return `${yearPillar}年虚岁约${nominalAge}。流年四化是当年环境的四个焦点：${lines.join('；')}。`
}

export function decadePlain(start: number, end: number, isChildhood: boolean, branch: string, stem?: string): string {
  if (isChildhood) {
    return `当前仍在童限，按${branch}宫看这一阶段的主题。童限还不是十年大限，结论要更保守。`
  }
  return `当前大限约${start}-${end}岁，行${stem ?? ''}${branch}。这十年的题目比今天的冲合更大，适合用来选方向、立规矩，不适合用来赌某一天的结果。`
}
