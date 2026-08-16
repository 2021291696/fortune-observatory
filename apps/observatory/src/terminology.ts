const pillarPositions = ['年柱', '月柱', '日柱', '时柱']
const pillarDomains = ['长辈与人生根基层面', '事业环境与同辈层面', '本人与配偶层面', '子女与晚辈层面']

export function positionIndex(factId: string): number | null {
  const tail = factId.slice(factId.lastIndexOf('-') + 1)
  const index = Number(tail)
  return Number.isInteger(index) && index >= 0 && index < 4 ? index : null
}

export type PlainFact = {
  fact_id: string
  relation: 'branch_clash' | 'branch_combination' | 'branch_same'
  natal_pillar: string
  transit_pillar: string
}

/** 把一条冲/合/同支事实讲成人话：今天与你的哪一柱发生什么、牵动哪块生活。 */
export function plainFactLine(fact: PlainFact): string {
  const index = positionIndex(fact.fact_id)
  const position = index === null ? '命盘' : pillarPositions[index]
  const domain = index === null ? '' : `，牵动${pillarDomains[index]}`
  if (fact.relation === 'branch_clash') {
    return `今天（${fact.transit_pillar}）与你的${position}${fact.natal_pillar}相冲${domain}`
  }
  if (fact.relation === 'branch_combination') {
    return `今天（${fact.transit_pillar}）与你的${position}${fact.natal_pillar}相合${domain}`
  }
  return `今天（${fact.transit_pillar}）与你的${position}${fact.natal_pillar}同支，力量叠加${domain}`
}

/** 柱位生活领域（给动态总评用）。 */
export function factDomain(fact: PlainFact): string {
  const index = positionIndex(fact.fact_id)
  return index === null ? '日常安排' : pillarDomains[index]
}

export const relationShort: Record<PlainFact['relation'], string> = {
  branch_clash: '冲',
  branch_combination: '合',
  branch_same: '同',
}

/** 术语 → 一句白话（title 悬浮提示用）。 */
export const termGlossary: Record<string, string> = {
  冲: '两个地支相互对立：节奏容易被外力打断，宜拆小步推进',
  合: '两个地支相互吸引：事情容易接得上，适合沟通与合作',
  同支: '同一个地支重复出现：这股力量被叠加放大',
  十神: '天干五行生克关系的十种称呼（正官、偏财等），描述一股力量对"你"的作用方式',
  藏干: '地支内部隐藏的天干，代表不显眼的次要力量',
  纳音: '每对干支对应的古典意象（如"海中金"），一种传统注解',
  庙: '星曜力量最强',
  旺: '星曜力量很强',
  得: '星曜力量较强',
  利: '星曜力量尚可',
  平: '星曜力量平平',
  陷: '星曜力量最弱',
  不: '星曜力量微弱',
  四化: '生年天干给特定星曜附加的四种属性：禄（顺遂）、权（强势）、科（名声）、忌（阻滞）',
  化禄: '顺遂、资源顺畅的附加属性',
  化权: '强势、掌控欲增强的附加属性',
  化科: '名声、贵人显现的附加属性',
  化忌: '阻滞、需要留心的附加属性',
  大限: '紫微斗数的十年运势阶段，每十年换一个宫位',
  小限: '紫微斗数的年度运势宫位',
  主星: '紫微斗数中最重要的14颗星，决定一个宫位的主要性格',
  辅星: '紫微斗数中的辅助星曜，起加减分作用',
  大运: '八字每十年切换一次的干支阶段',
  流年: '当年对应的干支',
  流月: '当月对应的干支',
  流日: '当天对应的干支',
  五行局: '紫微斗数定紫微星位置用的分组（水二局～金四局等），数字越小起运越早',
}
