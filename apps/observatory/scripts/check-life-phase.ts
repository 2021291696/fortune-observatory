// apps/observatory/scripts/check-life-phase.ts
import {
  decadalBuckets,
  pastQuestion,
  upcomingQuestion,
  nowQuestion,
} from '../src/lifePhase'

const TWELVE = Array.from({ length: 12 }, (_, i) => ({
  name: `宫${i}`,
  branch: '子',
  major_stars: ['紫微'],
  decadal_range: [i * 10, i * 10 + 9] as [number, number],
}))

function assert(cond: unknown, msg: string) {
  if (!cond) throw new Error(msg)
}

const young = decadalBuckets(TWELVE, 21)
assert(young.past.map((p) => p.decadal_range[0]).join() === '0,10', 'past 0-19')
assert(young.current?.decadal_range[0] === 20, 'current 20-29')
assert(young.upcoming.map((p) => p.decadal_range[0]).join() === '30,40', 'upcoming 30-49')

const past21 = pastQuestion(TWELVE, 21, 'relationship')
assert(past21, 'age 21 has past')
assert(past21!.includes('0-9'), 'past includes 0-9')
assert(past21!.includes('10-19'), 'past includes 10-19')
assert(!past21!.includes('20-29'), 'past omits current')
assert(!past21!.includes('80-'), 'past omits dropped')
assert(past21!.length <= 300, 'past question ≤300')
assert(past21!.includes('那十年容易'), 'past voice')
assert(past21!.includes('禁止「你当时已经」'), 'past forbids biography')
assert(past21!.includes('子女宫'), 'past mentions 子女宫 as name-only')

assert(pastQuestion(TWELVE, 5, 'health') === null, 'childhood no past')

const past55 = pastQuestion(TWELVE, 55, 'career')
assert(past55, 'age 55 has past')
for (const start of [0, 10, 20, 30, 40]) {
  assert(past55!.includes(`${start}-${start + 9}`), `55 past has ${start}`)
}
assert(!past55!.includes('50-59'), '55 past omits current')
assert(past55!.length <= 300, '55 past ≤300')

const next21 = upcomingQuestion(TWELVE, 21, 'relationship')
assert(next21, 'age 21 has upcoming')
assert(next21!.includes('30-39') && next21!.includes('40-49'), 'next two')
assert(!next21!.includes('50-'), 'no third upcoming')
assert(next21!.length <= 300, 'upcoming ≤300')
assert(upcomingQuestion(TWELVE, 130, 'wealth') === null, 'no upcoming after last')

assert(next21!.includes('那十年会容易'), 'upcoming voice')
assert(!next21!.includes('你当时已经'), 'upcoming forbids biography')

const now21 = nowQuestion(TWELVE, 21, 'relationship')
assert(now21, 'age 21 has current')
assert(now21!.includes('20-29'), 'now includes current')
assert(!now21!.includes('10-19'), 'now omits past')
assert(!now21!.includes('30-39'), 'now omits upcoming')
assert(now21!.includes('这十年容易'), 'now voice')
assert(now21!.includes('禁止「你已经」'), 'now forbids biography')
assert(now21!.length <= 300, 'now question ≤300')
assert(nowQuestion(TWELVE, 5, 'health'), 'childhood still has current')

console.log('check-life-phase ok')
