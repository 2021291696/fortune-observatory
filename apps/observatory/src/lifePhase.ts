export type LimitPalace = {
  name: string
  branch: string
  major_stars: string[]
  decadal_range: [number, number]
}

export function chartAge(calculationDatetime: string, now = new Date()): number | null {
  const birthYear = Number(String(calculationDatetime).slice(0, 4))
  return Number.isFinite(birthYear) ? now.getFullYear() - birthYear + 1 : null
}

export function decadalBuckets(palaces: LimitPalace[], age: number) {
  const ordered = [...palaces].sort((a, b) => a.decadal_range[0] - b.decadal_range[0])
  const past: LimitPalace[] = []
  let current: LimitPalace | null = null
  const future: LimitPalace[] = []
  for (const item of ordered) {
    const [start, end] = item.decadal_range
    if (end < age) past.push(item)
    else if (start <= age && age <= end && current === null) current = item
    else if (start > age) future.push(item)
    else if (start <= age && age <= end) future.push(item)
  }
  if (current === null && ordered.length) {
    current = ordered[ordered.length - 1]
    return {
      past: ordered.filter((item) => item !== current),
      current,
      upcoming: [] as LimitPalace[],
      dropped: [] as LimitPalace[],
    }
  }
  return { past, current, upcoming: future.slice(0, 2), dropped: future.slice(2) }
}

function limitLine(item: LimitPalace) {
  const stars = item.major_stars.slice(0, 2).join('、') || '无主星'
  const name = item.name.endsWith('宫') ? item.name : `${item.name}宫`
  return `${item.decadal_range[0]}-${item.decadal_range[1]}岁${name}（${item.branch}）坐${stars}`
}

export const themes = {
  health: '健康与身心状态',
  relationship: '感情与亲密关系',
  career: '事业与方向',
  wealth: '钱财与财务习惯',
} as const

function fitQuestion(text: string, max = 300) {
  return text.length <= max ? text : text.slice(0, max)
}

export function pastQuestion(
  palaces: LimitPalace[],
  age: number,
  domain: keyof typeof themes,
): string | null {
  const past = decadalBuckets(palaces, age).past
  if (!past.length) return null
  const limits = past.map(limitLine).join('；')
  return fitQuestion(
    `只写已过大限的${themes[domain]}，每限独立一小节写日子（节奏、坑、怎么接到下一限），用「那十年容易」，禁止「你当时已经」。不要写当前和未到：${limits}。子女宫只当宫名，当晚辈或作品，不写带孩子。`,
  )
}

export function nowQuestion(
  palaces: LimitPalace[],
  age: number,
  domain: keyof typeof themes,
): string | null {
  const current = decadalBuckets(palaces, age).current
  if (!current) return null
  return fitQuestion(
    `只写当前大限的${themes[domain]}（${limitLine(current)}）。写成独立小节：这十年容易有的节奏、坑、怎么接到下一限。用「这十年容易」，禁止「你已经」。不要写已过和未到。子女宫只当宫名。`,
  )
}

export function upcomingQuestion(
  palaces: LimitPalace[],
  age: number,
  domain: keyof typeof themes,
): string | null {
  const upcoming = decadalBuckets(palaces, age).upcoming
  if (!upcoming.length) return null
  const limits = upcoming.map(limitLine).join('；')
  return fitQuestion(
    `只写未到两限的${themes[domain]}，每限独立一小节写日子（节奏、坑、怎么接到再下一限），用「那十年会容易」，不当成正在过。不要写已过和当前：${limits}。子女宫只当宫名，不写带孩子。`,
  )
}
