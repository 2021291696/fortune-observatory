// 解读体系偏好：全站问事与运势只按选定体系出一张解读卡。
// 与主题/动效偏好同模式存本机（无账号体系，跨会话靠 localStorage）。
export type ReadingSystem = 'bazi' | 'ziwei'

const READING_SYSTEM_KEY = 'fortune-reading-system-v1'

export function loadReadingSystem(): ReadingSystem {
  try {
    return window.localStorage.getItem(READING_SYSTEM_KEY) === 'ziwei' ? 'ziwei' : 'bazi'
  } catch {
    return 'bazi'
  }
}

export function saveReadingSystem(value: ReadingSystem) {
  try {
    window.localStorage.setItem(READING_SYSTEM_KEY, value)
  } catch {
    // 存储不可用时偏好只在当前会话生效
  }
}

export const readingSystemLabels: Record<ReadingSystem, string> = {
  bazi: '八字',
  ziwei: '紫微',
}

export const readingSystemNotes: Record<ReadingSystem, string> = {
  bazi: '干支五行看格局与流年运程',
  ziwei: '十二宫看人生领域',
}

// 拆分功能上线前的存量收藏没有体系标记，按紫微口径标注（当时语料以紫微为主）。
export function savedSystemLabel(system: ReadingSystem | undefined): string {
  return readingSystemLabels[system ?? 'ziwei']
}
