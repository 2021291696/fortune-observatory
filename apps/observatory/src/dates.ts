import type { FortuneScope } from './types'

export function beijingCalendarDate() {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date())
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${values.year}-${values.month}-${values.day}`
}

function dateFromKey(value: string) {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day))
}

export function dateKey(value: Date) {
  return `${value.getUTCFullYear()}-${String(value.getUTCMonth() + 1).padStart(2, '0')}-${String(value.getUTCDate()).padStart(2, '0')}`
}

function addDays(value: Date, days: number) {
  const next = new Date(value)
  next.setUTCDate(next.getUTCDate() + days)
  return next
}

export function fortuneWindow(scope: FortuneScope) {
  const today = dateFromKey(beijingCalendarDate())
  if (scope === 'today') return { label: '今日', start: today, end: today }
  if (scope === 'tomorrow') {
    const tomorrow = addDays(today, 1)
    return { label: '明日', start: tomorrow, end: tomorrow }
  }
  if (scope === 'thisWeek' || scope === 'nextWeek') {
    const mondayOffset = (today.getUTCDay() + 6) % 7
    const start = addDays(today, -mondayOffset + (scope === 'nextWeek' ? 7 : 0))
    return { label: scope === 'thisWeek' ? '本周' : '下周', start, end: addDays(start, 6) }
  }
  const monthOffset = scope === 'nextMonth' ? 1 : 0
  const start = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() + monthOffset, 1))
  const end = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth() + monthOffset + 1, 0))
  return { label: scope === 'thisMonth' ? '本月' : '下月', start, end }
}
