import { ChartLine, ChatCircleDots, StarFour, UserCircle } from '@phosphor-icons/react'

export type AppView = 'fortune' | 'ask' | 'chart' | 'profile'

const views = [
  { id: 'fortune', label: '运势', icon: ChartLine },
  { id: 'ask', label: '问事', icon: ChatCircleDots },
  { id: 'chart', label: '命盘', icon: StarFour },
  { id: 'profile', label: '我的', icon: UserCircle },
] as const

function hasStoredProfiles(): boolean {
  try {
    const raw = window.localStorage.getItem('fortune-users-v1')
    if (!raw) return false
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) && parsed.length > 0
  } catch {
    return false
  }
}

export function viewFromHash(hash = window.location.hash): AppView {
  const value = hash.replace(/^#/, '')
  if (value === 'ask' || value === 'analysis') return 'ask'
  if (value === 'chart') return 'chart'
  if (value === 'profile' || value === 'saved') return 'profile'
  if (value === 'fortune') return 'fortune'
  // No explicit hash: returning visitors land on their fortune, first-time
  // visitors land on the chart page whose gate walks them into onboarding.
  return hasStoredProfiles() ? 'fortune' : 'chart'
}

export function AppNavigation({ activeView, onNavigate }: {
  activeView: AppView
  onNavigate: (view: AppView) => void
}) {
  return <nav className="primary-nav" aria-label="核心功能">
    {views.map(({ id, label, icon: Icon }) => <a
      key={id}
      className={activeView === id ? 'is-active' : ''}
      href={`#${id}`}
      aria-current={activeView === id ? 'page' : undefined}
      onClick={() => onNavigate(id)}
    >
      <Icon size={22} weight={activeView === id ? 'fill' : 'bold'} />
      <span><strong>{label}</strong></span>
    </a>)}
  </nav>
}
