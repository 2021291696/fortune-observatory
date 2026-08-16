const pillarPositions = ['年柱', '月柱', '日柱', '时柱']
const pillarDomains = ['长辈与人生根基层面', '事业环境与同辈层面', '本人与配偶层面', '子女与晚辈层面']

/** 寅起十二支序（三方四正 = 本宫 + 对宫 +6 + 三合 +4/+8）。 */
export const branchesFromYin: string[] = ['寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥', '子', '丑']

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
  宫干: '每个宫位配的天干（由出生年干五虎遁排定），是飞化的起点',
  飞化: '某宫天干引发的四化飞到另一宫，表示两个生活领域之间的能量传递',
  自化: '宫干四化落回本宫：这股力量自来自去、不容易留住',
  三方四正: '本宫+对宫+两个三合宫共四宫，看一个领域要连同一起看',
  流曜: '随流年流转的辅星（流魁流钺流昌流曲等），给当年增添助力或阻力',
  流年四化: '流年天干引发的四化，描述当年整体环境的四个焦点',
  童限: '未进入大限的幼年阶段，按另一套宫位轮值',
  罗睺: '月球轨道与黄道的升交点（平位置）——一个轨道交点而非实体星，传统称"蚀神"',
  计都: '罗睺的正对面（降交点），与罗睺永远成一对',
  月孛: '月球轨道的远地点（平位置），传统视为"暗月"',
  紫炁: '本表取月孛对宫占位（现代约定）；古典紫炁行度没有公认的天文对应',
  太阳: '太阳的视位置——七政盘中代表父辈、权威与核心自我',
  太阴: '月亮的视位置——七政盘中代表情绪、母亲与日常节律',
  水星: '水星的视位置——沟通、文书与交易之星',
  金星: '金星的视位置——喜好、金钱与感情之星',
  火星: '火星的视位置——行动、冲突与冲劲之星',
  木星: '木星的视位置——扩张、贵人机遇之星',
  土星: '土星的视位置——收缩、纪律与长期压力之星',
  二十八宿: '沿天球分布的 28 个恒星区段，中国传统的"天区门牌号"，每个宫支对应固定几宿',
  入宿: '天体落在哪一宿、距该宿距星多少度——古法的定位坐标，相当于"天上的街道地址"',
  恒星黄道: '以遥远恒星（二十八宿距星）为固定参照的黄道坐标，不随岁差漂移',
  命宫: '传统盘的起点宫位；七政按"太阳所在宫起生时顺数至卯"安命',
  身宫: '同法数至酉，与命宫永远相对，传统上代表身体与后天',
}
